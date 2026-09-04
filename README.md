# leitor-lote

Lê uma pasta de canhotos (imagens `.jpg/.png` e PDFs), extrai o número de cada um
(OCR ou IA, motor escolhível), valida, e grava cópias renomeadas em `<pasta>/saida/`.
Os resultados aparecem numa tabela na própria janela, com um botão para exportar
`resultado.csv` para onde você quiser. Roda 100% na máquina — sem upload, sem servidor.

## Uso (executável)

1. Baixe o zip do [Releases](https://github.com/GabrielFerrazzzzz/leitor-lote/releases) e extraia.
2. Rode `leitor-lote.exe`. Na 1ª vez o Windows mostra o SmartScreen —
   **Mais informações → Executar assim mesmo**.
3. Escolha a pasta, o tipo de leitura e o motor, e clique **Rodar**. Se o motor
   escolhido for local (Tesseract/RapidOCR/TrOCR), aparece a opção "Se não
   reconhecer, tentar de novo com IA" — veja a seção **Motor local + IA de
   reforço** abaixo.
4. As cópias renomeadas ficam em `<pasta>/saida/`. O resultado também aparece numa
   tabela na janela, com um botão **Exportar CSV…** para salvar `resultado.csv`
   onde você quiser.

### Motores

| Motor | Chave? | Observação |
|---|---|---|
| `tesseract` | não | requer Tesseract instalado no PATH (não vai no pacote nesta versão); bom no número impresso |
| `rapidocr` | não | embutido; melhor OCR tradicional grátis |
| `trocr` | não | baixa ~1,3 GB no 1º uso (precisa de internet uma vez) |
| `openai:gpt-5-mini` / `openai:gpt-5` | sim | cole a chave em **Configurar chaves…** |
| `mistral-ocr` | sim | idem |

### Motor local + IA de reforço

Não existe mais um seletor de "Modo" separado — o comportamento é decidido pelo
Motor escolhido:

- Motor **local** (`tesseract`/`rapidocr`/`trocr`): aparece a opção **"Se não
  reconhecer, tentar de novo com IA"**, marcada por padrão. Marcada, se o OCR
  local reprovar na validação ou a confiança ficar baixa, a leitura é refeita com
  `openai:gpt-5-mini` (se houver chave configurada). Desmarcada, usa só o motor
  local.
- Motor de **API** (`openai:*`/`mistral-ocr`): a leitura é feita direto por ele,
  sem OCR local antes.

(Internamente isso ainda é o campo `modo` — `"ocr"`/`"auto"`/`"ia"` — em
`ParametrosRodada`; só deixou de ser um campo separado na tela.)

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
    --tipo canhoto --motores tesseract,rapidocr,trocr,openai:gpt-5-mini,mistral-ocr
```

`gabarito.csv`: colunas `arquivo,esperado` (dígitos esperados). Saída: tabela no
terminal + `bench/resultado-<data>.csv`.
