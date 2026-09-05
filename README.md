# leitor-lote

Lê uma pasta de canhotos (imagens `.jpg/.png` e PDFs), extrai o número de cada um
(OCR ou IA, motor escolhível), valida, e grava cópias renomeadas em `<pasta>/saida/`.
Roda 100% na máquina — sem upload, sem servidor.

## Uso (instalador)

1. Baixe o `leitor-lote-setup.exe` do
   [Releases](https://github.com/GabrielFerrazzzzz/leitor-lote/releases/latest) e rode.
   O instalador deixa você escolher a pasta; não precisa de admin.
2. Na 1ª vez o Windows mostra o SmartScreen —
   **Mais informações → Executar assim mesmo**.
3. Escolha a pasta, o tipo de leitura e o motor, e clique **Rodar**. Se o motor
   escolhido for local (Tesseract/RapidOCR), aparecem as opções "Se não reconhecer,
   tentar de novo com IA" e "…tentar com outro motor" — veja **Fallbacks** abaixo.
4. As cópias renomeadas vão para `<pasta>/saida/` conforme cada arquivo é lido. Para
   ver a tabela e salvar `resultado.csv`, clique **Exportar CSV…**.

### Motores

| Motor | Chave? | Observação |
|---|---|---|
| `rapidocr` | não | embutido; padrão para os tipos de canhoto |
| `tesseract` | não | requer Tesseract instalado no PATH (não vai no pacote); bom no número impresso |
| `openai:gpt-5-mini` / `openai:gpt-5` | sim | cole a chave em **Configurar chaves…** |
| `mistral-ocr` | sim | idem |

### Fallbacks

Não existe seletor de "Modo" — o comportamento vem do Motor escolhido + dois
checkboxes (só aparecem com Motor local):

- **"Se não reconhecer, tentar de novo com IA"** (marcada por padrão): se o OCR
  local reprovar na validação ou a confiança ficar baixa, refaz com
  `openai:gpt-5-mini` (se houver chave). Internamente é o `modo="auto"`.
- **"Se não reconhecer, tentar com outro motor"** + combo: refaz o arquivo com o
  motor escolhido no combo (`ParametrosRodada.motor_fallback`). O combo só lista
  motores disponíveis diferentes do principal.

Ordem quando os dois estão ligados: principal → motor do combo → IA. Um fallback
que quebra (API sem rede, motor sem dependência) é ignorado — mantém o resultado
do principal, não vira `erro`.

Motor de **API** como principal (`openai:*`/`mistral-ocr`): a leitura é feita
direto por ele, sem OCR local antes, e os checkboxes somem.

## `tipos.json`

A lista de tipos de leitura é buscada de
`https://raw.githubusercontent.com/GabrielFerrazzzzz/leitor-lote/main/tipos.json`
(há uma cópia embutida usada offline). Formato:

```json
[
  {
    "id": "canhoto",
    "nome": "Canhoto",
    "modo": "auto",
    "motor": "rapidocr",
    "prompt": "Leia APENAS o número de 6 dígitos...",
    "campos": [{ "nome": "numero", "tamanho": 6, "sequencial": true }],
    "formato_exemplo": "349498"
  }
]
```

## Dev

```bash
uv sync --extra dev
uv run python -m leitor_lote      # abre a janela
uv run pytest                     # testes (readers reais marcados 'manual' ficam de fora)
uv run pytest -m manual           # exercita libs/APIs reais
uv run ruff check .
```

## Build do `.exe`

```bash
uv run pyinstaller leitor-lote.spec
# -> dist/leitor-lote/leitor-lote.exe
```

No CI, um push de tag `v*` builda no `windows-latest` e anexa o zip no Release.

## Benchmark

```bash
uv run python -m bench.benchmark --pasta ./amostras --gabarito ./amostras/gabarito.csv \
    --tipo canhoto --motores tesseract,rapidocr,openai:gpt-5-mini,mistral-ocr
```

`gabarito.csv`: colunas `arquivo,esperado` (dígitos esperados). Saída: tabela no
terminal + `bench/resultado-<data>.csv`.
