# `leitor-lote` — Design

**Data:** 2026-09-03
**Status:** aprovado (brainstorming), pronto pra virar plano de implementação

---

## 1. Contexto e motivação

Existe hoje o projeto **Automações Soma** (`automacoes-soma`, webapp Lovable + worker Bun no
EasyPanel + n8n) que lê canhotos de entrega — fotos/scans com um **número de documento
impresso** e um **número de nota escrito à mão** — e renomeia cada arquivo com o número lido.
A leitura roda no servidor: o usuário sobe um lote pro Supabase Storage, um worker chama a
OpenAI (Responses API) ou faz OCR com Tesseract, e devolve um zip com tudo renomeado.

O incômodo: pra clientes do tipo "Soma", o ideal é **não subir arquivo em canto nenhum** — a
pessoa baixa um programa, roda na máquina dela apontando pra uma pasta, e pronto. Sem
Storage, sem egress, sem n8n, sem conta.

Este projeto é esse programa: um **executável de desktop em Python** que faz a mesma leitura
em lote, 100% local. Também serve de peça de portfólio ("empacotei um pipeline de visão
computacional + OCR + LLM num executável Windows, com benchmark de motores").

Referência interna: `Projetos/Ensino/Leitura Soma.md` no vault Obsidian, seção
"Ideia do executável local (em avaliação — 2026-08-29)".

## 2. Objetivos

- Ler uma **pasta local** de imagens (`.jpg/.jpeg/.png`) e PDFs de canhotos, extrair o(s)
  número(s), e gravar **cópias renomeadas** + um relatório.
- Rodar **sem backend**: sem Supabase, sem n8n, sem servidor próprio.
- **Nenhuma chave de API embutida.** Motores pagos só funcionam se o usuário colar a própria
  chave; ela fica só na máquina dele.
- **Motor de OCR escolhível** — por tipo de leitura (no `tipos.json`) e sobreponível na
  janela por rodada. Trocar de motor é config, nunca código.
- Um **modo grátis** que funciona sem nenhuma chave (Tesseract / PaddleOCR embutidos).
- Um **benchmark** que roda todos os motores contra um gabarito real e mede o acerto, pra
  decidir qual motor marcar em cada tipo de documento.
- Empacotar num `.exe` Windows distribuível.

## 3. Não-objetivos (YAGNI)

- Auto-updater embutido (no máximo: checar um `version.json` e avisar).
- GUI além de uma única janela.
- Multi-OS (só Windows; o código não vai *impedir* Linux/Mac, mas não é alvo nem é testado).
- Qualquer backend, telemetria, licenciamento ou banco de dados.
- Sincronizar resultados pra lugar nenhum — a saída é local, o feedback do cliente é manual.
- EasyOCR (fora do bundle; a fatia "OCR tradicional grátis" fica com o PaddleOCR).
- Treinar/fine-tunar modelo próprio.

## 4. Escala assumida

1 cliente por automação, 1–2 máquinas que o Gabriel mesmo controla. Isso justifica:
sem code-signing (aceitar o aviso do SmartScreen 1×), sem instalador MSI (zip + pasta),
updates manuais (recompila, sobe num link, re-baixa).

## 5. Visão geral da arquitetura

Aplicação Python única, em camadas isoladas. Cada camada tem um contrato pequeno e é
testável sozinha.

```
leitor-lote/
  leitor_lote/
    __main__.py          # ponto de entrada: abre a janela
    gui.py               # janela Tkinter
    config.py            # config local + fetch do tipos.json
    preprocess.py        # normalização de imagem (OpenCV/Pillow)
    pipeline.py          # varre a pasta, orquestra, aplica validação
    validate.py          # regra determinística de aceitação da leitura
    output.py            # cópias renomeadas + resultado.csv + log.txt
    readers/
      __init__.py        # registry: nome do motor -> classe
      base.py            # dataclass Reading + classe base Reader
      tesseract_reader.py
      paddleocr_reader.py
      trocr_reader.py
      openai_reader.py
      mistral_reader.py
  bench/
    benchmark.py         # roda todos os motores contra um gabarito
  tests/
  tipos.fallback.json    # cópia embutida do tipos.json (usada offline)
  .github/workflows/build.yml
  pyproject.toml
  README.md
  docs/superpowers/specs/2026-09-03-leitor-lote-desktop-design.md
```

Fluxo de dados de uma rodada:

```
janela (pasta, tipo, motor, modo, seq/intervalo, chave)
  -> config.carregar()  +  config.buscar_tipos()
  -> pipeline.rodar(params)
       para cada arquivo (pool de concorrência 4-6):
         preprocess.preparar(arquivo, para_ocr=?) -> imagem normalizada
         reader.read(imagem) -> Reading{valor, confianca, motor, bruto}
         validate.avaliar(Reading, tipo, seq, intervalo) -> ResultadoValidado
         se modo == "auto" e reprovou/baixa confiança -> repete com o reader de IA
  -> output.gravar(resultados, pasta_saida)
       saida/<numero>.<ext>  (+ sufixo em colisão)
       resultado.csv, log.txt
```

## 6. Contratos por módulo

### 6.1 `readers/base.py`

```python
@dataclass(frozen=True)
class Reading:
    valor: str            # número(s) lido(s), cru do motor (ex.: "349498" ou "349498 - 383462")
    confianca: float | None   # 0..1 quando o motor fornece; None quando não
    motor: str            # id do motor que produziu ("tesseract", "openai:gpt-5-mini", ...)
    bruto: str            # resposta/texto cru do motor, pra depuração e log

class Reader(Protocol):
    id: str
    requer_chave: bool
    def disponivel(self, config) -> bool: ...   # p.ex. chave presente, modelo baixado
    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading: ...
```

- `imagem: PreparedImage` — vem do `preprocess`, carrega bytes normalizados + mimetype +
  dimensões + caminho temporário (alguns motores querem arquivo em disco).
- `tipo: Tipo` — o registro do `tipos.json` (id, prompt, formato esperado, campos).
- Motores nunca leem config global direto além do que `disponivel()` precisa; a chave é
  passada na construção do reader pelo `pipeline`.

### 6.2 `readers/` — implementações

| id | classe | requer_chave | peso | notas |
|---|---|---|---|---|
| `tesseract` | `TesseractReader` | não | bin ~30 MB embutido | `pytesseract` + binário empacotado; `--psm` ajustado pra linha de dígitos; bom no impresso, fraco no manuscrito |
| `paddleocr` | `PaddleOcrReader` | não | ~150–300 MB | `paddleocr` + `paddlepaddle` CPU; modelo `en` + detecção; melhor "OCR tradicional" grátis |
| `trocr` | `TrOcrReader` | não (baixa no 1º uso) | modelo ~1,3 GB baixado e cacheado em `%LOCALAPPDATA%/leitor-lote/models` | `transformers` + `torch` CPU; `microsoft/trocr-large-handwritten`; precisa de um detector de linha na frente (usa a detecção do Paddle ou um crop simples) |
| `openai:<modelo>` | `OpenAIReader` | sim | ~0 (só HTTP) | porta o `lerArquivoComIA` do worker: Responses API, `input_image` (a imagem já vem rasterizada do `preprocess`), retry/backoff em 429/5xx; modelos expostos: `gpt-5-mini` (padrão), `gpt-5` |
| `mistral-ocr` | `MistralOcrReader` | sim | ~0 (só HTTP) | endpoint OCR da Mistral (`mistral-ocr-latest`); manda a imagem da página, recebe texto; bom em cursiva |

Registry em `readers/__init__.py`: `MOTORES: dict[str, type[Reader]]`. A GUI lista as chaves;
motor com `requer_chave` e sem chave no config aparece **desabilitado**.

### 6.3 `preprocess.py`

```python
@dataclass
class PreparedImage:
    bytes_: bytes
    mimetype: str          # image/jpeg | image/png | application/pdf
    largura: int
    altura: int
    caminho_tmp: Path      # arquivo temporário em disco (apagado ao fim da rodada)

def preparar(arquivo: Path, *, para_ocr: bool) -> list[PreparedImage]:
    ...
```

- Sempre: corrigir orientação por EXIF; se o lado maior > 2000 px, reduzir mantendo
  proporção e re-encodar JPEG em q0.82 (mesmas constantes do `comprimirImagem.ts` do webapp,
  já validado com 251 arquivos reais).
- PDF: **sempre rasterizado** (via `pypdfium2`, que roda embutido, sem binário de sistema),
  cada página a 300 dpi → uma `PreparedImage` por página. Retorna lista por isso; imagem
  simples retorna lista de 1. Consequência: **todo reader recebe imagem**, nunca PDF — não
  há caminho "manda o PDF nativo pro VLM" nesta iteração.
- `para_ocr=True` adiciona: escala de cinza, `adaptiveThreshold` (Otsu), deskew por
  `minAreaRect` da maior massa de texto. `para_ocr=False` (caminho LLM) devolve a imagem só
  normalizada — VLM lê melhor a foto "crua" que a binarizada.

### 6.4 `validate.py`

```python
@dataclass
class ResultadoValidado:
    texto_lido: str        # valor final aceito, ou "Não reconhecido" (por campo)
    aprovado: bool
    motivo: str | None     # por que reprovou, pro log

def avaliar(r: Reading, tipo: Tipo, seq_esperada: int | None,
            intervalo_maximo: int | None) -> ResultadoValidado:
    ...
```

Regra portada da cascata determinística do n8n (`Projetos/Ensino/Leitura Soma.md`):

- Dirigida por `tipo.campos` (do `tipos.json`), não hardcoded. Cada campo tem um `tamanho`
  esperado (default 6). Exemplos: `canhoto` = 1 campo de 6 dígitos; `pedido` = 2 campos de 6
  dígitos, o `valor` do reader vem separado por `" - "`.
- Cada campo tem que bater `\d{tamanho}` depois de limpo (tirar tudo que não é dígito). Campo
  que não bate vira `"Não reconhecido"` — **sem derrubar o outro campo** que passou.
- Se `seq_esperada` e `intervalo_maximo` vierem preenchidos: rejeita valor fora de
  `[seq_esperada - intervalo, seq_esperada + intervalo]` (marca aquele campo como
  `"Não reconhecido"`). Regra dura, não é dica de prompt.
- `aprovado = True` só se todos os campos do tipo passaram.

### 6.5 `pipeline.py`

```python
@dataclass
class ParametrosRodada:
    pasta_entrada: Path
    tipo_id: str
    motor_id: str
    modo: Literal["ocr", "ia", "auto"]
    seq_esperada: int | None
    intervalo_maximo: int | None

@dataclass
class LinhaResultado:
    arquivo: str
    texto_lido: str
    confianca: float | None
    motor: str
    status: Literal["ok", "nao_reconhecido", "erro"]
    erro: str | None

def rodar(p: ParametrosRodada, cfg: Config, tipos: dict[str, Tipo],
          progresso: Callable[[int, int], None]) -> list[LinhaResultado]:
    ...
```

- Lista os arquivos suportados na pasta (não recursivo). Ordena por nome.
- `concurrent.futures.ThreadPoolExecutor(max_workers=4..6)` — mesma lição do resto do
  projeto: concorrência limitada, não "tudo de uma vez" (rate limit das APIs; CPU no OCR).
  Configurável em `config.json` (`concorrencia`, default 5).
- `motor_id` é uma chave qualquer do registry. A GUI tem **um** combo "Motor"; a
  interpretação depende do `modo`:
  - `ocr` → `motor_id` tem que ser um motor local (`tesseract`/`paddleocr`/`trocr`).
  - `ia` → `motor_id` tem que ser um motor de API (`openai:*`/`mistral-ocr`); erro claro se
    não tiver chave.
  - `auto` → `motor_id` é o motor local; se `not aprovado` **ou** (`confianca` não-`None` e
    `< limiar`, default 0.6 em `config.json`), refaz aquele arquivo com o
    `config.motor_ia_fallback` (default `openai:gpt-5-mini`). Motor local sem confiança
    (`None`, ex. TrOCR) → o gatilho é só `not aprovado`. Sem chave pro fallback → mantém o
    resultado do OCR e marca no log.
- `progresso(feitos, total)` alimenta a barra da GUI. Sem estado global; a GUI passa um
  callback que faz `after(0, ...)` no thread do Tk.
- Cancelamento: um `threading.Event`; a GUI seta ao fechar/cancelar, o pool para de agendar.

### 6.6 `output.py`

```python
def gravar(linhas: list[LinhaResultado], pasta_saida: Path) -> None: ...
```

- `pasta_saida = pasta_entrada / "saida"` (criada se não existir).
- Cópia de cada arquivo com nome = `texto_lido` limpo (sem acento, maiúsculas, `[^A-Z0-9]` →
  `_`), extensão original preservada. Colisão de nome no mesmo lote → sufixo `_2`, `_3`…
  (porta `nomeNoZip` do worker; desambiguação só quando há colisão real, ex. vários
  "Não reconhecido"). Status `erro` → prefixo `ERRO_`.
- `resultado.csv`: `arquivo,texto_lido,confianca,motor,status,erro` (UTF-8 com BOM, pro Excel
  abrir certo em português).
- `log.txt`: uma linha por arquivo com timestamp, motor, tempo, `bruto` truncado, e o
  `motivo` da validação quando reprovou.

### 6.7 `config.py`

```python
@dataclass
class Config:
    chave_openai: str | None
    chave_mistral: str | None
    ultima_pasta: str | None
    motor_padrao: str | None
    concorrencia: int = 5
    limiar_confianca: float = 0.6
    motor_ia_fallback: str = "openai:gpt-5-mini"
    tipos_url: str = "https://raw.githubusercontent.com/GabrielFerrazzzzz/leitor-lote/main/tipos.json"
    # ^ conta GabrielFerrazzzzz (mesma do automacoes-soma); confirmar no momento do push

def carregar() -> Config: ...          # %APPDATA%/leitor-lote/config.json, cria com defaults
def salvar(c: Config) -> None: ...
def buscar_tipos(cfg: Config) -> dict[str, Tipo]: ...   # GET tipos_url; fallback tipos.fallback.json
```

- `Tipo`: `{ id, nome, prompt, modo, motor, campos: [{nome, tamanho}], formato_exemplo }`.
- `buscar_tipos`: timeout 5 s; qualquer falha (offline, 404, JSON inválido) → carrega
  `tipos.fallback.json` embutido no bundle e loga o motivo. Nunca trava a rodada.
- A chave nunca vai pro log nem pro CSV. Guardada em texto no `config.json` (escala de 1–2
  máquinas controladas; keyring do Windows é um "poderia depois", não agora).

### 6.8 `gui.py` / `__main__.py`

Janela Tkinter única (`ttk`), ~150 linhas:

- Campo "Pasta" + botão "Procurar" (default = `ultima_pasta`).
- Combo "Tipo de leitura" (do `tipos.json`). Ao trocar, pré-seleciona `motor` e `modo` do tipo.
- Combo "Motor" (todas as chaves do registry — locais e de API; itens que exigem chave
  ausente aparecem como "OpenAI (sem chave)" desabilitado). Ao trocar o modo, o combo filtra
  pros motores válidos daquele modo.
- Combo "Modo" (`ocr` / `ia` / `auto`).
- Campos opcionais "Sequência esperada" e "Intervalo máximo" (só habilita o segundo quando o
  primeiro tem valor — espelha o webapp).
- Botão "Configurar chaves…" → diálogo com `chave_openai`, `chave_mistral`.
- Botão "Rodar" → desabilita a UI, `pipeline.rodar` num thread, barra de progresso +
  "X de Y", botão vira "Cancelar".
- Ao fim: label "Concluído — N ok, M não reconhecidos, K erros" + botão "Abrir pasta de
  saída" (`os.startfile`).
- Sem menu, sem abas, sem tela de histórico.

### 6.9 `bench/benchmark.py`

CLI separada (não entra no `.exe`, não roda no CI):

```
uv run python -m bench.benchmark --pasta ./amostras --gabarito ./amostras/gabarito.csv \
    --tipo canhoto --motores tesseract,paddleocr,trocr,openai:gpt-5-mini,mistral-ocr
```

- `gabarito.csv`: `arquivo,esperado` (por campo, quando o tipo tem mais de um: `esperado_1,esperado_2`).
- Para cada motor: roda o mesmo `preprocess` + `read` + limpeza, compara com o gabarito.
- Métricas por motor e por campo: **acerto exato** (%), **CER de dígito** (Levenshtein /
  nº de dígitos), **nº de "não reconhecido"**, tempo médio por arquivo, custo estimado
  (motores de API).
- Saída: tabela no terminal + `bench/resultado-<data>.csv`. É o insumo pra escolher o
  `motor` de cada tipo no `tipos.json` — e um gráfico desse resultado vai pro README como
  peça de portfólio.

## 7. Empacotamento e distribuição

- **PyInstaller `--onedir`**, zipado. Pasta com `leitor-lote.exe` + `_internal/` (modelos do
  Paddle e binário do Tesseract ao lado, sem descompactar no `%TEMP%` a cada abertura).
- TrOCR **não** vai no zip — é baixado do HuggingFace no 1º uso do motor `trocr` e cacheado
  em `%LOCALAPPDATA%/leitor-lote/models`. Primeira execução desse motor precisa de internet;
  as seguintes, não.
- `.github/workflows/build.yml`: em `push` de tag `v*`, roda em `windows-latest`, faz
  `uv sync`, `pyinstaller leitor-lote.spec`, zipa a pasta `dist/leitor-lote/`, e anexa o zip
  no GitHub Release da tag.
- Sem certificado de code-signing. README explica o "Mais informações → Executar assim
  mesmo" do SmartScreen na 1ª vez.
- Opcional (fase 2): no start, `GET` de um `version.json` no repo; se a versão local for
  menor, mostra um aviso não-bloqueante com o link do Release.

## 8. Ferramentas e ambiente de dev

- **VS Code** + **Python 3.12** + **`uv`** (venv + lock).
- `uv run python -m leitor_lote` roda a janela em dev.
- `pyproject.toml`: deps de runtime (`pillow`, `opencv-python-headless`, `numpy`,
  `pytesseract`, `paddleocr`, `paddlepaddle`, `transformers`, `torch` CPU, `pypdfium2`,
  `httpx`); deps de dev (`pytest`, `pyinstaller`, `ruff`).
- Lint/format: `ruff`.

## 9. Testes

`pytest`, sem rede, sem modelos pesados:

- `validate`: 6 dígitos ok/não; um campo bom + um ruim; dentro/fora de `seq ± intervalo`;
  entrada com lixo não-dígito.
- `output`: limpeza de nome; colisão → `_2`/`_3`; prefixo `ERRO_`; CSV com BOM e cabeçalho
  certo.
- `config`: cria default quando não existe; `buscar_tipos` cai no fallback quando a URL
  falha (monkeypatch no `httpx`); chave nunca aparece em CSV/log (asserção).
- `preprocess`: orientação EXIF aplicada; imagem grande reduz pra ≤ 2000 px; PDF de 2
  páginas → 2 `PreparedImage` (com um PDF minúsculo de fixture).
- `pipeline`: com um `FakeReader` determinístico — modo `auto` cai pro fallback quando o
  fake "reprova"; concorrência respeita o limite; `progresso` é chamado `total` vezes;
  cancelamento para o agendamento.
- Motores reais (`tesseract`, `paddleocr`, APIs): **não** no CI. Um teste `@pytest.mark.manual`
  por motor, rodado à mão com amostra local.

## 10. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Acerto do OCR grátis em manuscrito é baixo (Tesseract 12,5% CER, Paddle 5,8% em prosa) | O caso real é **6 dígitos**, não prosa — o benchmark com canhotos reais é quem decide; `modo=auto` cai pra IA quando o OCR titubeia; motor é trocável por tipo |
| `.exe` gigante com Paddle + Torch | `--onedir` (não `--onefile`); TrOCR fica fora do zip (download sob demanda); Torch CPU-only |
| PyInstaller + PaddleOCR/transformers = hooks chatos (paths de modelo) | `.spec` versionado com `datas`/`hiddenimports` explícitos; CI builda a cada tag pra pegar quebra cedo |
| Lógica de leitura duplicada (worker TS + este `.exe`) | Prompt e formato vêm do `tipos.json` por URL — a parte que mais muda fica num lugar só; a validação é simples e estável |
| Rasterizar PDF precisa de binário externo (`poppler`) | Usar `pypdfium2` (roda embutido, sem binário de sistema) em vez de `pdf2image`+poppler |
| Chave de API em texto no `config.json` | Aceito nessa escala (máquinas controladas); documentado; keyring fica como melhoria futura |
| SmartScreen bloqueia o `.exe` pra usuário leigo | Escala é 1–2 máquinas que o Gabriel prepara; README com o passo do "Executar assim mesmo" |

## 11. Fora do escopo desta iteração (candidatos a fase 2)

- Aviso de versão nova via `version.json`.
- Keyring do Windows pras chaves.
- Motor EasyOCR como opção extra.
- Modo CLI paralelo à GUI (pra automação encadeada).
- Detector de linha dedicado pro TrOCR (hoje reaproveita a detecção do Paddle).

## 12. Decisões travadas nesta rodada de brainstorming

- Projeto **novo e standalone**, não uma feature do `automacoes-soma`.
- **Sem backend** — descartado o schema novo no Supabase / uso da infra.
- Nome do repo: **`leitor-lote`** (neutro; nada de "Soma" no código).
- Interface: **janela Tkinter** (cliente não é dev).
- Bundle de motores: **Tesseract + PaddleOCR embutidos; TrOCR-Large sob demanda; OpenAI +
  Mistral OCR por chave**. EasyOCR fora.
- Empacotamento: **PyInstaller `--onedir` num zip**, build por GitHub Actions no tag.
- Modo e motor de leitura são **config por tipo** (`tipos.json`), sobreponíveis na janela.
- Chave de API: **nunca embutida**; o usuário cola a própria.
