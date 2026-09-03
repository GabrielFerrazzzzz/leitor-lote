# leitor-lote Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um executável de desktop Windows, em Python, que lê uma pasta de canhotos (imagens/PDFs), extrai o número de cada um por OCR ou IA (motor escolhível), valida, e grava cópias renomeadas + `resultado.csv` + `log.txt` — 100% local, sem backend.

**Architecture:** Aplicação Python em camadas isoladas: `preprocess` normaliza a imagem, um `Reader` plugável (Tesseract / PaddleOCR / TrOCR / OpenAI / Mistral OCR) devolve um `Reading`, `validate` aplica a regra determinística de 6 dígitos + faixa, `pipeline` orquestra num pool de concorrência limitada, `output` grava os arquivos. Uma janela Tkinter é a única interface. Um `bench/benchmark.py` separado compara os motores contra um gabarito real.

**Tech Stack:** Python 3.12, `uv`, Tkinter/ttk, Pillow, `opencv-python-headless`, NumPy, `pypdfium2`, `pytesseract` (+ binário Tesseract empacotado), `paddleocr` + `paddlepaddle` (CPU), `transformers` + `torch` (CPU, só TrOCR), `httpx`, `pytest`, `pyinstaller`, `ruff`.

## Global Constraints

- **Python 3.12** como piso, ambiente gerenciado com `uv`.
- **Alvo Windows** (dev e empacotamento). O código não bloqueia outros SOs, mas só Windows é testado/suportado.
- **Nenhuma chave de API embutida no binário.** A chave só vem do `config.json` local do usuário; **nunca** é escrita em `log.txt`, `resultado.csv`, nem em `Reading.bruto`.
- **Sem backend:** sem Supabase, sem n8n, sem banco, sem telemetria, sem licenciamento, sem rede além de (a) chamadas aos motores de API quando o usuário escolhe um e (b) `GET` do `tipos.json` e download do modelo TrOCR.
- Nome do pacote/repo: **`leitor-lote`** / módulo **`leitor_lote`**. **Nada específico do cliente "Soma" no código** — prompt, formato e campos vêm do `tipos.json`.
- **Concorrência sempre limitada** (`config.concorrencia`, default **5**). Nunca pool ilimitado.
- **Empacotamento:** PyInstaller **`--onedir`**, zipado; build no **GitHub Actions em tag `v*`**, runner `windows-latest`.
- **Textos de interface em pt-BR.**
- `resultado.csv` em **UTF-8 com BOM** (`utf-8-sig`).
- **Interface de motor única:** `Reading{valor: str, confianca: float | None, motor: str, bruto: str}`; método `read(imagem: PreparedImage, tipo: Tipo) -> Reading`.
- **Validação dirigida por `tipo.campos`** (cada campo tem `tamanho`, default 6). A regra de faixa `seq_esperada ± intervalo_maximo` é determinística (não é dica de prompt).
- **PDF sempre rasterizado** (`pypdfium2`, 300 dpi). Todo `Reader` recebe imagem, nunca PDF.
- **Fora de escopo:** EasyOCR, auto-updater, CLI da aplicação principal (só a janela), keyring do Windows, multi-OS, detector de linha dedicado pro TrOCR.
- **Readers reais não rodam no CI.** Cada reader (`tesseract`, `paddleocr`, `trocr`, `openai:*`, `mistral-ocr`) tem teste unitário com *monkeypatch* da chamada externa **+** um teste `@pytest.mark.manual` que exercita a lib de verdade.

---

## File Structure

```
leitor-lote/
  pyproject.toml                       # Task 1  — deps, ruff, pytest
  leitor-lote.spec                     # Task 14 — PyInstaller
  .github/workflows/build.yml          # Task 14 — build no tag
  README.md                            # Task 16
  leitor_lote/
    __init__.py                        # Task 1
    __main__.py                        # Task 13 — entry -> janela
    models.py                          # Task 2  — dataclasses compartilhadas
    validate.py                        # Task 3  — avaliar()
    config.py                          # Task 4  — Config, carregar/salvar, buscar_tipos
    tipos.fallback.json                # Task 4  — cópia embutida (refina o spec: fica DENTRO do pacote)
    preprocess.py                      # Task 5  — preparar()
    readers/
      __init__.py                      # Task 6  — MOTORES_IDS, resolve(), disponivel()
      base.py                          # Task 6  — Protocol Reader
      tesseract_reader.py              # Task 7
      paddleocr_reader.py              # Task 8
      trocr_reader.py                  # Task 9
      openai_reader.py                 # Task 10
      mistral_reader.py                # Task 11
    pipeline.py                        # Task 12 — rodar()
    output.py                          # Task 13 — gravar()
    gui.py                             # Task 13 — rodar_janela() + helpers puros
  bench/
    __init__.py                        # Task 15
    benchmark.py                       # Task 15
  tests/
    conftest.py                        # Task 1/5 — fixtures de imagem/PDF/config
    fakes.py                           # Task 6  — FakeReader
    test_*.py
```

---

### Task 1: Scaffold do projeto

**Files:**
- Create: `pyproject.toml`
- Create: `leitor_lote/__init__.py`
- Create: `leitor_lote/readers/__init__.py` (vazio por ora)
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Consumes: nada.
- Produces: pacote importável `leitor_lote`; `uv run pytest` funcional; `uv run ruff check` funcional.

- [ ] **Step 1: Escrever `pyproject.toml`**

```toml
[project]
name = "leitor-lote"
version = "0.1.0"
description = "Leitor de canhotos em lote, local (OCR/IA), com motor escolhivel"
requires-python = ">=3.12"
dependencies = [
    "pillow>=10.4",
    "opencv-python-headless>=4.10",
    "numpy>=1.26",
    "pypdfium2>=4.30",
    "pytesseract>=0.3.13",
    "paddleocr>=2.8",
    "paddlepaddle>=2.6",
    "transformers>=4.44",
    "torch>=2.4",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pyinstaller>=6.10", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["leitor_lote"]

[tool.pytest.ini_options]
markers = ["manual: exercita libs/APIs reais, nao roda no CI"]
addopts = "-m 'not manual'"

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 2: Criar os arquivos do pacote**

`leitor_lote/__init__.py`:
```python
__version__ = "0.1.0"
```

`leitor_lote/readers/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

`tests/test_smoke.py`:
```python
import leitor_lote


def test_importa_pacote():
    assert leitor_lote.__version__ == "0.1.0"
```

- [ ] **Step 3: Sincronizar o ambiente e rodar o teste**

Run: `uv sync --extra dev && uv run pytest tests/test_smoke.py -v`
Expected: PASS (1 passed)

- [ ] **Step 4: Rodar o lint**

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml leitor_lote/ tests/
git commit -m "chore: scaffold do projeto (uv, pytest, ruff)"
```

---

### Task 2: Modelos de dados (`models.py`)

**Files:**
- Create: `leitor_lote/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `Reading(valor: str, confianca: float | None, motor: str, bruto: str)` — `frozen`
  - `PreparedImage(bytes_: bytes, mimetype: str, largura: int, altura: int, caminho_tmp: Path)` — `frozen`
  - `Campo(nome: str, tamanho: int = 6, sequencial: bool = False)` — `frozen`. `sequencial` marca o campo que segue a sequência de notas (é nele que a regra `seq ± intervalo` se aplica na Task 3).
  - `Tipo(id: str, nome: str, prompt: str, modo: str, motor: str, campos: tuple[Campo, ...], formato_exemplo: str = "")` — `frozen`
  - `ResultadoValidado(texto_lido: str, aprovado: bool, motivo: str | None)` — `frozen`
  - `LinhaResultado(arquivo: str, texto_lido: str, confianca: float | None, motor: str, status: str, erro: str | None)` — `frozen`
  - `ParametrosRodada(pasta_entrada: Path, tipo_id: str, motor_id: str, modo: str, seq_esperada: int | None, intervalo_maximo: int | None)` — `frozen`

- [ ] **Step 1: Escrever os testes**

`tests/test_models.py`:
```python
from pathlib import Path

import pytest

from leitor_lote.models import (
    Campo,
    LinhaResultado,
    ParametrosRodada,
    PreparedImage,
    Reading,
    ResultadoValidado,
    Tipo,
)


def test_reading_frozen():
    r = Reading(valor="349498", confianca=0.9, motor="fake", bruto="349498")
    assert r.valor == "349498"
    with pytest.raises(Exception):
        r.valor = "x"  # frozen


def test_campo_defaults():
    c = Campo(nome="numero")
    assert c.tamanho == 6
    assert c.sequencial is False
    assert Campo(nome="nota", sequencial=True).sequencial is True


def test_tipo_com_campos():
    t = Tipo(
        id="canhoto",
        nome="Canhoto",
        prompt="leia o numero",
        modo="auto",
        motor="paddleocr",
        campos=(Campo("numero", 6),),
    )
    assert t.formato_exemplo == ""
    assert t.campos[0].tamanho == 6


def test_demais_dataclasses_constroem():
    PreparedImage(bytes_=b"x", mimetype="image/jpeg", largura=1, altura=2, caminho_tmp=Path("a"))
    ResultadoValidado(texto_lido="349498", aprovado=True, motivo=None)
    LinhaResultado(
        arquivo="a.jpg", texto_lido="349498", confianca=None, motor="fake", status="ok", erro=None
    )
    ParametrosRodada(
        pasta_entrada=Path("."),
        tipo_id="canhoto",
        motor_id="paddleocr",
        modo="auto",
        seq_esperada=None,
        intervalo_maximo=None,
    )
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.models`)

- [ ] **Step 3: Implementar `models.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Modo = Literal["ocr", "ia", "auto"]
Status = Literal["ok", "nao_reconhecido", "erro"]


@dataclass(frozen=True)
class Reading:
    valor: str
    confianca: float | None
    motor: str
    bruto: str


@dataclass(frozen=True)
class PreparedImage:
    bytes_: bytes
    mimetype: str
    largura: int
    altura: int
    caminho_tmp: Path


@dataclass(frozen=True)
class Campo:
    nome: str
    tamanho: int = 6
    sequencial: bool = False


@dataclass(frozen=True)
class Tipo:
    id: str
    nome: str
    prompt: str
    modo: Modo
    motor: str
    campos: tuple[Campo, ...]
    formato_exemplo: str = ""


@dataclass(frozen=True)
class ResultadoValidado:
    texto_lido: str
    aprovado: bool
    motivo: str | None


@dataclass(frozen=True)
class LinhaResultado:
    arquivo: str
    texto_lido: str
    confianca: float | None
    motor: str
    status: Status
    erro: str | None


@dataclass(frozen=True)
class ParametrosRodada:
    pasta_entrada: Path
    tipo_id: str
    motor_id: str
    modo: Modo
    seq_esperada: int | None
    intervalo_maximo: int | None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/models.py tests/test_models.py
git commit -m "feat: dataclasses de dominio (Reading, Tipo, LinhaResultado, ...)"
```

---

### Task 3: Validação determinística (`validate.py`)

**Files:**
- Create: `leitor_lote/validate.py`
- Create: `tests/test_validate.py`

**Interfaces:**
- Consumes: `Reading`, `Tipo`, `Campo`, `ResultadoValidado` de `leitor_lote.models`.
- Produces: `avaliar(r: Reading, tipo: Tipo, seq_esperada: int | None, intervalo_maximo: int | None) -> ResultadoValidado`. Regras: separa `r.valor` por `" - "`; para cada `tipo.campos[i]`, limpa não-dígitos, exige exatamente `campo.tamanho` dígitos, senão o campo vira `"Não reconhecido"` (sem derrubar os outros); se `seq_esperada` **e** `intervalo_maximo` vierem, rejeita valor fora de `[seq-intervalo, seq+intervalo]` — mas **só nos campos com `campo.sequencial == True`** (ou em todos, se nenhum campo do tipo estiver marcado `sequencial`). `aprovado` = todos os campos ok. `texto_lido` = campos juntados por `" - "`.

- [ ] **Step 1: Escrever os testes**

`tests/test_validate.py`:
```python
from leitor_lote.models import Campo, Reading, Tipo
from leitor_lote.validate import avaliar

CANHOTO = Tipo(id="canhoto", nome="Canhoto", prompt="", modo="auto", motor="paddleocr",
               campos=(Campo("numero", 6),))
PEDIDO = Tipo(id="pedido", nome="Pedido", prompt="", modo="auto", motor="paddleocr",
              campos=(Campo("documento", 6), Campo("nota", 6)))
PEDIDO_SEQ = Tipo(id="pedido", nome="Pedido", prompt="", modo="auto", motor="paddleocr",
                  campos=(Campo("documento", 6, sequencial=False),
                          Campo("nota", 6, sequencial=True)))


def _r(valor: str) -> Reading:
    return Reading(valor=valor, confianca=None, motor="fake", bruto=valor)


def test_canhoto_ok():
    v = avaliar(_r("349498"), CANHOTO, None, None)
    assert v.aprovado is True
    assert v.texto_lido == "349498"
    assert v.motivo is None


def test_canhoto_poucos_digitos():
    v = avaliar(_r("34949"), CANHOTO, None, None)
    assert v.aprovado is False
    assert v.texto_lido == "Não reconhecido"
    assert "5" in v.motivo


def test_canhoto_limpa_lixo_nao_digito():
    v = avaliar(_r("NF 349498 -"), CANHOTO, None, None)
    assert v.texto_lido == "349498"


def test_pedido_um_campo_sobrevive():
    v = avaliar(_r("349498 - 38346X"), PEDIDO, None, None)
    assert v.aprovado is False
    assert v.texto_lido == "349498 - Não reconhecido"


def test_faixa_dentro():
    v = avaliar(_r("383462"), CANHOTO, 383400, 1000)
    assert v.aprovado is True


def test_faixa_fora():
    v = avaliar(_r("803464"), CANHOTO, 383400, 1000)
    assert v.aprovado is False
    assert v.texto_lido == "Não reconhecido"
    assert "fora" in v.motivo


def test_faixa_exige_ambos_parametros():
    # só seq, sem intervalo -> a regra de faixa é pulada
    v = avaliar(_r("803464"), CANHOTO, 383400, None)
    assert v.aprovado is True


def test_faixa_limite_inclusivo():
    v = avaliar(_r("384400"), CANHOTO, 383400, 1000)  # exatamente seq + intervalo
    assert v.aprovado is True


def test_faixa_so_no_campo_sequencial():
    # documento longe da sequência NÃO reprova; nota fora da faixa reprova
    ok = avaliar(_r("999999 - 383462"), PEDIDO_SEQ, 383400, 1000)
    assert ok.texto_lido == "999999 - 383462"
    assert ok.aprovado is True
    ruim = avaliar(_r("999999 - 803464"), PEDIDO_SEQ, 383400, 1000)
    assert ruim.texto_lido == "999999 - Não reconhecido"
    assert ruim.aprovado is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_validate.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.validate`)

- [ ] **Step 3: Implementar `validate.py`**

```python
from __future__ import annotations

import re

from leitor_lote.models import Reading, ResultadoValidado, Tipo

NAO_RECONHECIDO = "Não reconhecido"


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def avaliar(
    r: Reading,
    tipo: Tipo,
    seq_esperada: int | None,
    intervalo_maximo: int | None,
) -> ResultadoValidado:
    partes = [p.strip() for p in r.valor.split(" - ")]
    n = len(tipo.campos)
    if len(partes) < n:
        partes = partes + [""] * (n - len(partes))

    checa_faixa = seq_esperada is not None and intervalo_maximo is not None
    algum_sequencial = any(c.sequencial for c in tipo.campos)

    saidas: list[str] = []
    motivos: list[str] = []
    for campo, parte in zip(tipo.campos, partes[:n]):
        d = _digitos(parte)
        if len(d) != campo.tamanho:
            saidas.append(NAO_RECONHECIDO)
            motivos.append(f"{campo.nome}: {len(d)} dígitos (esperado {campo.tamanho})")
            continue
        aplica_faixa = checa_faixa and (campo.sequencial or not algum_sequencial)
        if aplica_faixa:
            valor = int(d)
            lo, hi = seq_esperada - intervalo_maximo, seq_esperada + intervalo_maximo
            if not (lo <= valor <= hi):
                saidas.append(NAO_RECONHECIDO)
                motivos.append(f"{campo.nome}: {valor} fora de {seq_esperada}±{intervalo_maximo}")
                continue
        saidas.append(d)

    aprovado = all(s != NAO_RECONHECIDO for s in saidas)
    return ResultadoValidado(
        texto_lido=" - ".join(saidas),
        aprovado=aprovado,
        motivo="; ".join(motivos) if motivos else None,
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_validate.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/validate.py tests/test_validate.py
git commit -m "feat: validacao deterministica de N dígitos + faixa seq±intervalo"
```

---

### Task 4: Config e tipos (`config.py` + `tipos.fallback.json`)

**Files:**
- Create: `leitor_lote/config.py`
- Create: `leitor_lote/tipos.fallback.json`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: `Tipo`, `Campo` de `leitor_lote.models`; `httpx`.
- Produces:
  - `Config` (dataclass mutável) com campos: `chave_openai: str | None = None`, `chave_mistral: str | None = None`, `ultima_pasta: str | None = None`, `motor_padrao: str | None = None`, `concorrencia: int = 5`, `limiar_confianca: float = 0.6`, `motor_ia_fallback: str = "openai:gpt-5-mini"`, `tipos_url: str = "https://raw.githubusercontent.com/GabrielFerrazzzzz/leitor-lote/main/tipos.json"`
  - `carregar() -> Config` — lê `CONFIG_PATH` (`%APPDATA%/leitor-lote/config.json`); se não existir, cria com defaults.
  - `salvar(c: Config) -> None`
  - `buscar_tipos(cfg: Config) -> dict[str, Tipo]` — `GET cfg.tipos_url` (timeout 5s); qualquer falha → carrega `tipos.fallback.json` embutido. Nunca levanta.
  - Constantes de módulo `APP_DIR: Path`, `CONFIG_PATH: Path`, `FALLBACK_PATH: Path` (testes fazem monkeypatch nelas).

- [ ] **Step 1: Escrever `tipos.fallback.json`**

```json
[
  {
    "id": "canhoto",
    "nome": "Canhoto",
    "modo": "auto",
    "motor": "paddleocr",
    "prompt": "Leia APENAS o número de 6 dígitos do canhoto. Responda só os dígitos, sem texto.",
    "campos": [{ "nome": "numero", "tamanho": 6, "sequencial": true }],
    "formato_exemplo": "349498"
  },
  {
    "id": "pedido",
    "nome": "Pedido",
    "modo": "auto",
    "motor": "paddleocr",
    "prompt": "Leia o número do documento (impresso) e o número da nota (manuscrito), ambos com 6 dígitos. Responda no formato '<documento> - <nota>', só dígitos.",
    "campos": [
      { "nome": "documento", "tamanho": 6, "sequencial": false },
      { "nome": "nota", "tamanho": 6, "sequencial": true }
    ],
    "formato_exemplo": "349498 - 383462"
  }
]
```

- [ ] **Step 2: Escrever os testes**

`tests/test_config.py`:
```python
import json

import httpx
import pytest

from leitor_lote import config as cfgmod
from leitor_lote.models import Tipo


@pytest.fixture
def _paths(tmp_path, monkeypatch):
    app_dir = tmp_path / "leitor-lote"
    monkeypatch.setattr(cfgmod, "APP_DIR", app_dir)
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", app_dir / "config.json")
    return app_dir


def test_carregar_cria_default(_paths):
    c = cfgmod.carregar()
    assert c.concorrencia == 5
    assert c.motor_ia_fallback == "openai:gpt-5-mini"
    assert (cfgmod.CONFIG_PATH).exists()


def test_salvar_roundtrip(_paths):
    c = cfgmod.carregar()
    c.chave_openai = "sk-teste"
    c.ultima_pasta = "C:/x"
    cfgmod.salvar(c)
    d = cfgmod.carregar()
    assert d.chave_openai == "sk-teste"
    assert d.ultima_pasta == "C:/x"


def test_buscar_tipos_usa_fallback_quando_url_falha(_paths, monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(httpx, "get", boom)
    tipos = cfgmod.buscar_tipos(cfgmod.carregar())
    assert set(tipos) == {"canhoto", "pedido"}
    assert isinstance(tipos["canhoto"], Tipo)
    assert tipos["pedido"].campos[1].nome == "nota"
    assert tipos["pedido"].campos[1].sequencial is True
    assert tipos["pedido"].campos[0].sequencial is False


def test_buscar_tipos_parseia_resposta_http(_paths, monkeypatch):
    payload = [
        {"id": "x", "nome": "X", "prompt": "p", "modo": "ocr", "motor": "tesseract",
         "campos": [{"nome": "n", "tamanho": 4}]}
    ]

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp())
    tipos = cfgmod.buscar_tipos(cfgmod.carregar())
    assert tipos["x"].campos[0].tamanho == 4
    assert tipos["x"].modo == "ocr"


def test_chave_nunca_alem_do_config(_paths):
    # a chave mora no config.json e em lugar nenhum mais; garante que salvar()
    # nao vaza pra stdout/log (aqui: nao ha outra escrita)
    c = cfgmod.carregar()
    c.chave_openai = "sk-secreta"
    cfgmod.salvar(c)
    conteudo = cfgmod.CONFIG_PATH.read_text("utf-8")
    assert "sk-secreta" in conteudo  # esperado: SÓ aqui
    assert json.loads(conteudo)["chave_openai"] == "sk-secreta"
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.config`)

- [ ] **Step 4: Implementar `config.py`**

```python
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from leitor_lote.models import Campo, Tipo

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "leitor-lote"
CONFIG_PATH = APP_DIR / "config.json"
FALLBACK_PATH = Path(__file__).with_name("tipos.fallback.json")


@dataclass
class Config:
    chave_openai: str | None = None
    chave_mistral: str | None = None
    ultima_pasta: str | None = None
    motor_padrao: str | None = None
    concorrencia: int = 5
    limiar_confianca: float = 0.6
    motor_ia_fallback: str = "openai:gpt-5-mini"
    tipos_url: str = "https://raw.githubusercontent.com/GabrielFerrazzzzz/leitor-lote/main/tipos.json"


def carregar() -> Config:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text("utf-8"))
        campos = Config.__dataclass_fields__
        return Config(**{k: v for k, v in data.items() if k in campos})
    c = Config()
    salvar(c)
    return c


def salvar(c: Config) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(c), indent=2, ensure_ascii=False), "utf-8")


def _parse_tipos(raw: list[dict]) -> dict[str, Tipo]:
    out: dict[str, Tipo] = {}
    for t in raw:
        campos_raw = t.get("campos") or [{"nome": "numero", "tamanho": 6, "sequencial": True}]
        campos = tuple(
            Campo(
                nome=c["nome"],
                tamanho=int(c.get("tamanho", 6)),
                sequencial=bool(c.get("sequencial", False)),
            )
            for c in campos_raw
        )
        out[t["id"]] = Tipo(
            id=t["id"],
            nome=t["nome"],
            prompt=t["prompt"],
            modo=t.get("modo", "auto"),
            motor=t.get("motor", "paddleocr"),
            campos=campos,
            formato_exemplo=t.get("formato_exemplo", ""),
        )
    return out


def buscar_tipos(cfg: Config) -> dict[str, Tipo]:
    try:
        resp = httpx.get(cfg.tipos_url, timeout=5.0)
        resp.raise_for_status()
        return _parse_tipos(resp.json())
    except Exception:
        return _parse_tipos(json.loads(FALLBACK_PATH.read_text("utf-8")))
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add leitor_lote/config.py leitor_lote/tipos.fallback.json tests/test_config.py
git commit -m "feat: config local (%APPDATA%) + tipos via URL com fallback embutido"
```

---

### Task 5: Pré-processamento de imagem (`preprocess.py`)

**Files:**
- Create: `leitor_lote/preprocess.py`
- Create: `tests/conftest.py`
- Create: `tests/test_preprocess.py`

**Interfaces:**
- Consumes: `PreparedImage` de `leitor_lote.models`; `PIL`, `cv2`, `numpy`, `pypdfium2`.
- Produces:
  - `preparar(arquivo: Path, *, para_ocr: bool) -> list[PreparedImage]` — orienta por EXIF; reduz se lado maior > `MAX_LADO` (2000); re-encoda JPEG q `JPEG_Q` (82); PDF → 1 `PreparedImage` por página (300 dpi via `pypdfium2`); imagem simples → lista de 1. `para_ocr=True` adiciona cinza + `cv2.adaptiveThreshold` + deskew (correção só de inclinações pequenas — ver `_deskew`).
  - `descartar(imagens: Iterable[PreparedImage]) -> None` — apaga o `caminho_tmp` de cada imagem (`unlink(missing_ok=True)`, engole erro). Quem chama `preparar` é dono da limpeza; nesta base é a `pipeline` (Task 12), num `finally` por arquivo.
  - Constantes `MAX_LADO = 2000`, `JPEG_Q = 82`.
- Fixtures (`conftest.py`): `png_pequeno` (100×200), `png_grande` (3000×2000), `pdf_2p` (PDF de 2 páginas).

- [ ] **Step 1: Escrever `conftest.py`**

```python
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def png_pequeno(tmp_path: Path) -> Path:
    p = tmp_path / "peq.png"
    Image.new("RGB", (100, 200), "white").save(p)
    return p


@pytest.fixture
def png_grande(tmp_path: Path) -> Path:
    p = tmp_path / "gr.png"
    Image.new("RGB", (3000, 2000), "white").save(p)
    return p


@pytest.fixture
def pdf_2p(tmp_path: Path) -> Path:
    p = tmp_path / "doc.pdf"
    a = Image.new("RGB", (400, 300), "white")
    b = Image.new("RGB", (400, 300), "gray")
    a.save(p, save_all=True, append_images=[b])
    return p
```

- [ ] **Step 2: Escrever os testes**

`tests/test_preprocess.py`:
```python
import cv2

from leitor_lote import preprocess
from leitor_lote.models import PreparedImage


def test_imagem_simples_retorna_lista_de_um(png_pequeno):
    out = preprocess.preparar(png_pequeno, para_ocr=False)
    assert len(out) == 1
    assert isinstance(out[0], PreparedImage)
    assert out[0].mimetype == "image/jpeg"
    assert out[0].caminho_tmp.exists()


def test_reduz_imagem_grande(png_grande):
    out = preprocess.preparar(png_grande, para_ocr=False)[0]
    assert max(out.largura, out.altura) <= preprocess.MAX_LADO


def test_pdf_vira_uma_imagem_por_pagina(pdf_2p):
    out = preprocess.preparar(pdf_2p, para_ocr=False)
    assert len(out) == 2
    assert all(x.mimetype == "image/jpeg" for x in out)


def test_para_ocr_aplica_threshold(png_pequeno, monkeypatch):
    chamado = {"n": 0}
    real = cv2.adaptiveThreshold

    def espia(*a, **k):
        chamado["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(cv2, "adaptiveThreshold", espia)
    preprocess.preparar(png_pequeno, para_ocr=True)
    assert chamado["n"] == 1
    chamado["n"] = 0
    preprocess.preparar(png_pequeno, para_ocr=False)
    assert chamado["n"] == 0


def test_deskew_nao_gira_imagem_alinhada(tmp_path):
    from PIL import Image, ImageDraw

    p = tmp_path / "barra.png"
    img = Image.new("RGB", (600, 200), "white")
    ImageDraw.Draw(img).rectangle([40, 90, 560, 110], fill="black")  # barra horizontal já alinhada
    img.save(p)
    out = preprocess.preparar(p, para_ocr=True)[0]
    assert out.largura > out.altura  # continua paisagem — não sofreu quarto de volta


def test_descarta_temporarios(png_pequeno):
    out = preprocess.preparar(png_pequeno, para_ocr=False)
    caminhos = [x.caminho_tmp for x in out]
    assert all(c.exists() for c in caminhos)
    preprocess.descartar(out)
    assert not any(c.exists() for c in caminhos)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_preprocess.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.preprocess`)

- [ ] **Step 4: Implementar `preprocess.py`**

```python
from __future__ import annotations

import io
import tempfile
from collections.abc import Iterable
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageOps

from leitor_lote.models import PreparedImage

MAX_LADO = 2000
JPEG_Q = 82
DPI = 300
SKEW_MAX_GRAUS = 15.0  # acima disso é ruído do minAreaRect, não inclinação real — não rotaciona


def _deskew(arr: np.ndarray) -> np.ndarray:
    # pontos escuros como (x, y) — np.where devolve (linha, col) = (y, x), então inverte
    coords = np.column_stack(np.where(arr < 255))[:, ::-1]
    if coords.shape[0] < 50:
        return arr
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    # OpenCV >=4.5: minAreaRect devolve angle em (0, 90]; normaliza pra (-45, 45]
    if angle > 45:
        angle -= 90
    if abs(angle) < 0.5 or abs(angle) > SKEW_MAX_GRAUS:
        return arr
    h, w = arr.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(arr, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _para_prepared(img: Image.Image, para_ocr: bool) -> PreparedImage:
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > MAX_LADO:
        img.thumbnail((MAX_LADO, MAX_LADO))
    if para_ocr:
        arr = np.array(img.convert("L"))
        arr = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
        )
        arr = _deskew(arr)
        saida = Image.fromarray(arr).convert("RGB")
    else:
        saida = img
    buf = io.BytesIO()
    saida.save(buf, format="JPEG", quality=JPEG_Q)
    dados = buf.getvalue()
    fd, nome = tempfile.mkstemp(suffix=".jpg")
    tmp = Path(nome)
    with open(fd, "wb") as f:
        f.write(dados)
    return PreparedImage(
        bytes_=dados,
        mimetype="image/jpeg",
        largura=saida.width,
        altura=saida.height,
        caminho_tmp=tmp,
    )


def preparar(arquivo: Path, *, para_ocr: bool) -> list[PreparedImage]:
    if arquivo.suffix.lower() == ".pdf":
        doc = pdfium.PdfDocument(str(arquivo))
        try:
            return [
                _para_prepared(doc[i].render(scale=DPI / 72).to_pil(), para_ocr)
                for i in range(len(doc))
            ]
        finally:
            doc.close()
    with Image.open(arquivo) as img:
        return [_para_prepared(img, para_ocr)]


def descartar(imagens: Iterable[PreparedImage]) -> None:
    for img in imagens:
        try:
            Path(img.caminho_tmp).unlink(missing_ok=True)
        except OSError:
            pass
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_preprocess.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add leitor_lote/preprocess.py tests/conftest.py tests/test_preprocess.py
git commit -m "feat: preprocess (EXIF, resize 2000/q82, PDF->paginas, threshold+deskew p/ OCR)"
```

---

### Task 6: Interface de motor e registry (`readers/base.py` + `readers/__init__.py`)

**Files:**
- Create: `leitor_lote/readers/base.py`
- Modify: `leitor_lote/readers/__init__.py`
- Create: `tests/fakes.py`
- Create: `tests/test_readers_registry.py`

**Interfaces:**
- Consumes: `PreparedImage`, `Reading`, `Tipo` de `leitor_lote.models`; `Config` de `leitor_lote.config`.
- Produces:
  - `readers/base.py`: `Reader` (`typing.Protocol`, `runtime_checkable`) com atributos `id: str`, `requer_chave: bool` e métodos `disponivel(self, config) -> bool`, `read(self, imagem: PreparedImage, tipo: Tipo) -> Reading`.
  - `readers/__init__.py`:
    - `MOTORES_IDS: list[str] = ["tesseract", "paddleocr", "trocr", "openai:gpt-5-mini", "openai:gpt-5", "mistral-ocr"]`
    - `LOCAIS: set[str] = {"tesseract", "paddleocr", "trocr"}`
    - `resolve(motor_id: str, config) -> Reader` — importa o módulo do reader **sob demanda** (evita puxar torch/paddle no import). `openai:<modelo>` → `OpenAIReader(modelo=<modelo>, chave=config.chave_openai)`. `mistral-ocr` → `MistralOcrReader(chave=config.chave_mistral)`. Id desconhecido → `ValueError`.
    - `disponivel(motor_id: str, config) -> bool` — `openai:*` exige `config.chave_openai`; `mistral-ocr` exige `config.chave_mistral`; locais sempre `True`.
  - `tests/fakes.py`: `FakeReader(valor="349498", confianca=0.9, falhar=False)` implementando `Reader`.

- [ ] **Step 1: Escrever `tests/fakes.py`**

```python
from leitor_lote.models import PreparedImage, Reading, Tipo


class FakeReader:
    id = "fake"
    requer_chave = False

    def __init__(self, valor: str = "349498", confianca: float | None = 0.9, falhar: bool = False):
        self._valor = valor
        self._conf = confianca
        self._falhar = falhar

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        if self._falhar:
            raise RuntimeError("boom")
        return Reading(valor=self._valor, confianca=self._conf, motor="fake", bruto=self._valor)
```

- [ ] **Step 2: Escrever os testes**

`tests/test_readers_registry.py`:
```python
import pytest

from leitor_lote import readers
from leitor_lote.config import Config
from leitor_lote.readers.base import Reader
from tests.fakes import FakeReader


def test_fake_satisfaz_protocolo():
    assert isinstance(FakeReader(), Reader)


def test_resolve_local():
    r = readers.resolve("tesseract", Config())
    assert r.id == "tesseract"


def test_resolve_openai_com_modelo():
    r = readers.resolve("openai:gpt-5", Config(chave_openai="sk-x"))
    assert r.modelo == "gpt-5"


def test_resolve_desconhecido():
    with pytest.raises(ValueError):
        readers.resolve("xpto", Config())


def test_disponivel_por_chave():
    assert readers.disponivel("openai:gpt-5-mini", Config(chave_openai="sk-x")) is True
    assert readers.disponivel("openai:gpt-5-mini", Config()) is False
    assert readers.disponivel("mistral-ocr", Config()) is False
    assert readers.disponivel("paddleocr", Config()) is True
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_readers_registry.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.readers.base`)

- [ ] **Step 4: Implementar `readers/base.py`**

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from leitor_lote.models import PreparedImage, Reading, Tipo


@runtime_checkable
class Reader(Protocol):
    id: str
    requer_chave: bool

    def disponivel(self, config) -> bool: ...

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading: ...
```

- [ ] **Step 5: Implementar `readers/__init__.py`**

```python
from __future__ import annotations

from leitor_lote.readers.base import Reader

MOTORES_IDS: list[str] = [
    "tesseract",
    "paddleocr",
    "trocr",
    "openai:gpt-5-mini",
    "openai:gpt-5",
    "mistral-ocr",
]
LOCAIS: set[str] = {"tesseract", "paddleocr", "trocr"}


def resolve(motor_id: str, config) -> Reader:
    base, _, modelo = motor_id.partition(":")
    if base == "tesseract":
        from leitor_lote.readers.tesseract_reader import TesseractReader

        return TesseractReader()
    if base == "paddleocr":
        from leitor_lote.readers.paddleocr_reader import PaddleOcrReader

        return PaddleOcrReader()
    if base == "trocr":
        from leitor_lote.readers.trocr_reader import TrOcrReader

        return TrOcrReader()
    if base == "openai":
        from leitor_lote.readers.openai_reader import OpenAIReader

        return OpenAIReader(modelo=modelo or "gpt-5-mini", chave=config.chave_openai)
    if base == "mistral-ocr":
        from leitor_lote.readers.mistral_reader import MistralOcrReader

        return MistralOcrReader(chave=config.chave_mistral)
    raise ValueError(f"motor desconhecido: {motor_id}")


def disponivel(motor_id: str, config) -> bool:
    base = motor_id.split(":")[0]
    if base == "openai":
        return bool(config.chave_openai)
    if base == "mistral-ocr":
        return bool(config.chave_mistral)
    return True
```

Nota: `test_resolve_local` e os testes de `openai`/`mistral` dependem das Tasks 7–11 existirem. Ordene 7–11 antes de rodar a suíte inteira; para fechar a Task 6 isoladamente, rode só `test_fake_satisfaz_protocolo`, `test_resolve_desconhecido` e `test_disponivel_por_chave`.

- [ ] **Step 6: Rodar o subconjunto que não depende dos readers concretos**

Run: `uv run pytest tests/test_readers_registry.py -v -k "protocolo or desconhecido or por_chave"`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add leitor_lote/readers/ tests/fakes.py tests/test_readers_registry.py
git commit -m "feat: Protocol Reader + registry com resolve()/disponivel() lazy"
```

---

### Task 7: `TesseractReader`

**Files:**
- Create: `leitor_lote/readers/tesseract_reader.py`
- Create: `tests/test_tesseract_reader.py`

**Interfaces:**
- Consumes: `PreparedImage`, `Reading`, `Tipo`; `pytesseract`, `PIL.Image`.
- Produces: `TesseractReader` (`id="tesseract"`, `requer_chave=False`). `read()` roda `pytesseract.image_to_data` (`--psm 7`, whitelist `0123456789`), junta os tokens em `valor`, média das confianças `>= 0` normalizada por 100 em `confianca` (`None` se não houver), `bruto` = `repr` dos tokens.

- [ ] **Step 1: Escrever o teste (monkeypatch) + o manual**

`tests/test_tesseract_reader.py`:
```python
import pytest

from leitor_lote.models import Campo, PreparedImage, Tipo
from leitor_lote.readers.tesseract_reader import TesseractReader

TIPO = Tipo(id="canhoto", nome="C", prompt="", modo="ocr", motor="tesseract",
            campos=(Campo("numero", 6),))


def _img(tmp_path):
    from PIL import Image

    p = tmp_path / "x.jpg"
    Image.new("RGB", (200, 60), "white").save(p)
    return PreparedImage(bytes_=b"x", mimetype="image/jpeg", largura=200, altura=60, caminho_tmp=p)


def test_read_junta_tokens_e_confianca(tmp_path, monkeypatch):
    import pytesseract

    fake = {"text": ["34", "", "9498"], "conf": ["90", "-1", "80"]}
    monkeypatch.setattr(pytesseract, "image_to_data", lambda *a, **k: fake)
    r = TesseractReader().read(_img(tmp_path), TIPO)
    assert r.valor == "349498"
    assert r.motor == "tesseract"
    assert abs(r.confianca - 0.85) < 1e-6


@pytest.mark.manual
def test_read_real(tmp_path):
    from PIL import Image, ImageDraw

    p = tmp_path / "n.jpg"
    img = Image.new("RGB", (240, 80), "white")
    ImageDraw.Draw(img).text((20, 25), "349498", fill="black")
    img.save(p)
    pi = PreparedImage(bytes_=p.read_bytes(), mimetype="image/jpeg", largura=240, altura=80,
                       caminho_tmp=p)
    r = TesseractReader().read(pi, TIPO)
    assert "349498" in r.valor
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_tesseract_reader.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.readers.tesseract_reader`)

- [ ] **Step 3: Implementar `tesseract_reader.py`**

```python
from __future__ import annotations

import pytesseract
from PIL import Image

from leitor_lote.models import PreparedImage, Reading, Tipo

_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789"


class TesseractReader:
    id = "tesseract"
    requer_chave = False

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        with Image.open(imagem.caminho_tmp) as img:
            data = pytesseract.image_to_data(
                img, config=_CONFIG, output_type=pytesseract.Output.DICT
            )
        tokens = [(t, c) for t, c in zip(data["text"], data["conf"]) if t.strip()]
        valor = "".join(t for t, _ in tokens)
        confs = [int(c) for _, c in tokens if str(c).lstrip("-").isdigit() and int(c) >= 0]
        conf = (sum(confs) / len(confs) / 100.0) if confs else None
        return Reading(valor=valor, confianca=conf, motor="tesseract", bruto=repr(tokens))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_tesseract_reader.py -v`
Expected: PASS (1 passed, 1 deselected)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/readers/tesseract_reader.py tests/test_tesseract_reader.py
git commit -m "feat: TesseractReader (pytesseract, psm 7, whitelist de digitos)"
```

---

### Task 8: `PaddleOcrReader`

**Files:**
- Create: `leitor_lote/readers/paddleocr_reader.py`
- Create: `tests/test_paddleocr_reader.py`

**Interfaces:**
- Consumes: `PreparedImage`, `Reading`, `Tipo`; `paddleocr.PaddleOCR`.
- Produces: `PaddleOcrReader` (`id="paddleocr"`, `requer_chave=False`). Engine carregada uma vez via `functools.cache` em `_engine()`. `read()` chama `_engine().ocr(caminho, cls=True)`, extrai só dígitos dos textos em `valor`, média dos scores em `confianca`, `bruto` = `str(linhas)`.

- [ ] **Step 1: Escrever os testes**

`tests/test_paddleocr_reader.py`:
```python
import pytest

from leitor_lote.models import Campo, PreparedImage, Tipo
from leitor_lote.readers import paddleocr_reader
from leitor_lote.readers.paddleocr_reader import PaddleOcrReader

TIPO = Tipo(id="canhoto", nome="C", prompt="", modo="ocr", motor="paddleocr",
            campos=(Campo("numero", 6),))


def _img(tmp_path):
    from PIL import Image

    p = tmp_path / "x.jpg"
    Image.new("RGB", (200, 60), "white").save(p)
    return PreparedImage(bytes_=b"x", mimetype="image/jpeg", largura=200, altura=60, caminho_tmp=p)


def test_read_extrai_digitos_e_media_de_score(tmp_path, monkeypatch):
    class _Eng:
        def ocr(self, caminho, cls=True):
            return [[[[[0, 0]], ("NF 3494", 0.9)], [[[0, 0]], ("98", 0.8)]]]

    monkeypatch.setattr(paddleocr_reader, "_engine", lambda: _Eng())
    r = PaddleOcrReader().read(_img(tmp_path), TIPO)
    assert r.valor == "349498"
    assert abs(r.confianca - 0.85) < 1e-6
    assert r.motor == "paddleocr"


@pytest.mark.manual
def test_read_real(tmp_path):
    from PIL import Image, ImageDraw

    p = tmp_path / "n.jpg"
    img = Image.new("RGB", (240, 80), "white")
    ImageDraw.Draw(img).text((20, 25), "349498", fill="black")
    img.save(p)
    pi = PreparedImage(bytes_=p.read_bytes(), mimetype="image/jpeg", largura=240, altura=80,
                       caminho_tmp=p)
    r = PaddleOcrReader().read(pi, TIPO)
    assert "349498" in r.valor
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_paddleocr_reader.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementar `paddleocr_reader.py`**

```python
from __future__ import annotations

from functools import cache

from leitor_lote.models import PreparedImage, Reading, Tipo


@cache
def _engine():
    from paddleocr import PaddleOCR

    return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)


class PaddleOcrReader:
    id = "paddleocr"
    requer_chave = False

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        res = _engine().ocr(str(imagem.caminho_tmp), cls=True)
        linhas = res[0] if res else []
        textos: list[str] = []
        scores: list[float] = []
        for _, (txt, score) in linhas:
            textos.append(txt)
            scores.append(float(score))
        valor = "".join(ch for ch in "".join(textos) if ch.isdigit())
        conf = (sum(scores) / len(scores)) if scores else None
        return Reading(valor=valor, confianca=conf, motor="paddleocr", bruto=str(linhas))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_paddleocr_reader.py -v`
Expected: PASS (1 passed, 1 deselected)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/readers/paddleocr_reader.py tests/test_paddleocr_reader.py
git commit -m "feat: PaddleOcrReader (engine cacheada, extrai digitos + media de score)"
```

---

### Task 9: `TrOcrReader`

**Files:**
- Create: `leitor_lote/readers/trocr_reader.py`
- Create: `tests/test_trocr_reader.py`

**Interfaces:**
- Consumes: `PreparedImage`, `Reading`, `Tipo`; `transformers`, `torch`, `PIL.Image`.
- Produces: `TrOcrReader` (`id="trocr"`, `requer_chave=False`). `_pipe()` (cache) baixa/carrega `microsoft/trocr-large-handwritten` em `CACHE_DIR` (`%LOCALAPPDATA%/leitor-lote/models`). `read()` gera texto (`max_new_tokens=32`), `valor` = só dígitos, `confianca=None`, `bruto` = texto cru.

- [ ] **Step 1: Escrever os testes**

`tests/test_trocr_reader.py`:
```python
import pytest

from leitor_lote.models import Campo, PreparedImage, Tipo
from leitor_lote.readers import trocr_reader
from leitor_lote.readers.trocr_reader import TrOcrReader

TIPO = Tipo(id="canhoto", nome="C", prompt="", modo="ocr", motor="trocr",
            campos=(Campo("numero", 6),))


def _img(tmp_path):
    from PIL import Image

    p = tmp_path / "x.jpg"
    Image.new("RGB", (200, 60), "white").save(p)
    return PreparedImage(bytes_=b"x", mimetype="image/jpeg", largura=200, altura=60, caminho_tmp=p)


def test_read_extrai_digitos_sem_confianca(tmp_path, monkeypatch):
    class _Proc:
        def __call__(self, images, return_tensors):
            class _T:
                pixel_values = "PV"

            return _T()

        def batch_decode(self, ids, skip_special_tokens):
            return ["nota 349498 "]

    class _Model:
        def generate(self, pixel_values, max_new_tokens):
            return ["ids"]

    monkeypatch.setattr(trocr_reader, "_pipe", lambda: (_Proc(), _Model()))
    r = TrOcrReader().read(_img(tmp_path), TIPO)
    assert r.valor == "349498"
    assert r.confianca is None
    assert r.motor == "trocr"


@pytest.mark.manual
def test_read_real(tmp_path):
    from PIL import Image, ImageDraw

    p = tmp_path / "n.jpg"
    img = Image.new("RGB", (240, 80), "white")
    ImageDraw.Draw(img).text((20, 25), "349498", fill="black")
    img.save(p)
    pi = PreparedImage(bytes_=p.read_bytes(), mimetype="image/jpeg", largura=240, altura=80,
                       caminho_tmp=p)
    r = TrOcrReader().read(pi, TIPO)
    assert r.valor.isdigit()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_trocr_reader.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementar `trocr_reader.py`**

```python
from __future__ import annotations

import os
from functools import cache
from pathlib import Path

from PIL import Image

from leitor_lote.models import PreparedImage, Reading, Tipo

MODEL_ID = "microsoft/trocr-large-handwritten"
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "leitor-lote" / "models"


@cache
def _pipe():
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    proc = TrOCRProcessor.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
    return proc, model


class TrOcrReader:
    id = "trocr"
    requer_chave = False

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        proc, model = _pipe()
        with Image.open(imagem.caminho_tmp) as img:
            rgb = img.convert("RGB")
        pixel_values = proc(images=rgb, return_tensors="pt").pixel_values
        ids = model.generate(pixel_values, max_new_tokens=32)
        texto = proc.batch_decode(ids, skip_special_tokens=True)[0]
        valor = "".join(ch for ch in texto if ch.isdigit())
        return Reading(valor=valor, confianca=None, motor="trocr", bruto=texto)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_trocr_reader.py -v`
Expected: PASS (1 passed, 1 deselected)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/readers/trocr_reader.py tests/test_trocr_reader.py
git commit -m "feat: TrOcrReader (microsoft/trocr-large-handwritten, download sob demanda)"
```

---

### Task 10: `OpenAIReader`

**Files:**
- Create: `leitor_lote/readers/openai_reader.py`
- Create: `tests/test_openai_reader.py`

**Interfaces:**
- Consumes: `PreparedImage`, `Reading`, `Tipo`; `httpx`, `base64`, `time`.
- Produces: `OpenAIReader(modelo: str = "gpt-5-mini", chave: str | None = None)` (`id="openai"`, `requer_chave=True`). `read()` porta o `lerArquivoComIA` do worker: `POST https://api.openai.com/v1/responses`, `content` = `[{input_image, image_url: data:<mime>;base64,...}, {input_text, text: tipo.prompt}]`, `max_output_tokens=300`; até 3 tentativas com backoff (`time.sleep(tentativa*2)`) em 429/5xx; sucesso → `Reading(valor=texto, confianca=None, motor=f"openai:{modelo}", bruto=texto)`. `bruto` **nunca** contém a chave.

- [ ] **Step 1: Escrever os testes**

`tests/test_openai_reader.py`:
```python
import httpx
import pytest

from leitor_lote.models import Campo, PreparedImage, Tipo
from leitor_lote.readers.openai_reader import OpenAIReader

TIPO = Tipo(id="canhoto", nome="C", prompt="leia", modo="ia", motor="openai:gpt-5-mini",
            campos=(Campo("numero", 6),))
IMG = PreparedImage(bytes_=b"abc", mimetype="image/jpeg", largura=1, altura=1, caminho_tmp=None)


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erro", request=None, response=None)


def test_retry_em_429_depois_sucesso(monkeypatch):
    respostas = [
        _Resp(429),
        _Resp(200, {"output": [{"content": [{"text": " 349498 "}]}]}),
    ]
    chamadas = {"n": 0}

    def fake_post(url, **kw):
        chamadas["n"] += 1
        return respostas.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = OpenAIReader(modelo="gpt-5-mini", chave="sk-secreta").read(IMG, TIPO)
    assert chamadas["n"] == 2
    assert r.valor == "349498"
    assert r.motor == "openai:gpt-5-mini"
    assert "sk-secreta" not in r.bruto


def test_disponivel_exige_chave():
    from leitor_lote.config import Config

    assert OpenAIReader(chave="sk-x").disponivel(Config()) is True
    assert OpenAIReader().disponivel(Config()) is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_openai_reader.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementar `openai_reader.py`**

```python
from __future__ import annotations

import base64
import time

import httpx

from leitor_lote.models import PreparedImage, Reading, Tipo

URL = "https://api.openai.com/v1/responses"


class OpenAIReader:
    id = "openai"
    requer_chave = True

    def __init__(self, modelo: str = "gpt-5-mini", chave: str | None = None):
        self.modelo = modelo
        self.chave = chave

    def disponivel(self, config) -> bool:
        return bool(self.chave or (config and config.chave_openai))

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        data_url = f"data:{imagem.mimetype};base64,{base64.b64encode(imagem.bytes_).decode()}"
        body = {
            "model": self.modelo,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_image", "detail": "auto", "image_url": data_url},
                        {"type": "input_text", "text": tipo.prompt},
                    ],
                }
            ],
            "max_output_tokens": 300,
        }
        headers = {"Authorization": f"Bearer {self.chave}", "Content-Type": "application/json"}
        ultimo: Exception | None = None
        for tentativa in range(1, 4):
            try:
                r = httpx.post(URL, json=body, headers=headers, timeout=60.0)
                if (r.status_code == 429 or r.status_code >= 500) and tentativa < 3:
                    time.sleep(tentativa * 2)
                    continue
                r.raise_for_status()
                texto = r.json()["output"][0]["content"][0]["text"].strip()
                return Reading(
                    valor=texto, confianca=None, motor=f"openai:{self.modelo}", bruto=texto
                )
            except Exception as e:  # noqa: BLE001
                ultimo = e
                if tentativa < 3:
                    time.sleep(tentativa)
        raise RuntimeError(f"OpenAI falhou apos 3 tentativas: {ultimo}")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_openai_reader.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/readers/openai_reader.py tests/test_openai_reader.py
git commit -m "feat: OpenAIReader (Responses API, input_image, retry/backoff 429/5xx)"
```

---

### Task 11: `MistralOcrReader`

**Files:**
- Create: `leitor_lote/readers/mistral_reader.py`
- Create: `tests/test_mistral_reader.py`

**Interfaces:**
- Consumes: `PreparedImage`, `Reading`, `Tipo`; `httpx`, `base64`.
- Produces: `MistralOcrReader(chave: str | None = None)` (`id="mistral-ocr"`, `requer_chave=True`). `read()`: `POST https://api.mistral.ai/v1/ocr`, body `{"model": "mistral-ocr-latest", "document": {"type": "image_url", "image_url": "data:<mime>;base64,..."}}`; junta `pages[].markdown` em `bruto`, `valor` = só dígitos; `confianca=None`.

- [ ] **Step 1: Escrever os testes**

`tests/test_mistral_reader.py`:
```python
import httpx
import pytest

from leitor_lote.config import Config
from leitor_lote.models import Campo, PreparedImage, Tipo
from leitor_lote.readers.mistral_reader import MistralOcrReader

TIPO = Tipo(id="canhoto", nome="C", prompt="", modo="ia", motor="mistral-ocr",
            campos=(Campo("numero", 6),))
IMG = PreparedImage(bytes_=b"abc", mimetype="image/jpeg", largura=1, altura=1, caminho_tmp=None)


def test_read_junta_paginas_e_extrai_digitos(monkeypatch):
    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"pages": [{"markdown": "nota: 3494"}, {"markdown": "98 fim"}]}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    r = MistralOcrReader(chave="key").read(IMG, TIPO)
    assert r.valor == "349498"
    assert r.motor == "mistral-ocr"
    assert "key" not in r.bruto


def test_disponivel_exige_chave():
    assert MistralOcrReader(chave="k").disponivel(Config()) is True
    assert MistralOcrReader().disponivel(Config()) is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_mistral_reader.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementar `mistral_reader.py`**

```python
from __future__ import annotations

import base64

import httpx

from leitor_lote.models import PreparedImage, Reading, Tipo

URL = "https://api.mistral.ai/v1/ocr"


class MistralOcrReader:
    id = "mistral-ocr"
    requer_chave = True

    def __init__(self, chave: str | None = None):
        self.chave = chave

    def disponivel(self, config) -> bool:
        return bool(self.chave or (config and config.chave_mistral))

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        data_url = f"data:{imagem.mimetype};base64,{base64.b64encode(imagem.bytes_).decode()}"
        body = {
            "model": "mistral-ocr-latest",
            "document": {"type": "image_url", "image_url": data_url},
        }
        headers = {"Authorization": f"Bearer {self.chave}", "Content-Type": "application/json"}
        r = httpx.post(URL, json=body, headers=headers, timeout=60.0)
        r.raise_for_status()
        texto = "\n".join(p.get("markdown", "") for p in r.json().get("pages", [])).strip()
        valor = "".join(ch for ch in texto if ch.isdigit())
        return Reading(valor=valor, confianca=None, motor="mistral-ocr", bruto=texto)
```

- [ ] **Step 4: Rodar e ver passar (suíte inteira do registry agora fecha)**

Run: `uv run pytest tests/test_mistral_reader.py tests/test_readers_registry.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/readers/mistral_reader.py tests/test_mistral_reader.py
git commit -m "feat: MistralOcrReader (endpoint /v1/ocr, junta markdown das paginas)"
```

---

### Task 12: Orquestração (`pipeline.py`)

**Files:**
- Create: `leitor_lote/pipeline.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `ParametrosRodada`, `LinhaResultado`, `Tipo` de `models`; `Config` de `config`; `resolve`, `disponivel` de `readers`; `preparar`, `descartar` de `preprocess`; `avaliar` de `validate`.
- Produces:
  - `rodar(p: ParametrosRodada, cfg: Config, tipos: dict[str, Tipo], progresso: Callable[[int, int], None], cancel: threading.Event | None = None) -> list[LinhaResultado]`
  - `EXT_OK: set[str] = {".jpg", ".jpeg", ".png", ".pdf"}`
  - Comportamento: lista arquivos suportados (não recursivo, ordenado); `ThreadPoolExecutor(max_workers=max(1, cfg.concorrencia))`; por arquivo — `preparar(para_ocr = p.modo != "ia")`, `resolve(p.motor_id).read` em cada página, `avaliar`; para na 1ª página aprovada. Se `p.modo == "auto"` e (`not aprovado` **ou** `confianca` não-`None` e `< cfg.limiar_confianca`) e `disponivel(cfg.motor_ia_fallback, cfg)` → refaz com `resolve(cfg.motor_ia_fallback)` sobre `preparar(para_ocr=False)`. Exceção no arquivo → `LinhaResultado(status="erro", erro=str(e))`. `cancel.is_set()` → não agenda mais e marca `erro="cancelado"`. `progresso(feitos, total)` chamado uma vez com `(0, total)` e depois a cada arquivo concluído. **Toda lista devolvida por `preparar` (a do caminho principal e a do fallback) é passada pra `descartar` num `finally` por arquivo — os temporários nunca vazam.**

- [ ] **Step 1: Escrever os testes**

`tests/test_pipeline.py`:
```python
import threading
from pathlib import Path

import pytest
from PIL import Image

from leitor_lote import pipeline
from leitor_lote.config import Config
from leitor_lote.models import Campo, ParametrosRodada, PreparedImage, Reading, Tipo

CANHOTO = Tipo(id="canhoto", nome="C", prompt="", modo="auto", motor="paddleocr",
               campos=(Campo("numero", 6),))
TIPOS = {"canhoto": CANHOTO}


@pytest.fixture(autouse=True)
def _stub_descartar(monkeypatch):
    # o pipeline chama preprocess.descartar num finally; nestes testes preparar é
    # mockado, então descartar não tem o que fazer — neutraliza pra isolar a orquestração
    monkeypatch.setattr(pipeline, "descartar", lambda *a, **k: None)


def _pasta(tmp_path: Path, n: int) -> Path:
    d = tmp_path / "entrada"
    d.mkdir()
    for i in range(n):
        Image.new("RGB", (50, 50), "white").save(d / f"img{i:02d}.png")
    return d


def _prepared(tmp_path):
    p = tmp_path / "t.jpg"
    p.write_bytes(b"x")
    return [PreparedImage(bytes_=b"x", mimetype="image/jpeg", largura=1, altura=1, caminho_tmp=p)]


def _params(pasta, modo="ocr", motor="paddleocr"):
    return ParametrosRodada(pasta_entrada=pasta, tipo_id="canhoto", motor_id=motor, modo=modo,
                            seq_esperada=None, intervalo_maximo=None)


def test_ok_simples(tmp_path, monkeypatch):
    pasta = _pasta(tmp_path, 3)
    monkeypatch.setattr(pipeline, "preparar", lambda *a, **k: _prepared(tmp_path))

    class _R:
        def read(self, img, tipo):
            return Reading(valor="349498", confianca=0.9, motor="paddleocr", bruto="")

    monkeypatch.setattr(pipeline, "resolve", lambda mid, cfg: _R())
    vistos = []
    out = pipeline.rodar(_params(pasta), Config(), TIPOS, lambda f, t: vistos.append((f, t)))
    assert [l.status for l in out] == ["ok", "ok", "ok"]
    assert vistos[0] == (0, 3)
    assert vistos[-1] == (3, 3)


def test_auto_cai_pro_fallback_quando_ocr_reprova(tmp_path, monkeypatch):
    pasta = _pasta(tmp_path, 1)
    monkeypatch.setattr(pipeline, "preparar", lambda *a, **k: _prepared(tmp_path))

    class _OCR:
        def read(self, img, tipo):
            return Reading(valor="12", confianca=0.2, motor="paddleocr", bruto="")

    class _IA:
        def read(self, img, tipo):
            return Reading(valor="349498", confianca=None, motor="openai:gpt-5-mini", bruto="")

    monkeypatch.setattr(pipeline, "resolve",
                        lambda mid, cfg: _IA() if mid.startswith("openai") else _OCR())
    monkeypatch.setattr(pipeline, "disponivel", lambda mid, cfg: True)
    out = pipeline.rodar(_params(pasta, modo="auto"), Config(chave_openai="sk"), TIPOS,
                         lambda f, t: None)
    assert out[0].status == "ok"
    assert out[0].texto_lido == "349498"
    assert out[0].motor == "openai:gpt-5-mini"


def test_respeita_limite_de_concorrencia(tmp_path, monkeypatch):
    pasta = _pasta(tmp_path, 10)
    monkeypatch.setattr(pipeline, "preparar", lambda *a, **k: _prepared(tmp_path))
    ativos = {"n": 0, "max": 0}
    lock = threading.Lock()

    class _R:
        def read(self, img, tipo):
            with lock:
                ativos["n"] += 1
                ativos["max"] = max(ativos["max"], ativos["n"])
            import time

            time.sleep(0.02)
            with lock:
                ativos["n"] -= 1
            return Reading(valor="349498", confianca=0.9, motor="paddleocr", bruto="")

    monkeypatch.setattr(pipeline, "resolve", lambda mid, cfg: _R())
    pipeline.rodar(_params(pasta), Config(concorrencia=3), TIPOS, lambda f, t: None)
    assert ativos["max"] <= 3


def test_cancelado_marca_erro(tmp_path, monkeypatch):
    pasta = _pasta(tmp_path, 4)
    monkeypatch.setattr(pipeline, "preparar", lambda *a, **k: _prepared(tmp_path))
    monkeypatch.setattr(pipeline, "resolve", lambda mid, cfg: None)
    ev = threading.Event()
    ev.set()
    out = pipeline.rodar(_params(pasta), Config(), TIPOS, lambda f, t: None, cancel=ev)
    assert all(l.status == "erro" and l.erro == "cancelado" for l in out)


def test_descarta_temporarios_de_cada_arquivo(tmp_path, monkeypatch):
    pasta = _pasta(tmp_path, 3)
    monkeypatch.setattr(pipeline, "preparar", lambda *a, **k: _prepared(tmp_path))
    monkeypatch.setattr(pipeline, "resolve",
                        lambda mid, cfg: type("R", (), {"read": lambda s, i, t:
                            Reading(valor="349498", confianca=0.9, motor="paddleocr", bruto="")})())
    descartados = []
    monkeypatch.setattr(pipeline, "descartar", lambda imgs: descartados.append(list(imgs)))
    pipeline.rodar(_params(pasta), Config(), TIPOS, lambda f, t: None)
    assert len(descartados) == 3  # um finally por arquivo
    assert all(len(lote) >= 1 for lote in descartados)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.pipeline`)

- [ ] **Step 3: Implementar `pipeline.py`**

```python
from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from leitor_lote.config import Config
from leitor_lote.models import LinhaResultado, ParametrosRodada, Tipo
from leitor_lote.preprocess import descartar, preparar
from leitor_lote.readers import disponivel, resolve
from leitor_lote.validate import avaliar

EXT_OK: set[str] = {".jpg", ".jpeg", ".png", ".pdf"}


def _arquivos(pasta: Path) -> list[Path]:
    return sorted(
        p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXT_OK
    )


def _melhor_de_paginas(reader, paginas, tipo, p):
    melhor = None
    for img in paginas:
        leitura = reader.read(img, tipo)
        v = avaliar(leitura, tipo, p.seq_esperada, p.intervalo_maximo)
        if v.aprovado:
            return leitura, v
        melhor = melhor or (leitura, v)
    return melhor


def _ler_um(arquivo: Path, p: ParametrosRodada, cfg: Config, tipo: Tipo,
            cancel: threading.Event) -> LinhaResultado:
    if cancel.is_set():
        return LinhaResultado(arquivo.name, "", None, "", "erro", "cancelado")
    preparados: list = []
    try:
        paginas = preparar(arquivo, para_ocr=p.modo != "ia")
        preparados.extend(paginas)
        reader = resolve(p.motor_id, cfg)
        leitura, v = _melhor_de_paginas(reader, paginas, tipo, p)

        if p.modo == "auto":
            baixa_conf = leitura.confianca is not None and leitura.confianca < cfg.limiar_confianca
            if (not v.aprovado or baixa_conf) and disponivel(cfg.motor_ia_fallback, cfg):
                r2 = resolve(cfg.motor_ia_fallback, cfg)
                paginas_ia = preparar(arquivo, para_ocr=False)
                preparados.extend(paginas_ia)
                res2 = _melhor_de_paginas(r2, paginas_ia, tipo, p)
                if res2 and (res2[1].aprovado or not v.aprovado):
                    leitura, v = res2

        status = "ok" if v.aprovado else "nao_reconhecido"
        return LinhaResultado(arquivo.name, v.texto_lido, leitura.confianca, leitura.motor,
                              status, None)
    except Exception as e:  # noqa: BLE001
        return LinhaResultado(arquivo.name, "", None, "", "erro", str(e))
    finally:
        descartar(preparados)


def rodar(
    p: ParametrosRodada,
    cfg: Config,
    tipos: dict[str, Tipo],
    progresso: Callable[[int, int], None],
    cancel: threading.Event | None = None,
) -> list[LinhaResultado]:
    cancel = cancel or threading.Event()
    tipo = tipos[p.tipo_id]
    arquivos = _arquivos(p.pasta_entrada)
    total = len(arquivos)
    progresso(0, total)

    resultados: list[LinhaResultado] = []
    feitos = 0
    with ThreadPoolExecutor(max_workers=max(1, cfg.concorrencia)) as ex:
        futs = [ex.submit(_ler_um, a, p, cfg, tipo, cancel) for a in arquivos]
        for fut in as_completed(futs):
            resultados.append(fut.result())
            feitos += 1
            progresso(feitos, total)

    resultados.sort(key=lambda r: r.arquivo)
    return resultados
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add leitor_lote/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline (pool limitado, modo ocr/ia/auto com fallback, cancelamento)"
```

---

### Task 13: Saída em disco + janela (`output.py`, `gui.py`, `__main__.py`)

**Files:**
- Create: `leitor_lote/output.py`
- Create: `leitor_lote/gui.py`
- Create: `leitor_lote/__main__.py`
- Create: `tests/test_output.py`
- Create: `tests/test_gui_helpers.py`

**Interfaces:**
- Consumes: `LinhaResultado` de `models`; `Config`, `carregar`, `salvar`, `buscar_tipos` de `config`; `ParametrosRodada` de `models`; `rodar` de `pipeline`; `MOTORES_IDS`, `LOCAIS`, `disponivel` de `readers`.
- Produces:
  - `output.gravar(linhas: list[LinhaResultado], pasta_saida: Path) -> None` — `pasta_entrada = pasta_saida.parent`; cria `pasta_saida`; para cada linha grava linha no `resultado.csv` (`utf-8-sig`, colunas `arquivo,texto_lido,confianca,motor,status,erro`) e copia o arquivo de origem pra `pasta_saida` com nome `limpar_nome(texto_lido)` (+ `ERRO_` se `status=="erro"`, usando o nome original) + extensão original, com sufixo `_2/_3` em colisão; escreve `log.txt`.
  - `output.limpar_nome(s: str) -> str` — NFKD→ascii, upper, `[^A-Z0-9]+`→`_`, strip `_`; vazio → `"SEM_LEITURA"`.
  - `gui.opcoes_motor(modo: str, cfg: Config) -> list[tuple[str, bool]]` — ids válidos pro modo (`ocr`/`auto` = locais; `ia` = API), cada um com `disponivel(id, cfg)`.
  - `gui.montar_parametros(pasta: str, tipo_id: str, motor_id: str, modo: str, seq: str, intervalo: str) -> ParametrosRodada` — strings vazias viram `None`.
  - `gui.rodar_janela() -> None` — a janela Tkinter (testada manual).
  - `__main__.py` chama `gui.rodar_janela()`.

- [ ] **Step 1: Escrever `tests/test_output.py`**

```python
from pathlib import Path

from leitor_lote import output
from leitor_lote.models import LinhaResultado


def test_limpar_nome():
    assert output.limpar_nome("São Paulo 12!") == "SAO_PAULO_12"
    assert output.limpar_nome("---") == "SEM_LEITURA"


def _entrada(tmp_path: Path, nomes: list[str]) -> Path:
    d = tmp_path / "entrada"
    d.mkdir()
    for n in nomes:
        (d / n).write_bytes(b"conteudo")
    return d


def test_grava_csv_com_bom_e_cabecalho(tmp_path):
    ent = _entrada(tmp_path, ["a.jpg"])
    linhas = [LinhaResultado("a.jpg", "349498", 0.91, "paddleocr", "ok", None)]
    output.gravar(linhas, ent / "saida")
    csv_bytes = (ent / "saida" / "resultado.csv").read_bytes()
    assert csv_bytes[:3] == b"\xef\xbb\xbf"
    assert csv_bytes.decode("utf-8-sig").splitlines()[0] == "arquivo,texto_lido,confianca,motor,status,erro"
    assert (ent / "saida" / "349498.jpg").exists()


def test_colisao_ganha_sufixo(tmp_path):
    ent = _entrada(tmp_path, ["a.jpg", "b.jpg"])
    linhas = [
        LinhaResultado("a.jpg", "Não reconhecido", None, "paddleocr", "nao_reconhecido", None),
        LinhaResultado("b.jpg", "Não reconhecido", None, "paddleocr", "nao_reconhecido", None),
    ]
    output.gravar(linhas, ent / "saida")
    assert (ent / "saida" / "NAO_RECONHECIDO.jpg").exists()
    assert (ent / "saida" / "NAO_RECONHECIDO_2.jpg").exists()


def test_erro_ganha_prefixo(tmp_path):
    ent = _entrada(tmp_path, ["falha.jpg"])
    linhas = [LinhaResultado("falha.jpg", "", None, "", "erro", "timeout")]
    output.gravar(linhas, ent / "saida")
    assert (ent / "saida" / "ERRO_FALHA.jpg").exists()


def test_csv_nao_tem_colunas_de_chave(tmp_path):
    ent = _entrada(tmp_path, ["a.jpg"])
    output.gravar([LinhaResultado("a.jpg", "1", None, "openai:gpt-5", "ok", None)], ent / "saida")
    header = (ent / "saida" / "resultado.csv").read_text("utf-8-sig").splitlines()[0]
    assert "chave" not in header and "key" not in header.lower()
```

- [ ] **Step 2: Escrever `tests/test_gui_helpers.py`**

```python
from leitor_lote import gui
from leitor_lote.config import Config


def test_opcoes_motor_ocr_so_locais():
    ids = [m for m, _ in gui.opcoes_motor("ocr", Config())]
    assert ids == ["tesseract", "paddleocr", "trocr"]


def test_opcoes_motor_ia_desabilita_sem_chave():
    opts = gui.opcoes_motor("ia", Config())
    assert opts and all(habil is False for _, habil in opts)
    opts2 = gui.opcoes_motor("ia", Config(chave_openai="sk"))
    assert ("openai:gpt-5-mini", True) in opts2
    assert ("mistral-ocr", False) in opts2


def test_montar_parametros_vazios_viram_none(tmp_path):
    p = gui.montar_parametros(str(tmp_path), "canhoto", "paddleocr", "auto", "", "  ")
    assert p.seq_esperada is None
    assert p.intervalo_maximo is None
    p2 = gui.montar_parametros(str(tmp_path), "canhoto", "paddleocr", "auto", "383400", "1000")
    assert (p2.seq_esperada, p2.intervalo_maximo) == (383400, 1000)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_output.py tests/test_gui_helpers.py -v`
Expected: FAIL (`ModuleNotFoundError: leitor_lote.output`)

- [ ] **Step 4: Implementar `output.py`**

```python
from __future__ import annotations

import csv
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

from leitor_lote.models import LinhaResultado

COLUNAS = ["arquivo", "texto_lido", "confianca", "motor", "status", "erro"]


def limpar_nome(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9]+", "_", s.upper()).strip("_")
    return s or "SEM_LEITURA"


def _nome_unico(base: str, ext: str, usados: dict[str, int]) -> str:
    n = usados.get(base, 0) + 1
    usados[base] = n
    return f"{base}{ext}" if n == 1 else f"{base}_{n}{ext}"


def gravar(linhas: list[LinhaResultado], pasta_saida: Path) -> None:
    pasta_entrada = pasta_saida.parent
    pasta_saida.mkdir(parents=True, exist_ok=True)
    usados: dict[str, int] = {}

    with (pasta_saida / "resultado.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUNAS)
        for linha in linhas:
            w.writerow(
                [
                    linha.arquivo,
                    linha.texto_lido,
                    "" if linha.confianca is None else f"{linha.confianca:.3f}",
                    linha.motor,
                    linha.status,
                    linha.erro or "",
                ]
            )
            origem = pasta_entrada / linha.arquivo
            if not origem.exists():
                continue
            if linha.status == "erro":
                base = "ERRO_" + limpar_nome(Path(linha.arquivo).stem)
            else:
                base = limpar_nome(linha.texto_lido)
            destino = pasta_saida / _nome_unico(base, origem.suffix.lower(), usados)
            shutil.copy2(origem, destino)

    with (pasta_saida / "log.txt").open("w", encoding="utf-8") as f:
        for linha in linhas:
            ts = datetime.now().isoformat(timespec="seconds")
            f.write(f"{ts}\t{linha.arquivo}\t{linha.motor}\t{linha.status}\t{linha.erro or ''}\n")
```

- [ ] **Step 5: Implementar `gui.py`**

```python
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from leitor_lote import config as cfgmod
from leitor_lote.models import ParametrosRodada
from leitor_lote.pipeline import rodar
from leitor_lote.readers import LOCAIS, MOTORES_IDS, disponivel


def opcoes_motor(modo: str, cfg: cfgmod.Config) -> list[tuple[str, bool]]:
    quer_local = modo in ("ocr", "auto")
    ids = [m for m in MOTORES_IDS if (m.split(":")[0] in LOCAIS) == quer_local]
    return [(m, disponivel(m, cfg)) for m in ids]


def montar_parametros(
    pasta: str, tipo_id: str, motor_id: str, modo: str, seq: str, intervalo: str
) -> ParametrosRodada:
    return ParametrosRodada(
        pasta_entrada=Path(pasta),
        tipo_id=tipo_id,
        motor_id=motor_id,
        modo=modo,  # type: ignore[arg-type]
        seq_esperada=int(seq) if seq.strip() else None,
        intervalo_maximo=int(intervalo) if intervalo.strip() else None,
    )


def rodar_janela() -> None:  # pragma: no cover - exercitado manualmente
    cfg = cfgmod.carregar()
    tipos = cfgmod.buscar_tipos(cfg)
    cancel = threading.Event()

    root = tk.Tk()
    root.title("leitor-lote")
    root.geometry("460x360")

    pasta_var = tk.StringVar(value=cfg.ultima_pasta or "")
    tipo_var = tk.StringVar(value=next(iter(tipos)))
    modo_var = tk.StringVar(value=tipos[tipo_var.get()].modo)
    motor_var = tk.StringVar(value=tipos[tipo_var.get()].motor)
    seq_var = tk.StringVar()
    int_var = tk.StringVar()

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    def escolher_pasta() -> None:
        d = filedialog.askdirectory(initialdir=pasta_var.get() or None)
        if d:
            pasta_var.set(d)

    ttk.Label(frm, text="Pasta").grid(row=0, column=0, sticky="w")
    ttk.Entry(frm, textvariable=pasta_var, width=36).grid(row=0, column=1)
    ttk.Button(frm, text="Procurar", command=escolher_pasta).grid(row=0, column=2)

    ttk.Label(frm, text="Tipo").grid(row=1, column=0, sticky="w")
    cb_tipo = ttk.Combobox(frm, textvariable=tipo_var, values=list(tipos), state="readonly")
    cb_tipo.grid(row=1, column=1, columnspan=2, sticky="we")

    ttk.Label(frm, text="Modo").grid(row=2, column=0, sticky="w")
    cb_modo = ttk.Combobox(frm, textvariable=modo_var, values=["ocr", "ia", "auto"],
                           state="readonly")
    cb_modo.grid(row=2, column=1, columnspan=2, sticky="we")

    ttk.Label(frm, text="Motor").grid(row=3, column=0, sticky="w")
    cb_motor = ttk.Combobox(frm, textvariable=motor_var, state="readonly")
    cb_motor.grid(row=3, column=1, columnspan=2, sticky="we")

    def atualizar_motores(*_a) -> None:
        opts = opcoes_motor(modo_var.get(), cfg)
        cb_motor["values"] = [m for m, _ in opts]
        habilitados = [m for m, ok in opts if ok]
        if motor_var.get() not in habilitados and habilitados:
            motor_var.set(habilitados[0])

    def ao_trocar_tipo(*_a) -> None:
        t = tipos[tipo_var.get()]
        modo_var.set(t.modo)
        motor_var.set(t.motor)
        atualizar_motores()

    tipo_var.trace_add("write", ao_trocar_tipo)
    modo_var.trace_add("write", atualizar_motores)
    atualizar_motores()

    ttk.Label(frm, text="Sequência esperada").grid(row=4, column=0, sticky="w")
    ttk.Entry(frm, textvariable=seq_var).grid(row=4, column=1, columnspan=2, sticky="we")
    ttk.Label(frm, text="Intervalo máximo").grid(row=5, column=0, sticky="w")
    ttk.Entry(frm, textvariable=int_var).grid(row=5, column=1, columnspan=2, sticky="we")

    def configurar_chaves() -> None:
        d = tk.Toplevel(root)
        d.title("Chaves")
        o = tk.StringVar(value=cfg.chave_openai or "")
        m = tk.StringVar(value=cfg.chave_mistral or "")
        ttk.Label(d, text="OpenAI").grid(row=0, column=0)
        ttk.Entry(d, textvariable=o, show="*", width=40).grid(row=0, column=1)
        ttk.Label(d, text="Mistral").grid(row=1, column=0)
        ttk.Entry(d, textvariable=m, show="*", width=40).grid(row=1, column=1)

        def salvar_() -> None:
            cfg.chave_openai = o.get().strip() or None
            cfg.chave_mistral = m.get().strip() or None
            cfgmod.salvar(cfg)
            atualizar_motores()
            d.destroy()

        ttk.Button(d, text="Salvar", command=salvar_).grid(row=2, column=0, columnspan=2)

    ttk.Button(frm, text="Configurar chaves…", command=configurar_chaves).grid(
        row=6, column=0, columnspan=3, pady=(8, 0)
    )

    barra = ttk.Progressbar(frm, maximum=100)
    barra.grid(row=7, column=0, columnspan=3, sticky="we", pady=8)
    status = ttk.Label(frm, text="")
    status.grid(row=8, column=0, columnspan=3)
    btn = ttk.Button(frm, text="Rodar")
    btn.grid(row=9, column=0, columnspan=3)

    def progresso(feitos: int, total: int) -> None:
        pct = 0 if total == 0 else int(100 * feitos / total)
        root.after(0, lambda: (barra.config(value=pct), status.config(text=f"{feitos} de {total}")))

    def concluir(linhas) -> None:
        from leitor_lote.output import gravar

        saida = Path(pasta_var.get()) / "saida"
        gravar(linhas, saida)
        ok = sum(1 for x in linhas if x.status == "ok")
        nr = sum(1 for x in linhas if x.status == "nao_reconhecido")
        er = sum(1 for x in linhas if x.status == "erro")
        cfg.ultima_pasta = pasta_var.get()
        cfgmod.salvar(cfg)
        root.after(0, lambda: _fim(saida, ok, nr, er))

    def _fim(saida: Path, ok: int, nr: int, er: int) -> None:
        status.config(text=f"Concluído — {ok} ok, {nr} não reconhecidos, {er} erros")
        btn.config(text="Abrir pasta de saída", command=lambda: _abrir(saida), state="normal")

    def _abrir(p: Path) -> None:
        import os

        os.startfile(p)  # noqa: S606 - Windows

    def executar() -> None:
        if not pasta_var.get() or not Path(pasta_var.get()).is_dir():
            messagebox.showerror("leitor-lote", "Escolha uma pasta válida.")
            return
        btn.config(state="disabled")
        p = montar_parametros(
            pasta_var.get(), tipo_var.get(), motor_var.get(), modo_var.get(),
            seq_var.get(), int_var.get(),
        )

        def trabalho() -> None:
            linhas = rodar(p, cfg, tipos, progresso, cancel)
            concluir(linhas)

        threading.Thread(target=trabalho, daemon=True).start()

    btn.config(command=executar)
    root.mainloop()
```

- [ ] **Step 6: Implementar `__main__.py`**

```python
from leitor_lote.gui import rodar_janela

if __name__ == "__main__":
    rodar_janela()
```

- [ ] **Step 7: Rodar e ver passar**

Run: `uv run pytest tests/test_output.py tests/test_gui_helpers.py -v`
Expected: PASS (8 passed)

- [ ] **Step 8: Teste manual da janela**

Run: `uv run python -m leitor_lote`
Expected: a janela abre; escolher uma pasta com 2–3 imagens, tipo `canhoto`, modo `ocr`, motor `tesseract`, clicar Rodar → barra anda, ao fim aparece "Concluído — …" e o botão vira "Abrir pasta de saída"; a pasta `saida/` tem `resultado.csv`, `log.txt` e as cópias.

- [ ] **Step 9: Commit**

```bash
git add leitor_lote/output.py leitor_lote/gui.py leitor_lote/__main__.py tests/test_output.py tests/test_gui_helpers.py
git commit -m "feat: output (copias renomeadas + csv/log) e janela Tkinter"
```

---

### Task 14: Empacotamento (`leitor-lote.spec` + `.github/workflows/build.yml`)

**Files:**
- Create: `leitor-lote.spec`
- Create: `.github/workflows/build.yml`
- Modify: `README.md` (seção de build — pode ser feita junto da Task 16; aqui só garantir que `pyinstaller leitor-lote.spec` roda)

**Interfaces:**
- Consumes: todo o pacote `leitor_lote`.
- Produces: `dist/leitor-lote/leitor-lote.exe` (modo `--onedir`), com `leitor_lote/tipos.fallback.json`, dados do `paddleocr`/`pypdfium2` e o binário do Tesseract embarcados. Workflow que, em tag `v*`, builda no `windows-latest` e anexa `leitor-lote-<tag>.zip` no Release.

- [ ] **Step 1: Escrever `leitor-lote.spec`**

```python
# leitor-lote.spec
import shutil

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("leitor_lote/tipos.fallback.json", "leitor_lote")]
datas += collect_data_files("paddleocr")
datas += collect_data_files("pypdfium2_raw")

binaries = []
_tess = shutil.which("tesseract")
if _tess:
    binaries.append((_tess, "."))

hiddenimports = collect_submodules("paddleocr") + ["PIL._tkinter_finder"]

a = Analysis(
    ["leitor_lote/__main__.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="leitor-lote", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="leitor-lote")
```

- [ ] **Step 2: Escrever `.github/workflows/build.yml`**

```yaml
name: build
on:
  push:
    tags: ["v*"]

jobs:
  windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.12"
      - name: Instalar Tesseract
        run: choco install -y tesseract
      - run: uv sync --extra dev
      - run: uv run pyinstaller leitor-lote.spec
      - name: Zipar
        run: Compress-Archive -Path dist/leitor-lote/* -DestinationPath leitor-lote-${{ github.ref_name }}.zip
      - uses: softprops/action-gh-release@v2
        with:
          files: leitor-lote-*.zip
```

- [ ] **Step 3: Buildar localmente (Windows) e conferir**

Run: `uv run pyinstaller leitor-lote.spec`
Expected: termina sem erro; existe `dist/leitor-lote/leitor-lote.exe`.

Run: `./dist/leitor-lote/leitor-lote.exe`
Expected: a janela abre (mesmo smoke da Task 13, Step 8) rodando a partir do executável empacotado.

- [ ] **Step 4: Validar o YAML do workflow**

Run: `uv run python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/build.yml')); print('yaml ok')"`
Expected: `yaml ok`
(`uv run --with pyyaml python -c ...` se `pyyaml` não estiver no ambiente.)

- [ ] **Step 5: Commit**

```bash
git add leitor-lote.spec .github/workflows/build.yml
git commit -m "build: PyInstaller --onedir + GitHub Actions publicando zip no tag"
```

---

### Task 15: Benchmark de motores (`bench/benchmark.py`)

**Files:**
- Create: `bench/__init__.py`
- Create: `bench/benchmark.py`
- Create: `tests/test_benchmark.py`

**Interfaces:**
- Consumes: `carregar`, `buscar_tipos` de `config`; `resolve` de `readers`; `preparar` de `preprocess`.
- Produces:
  - `bench.benchmark.lev(a: str, b: str) -> int` — distância de Levenshtein.
  - `bench.benchmark.cer_digitos(esperado: str, obtido: str) -> float` — `lev` sobre só-dígitos / `max(1, len(dígitos de esperado))`.
  - `bench.benchmark.rodar(pasta: Path, gabarito: Path, tipo_id: str, motores: list[str]) -> list[dict]` — por motor: `acerto_%`, `cer_digito` (média), `nao_reconhecido`, `seg_por_arq`.
  - `bench.benchmark.main() -> None` — argparse (`--pasta --gabarito --tipo --motores`), imprime as linhas e grava `bench/resultado-<AAAA-MM-DD>.csv` (`utf-8-sig`).
  - Formato do `gabarito.csv`: colunas `arquivo,esperado` (dígitos esperados, concatenados quando o tipo tem mais de um campo).

- [ ] **Step 1: Escrever os testes**

`tests/test_benchmark.py`:
```python
from pathlib import Path

from PIL import Image

from bench import benchmark
from leitor_lote.models import Reading


def test_lev():
    assert benchmark.lev("123", "123") == 0
    assert benchmark.lev("123", "124") == 1
    assert benchmark.lev("", "12") == 2


def test_cer_digitos():
    assert benchmark.cer_digitos("383462", "383462") == 0.0
    assert abs(benchmark.cer_digitos("383462", "383460") - (1 / 6)) < 1e-9


def test_rodar_com_fake(tmp_path, monkeypatch):
    pasta = tmp_path / "amostras"
    pasta.mkdir()
    for n in ("a.jpg", "b.jpg"):
        Image.new("RGB", (40, 40), "white").save(pasta / n)
    gab = pasta / "gabarito.csv"
    gab.write_text("arquivo,esperado\na.jpg,349498\nb.jpg,111111\n", encoding="utf-8-sig")

    monkeypatch.setattr(benchmark, "preparar",
                        lambda *a, **k: [object()])

    class _R:
        def read(self, img, tipo):
            return Reading(valor="349498", confianca=None, motor="fake", bruto="")

    monkeypatch.setattr(benchmark, "resolve", lambda mid, cfg: _R())
    monkeypatch.setattr(benchmark, "_tipo", lambda tid: object())
    linhas = benchmark.rodar(pasta, gab, "canhoto", ["fake"])
    assert linhas[0]["motor"] == "fake"
    assert linhas[0]["acerto_%"] == 50.0
    assert linhas[0]["nao_reconhecido"] == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_benchmark.py -v`
Expected: FAIL (`ModuleNotFoundError: bench.benchmark`)

- [ ] **Step 3: Implementar `bench/__init__.py` e `bench/benchmark.py`**

`bench/__init__.py`:
```python
```

`bench/benchmark.py`:
```python
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from leitor_lote import config as cfgmod
from leitor_lote.preprocess import preparar
from leitor_lote.readers import LOCAIS, resolve

_LOCAIS_BASE = LOCAIS


def lev(a: str, b: str) -> int:
    linha = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, linha[0] = linha[0], i
        for j, cb in enumerate(b, 1):
            prev, linha[j] = linha[j], min(linha[j] + 1, linha[j - 1] + 1, prev + (ca != cb))
    return linha[-1]


def _so_digitos(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def cer_digitos(esperado: str, obtido: str) -> float:
    e, o = _so_digitos(esperado), _so_digitos(obtido)
    return lev(e, o) / max(1, len(e))


def _gabarito(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig") as f:
        return {r["arquivo"]: r.get("esperado", "") for r in csv.DictReader(f)}


def _tipo(tipo_id: str):
    cfg = cfgmod.carregar()
    return cfgmod.buscar_tipos(cfg)[tipo_id]


def rodar(pasta: Path, gabarito: Path, tipo_id: str, motores: list[str]) -> list[dict]:
    cfg = cfgmod.carregar()
    tipo = _tipo(tipo_id)
    esperados = _gabarito(gabarito)
    saida: list[dict] = []
    for motor_id in motores:
        reader = resolve(motor_id, cfg)
        local = motor_id.split(":")[0] in _LOCAIS_BASE
        acertos = naorec = 0
        soma_cer = soma_t = 0.0
        for arquivo, esperado in esperados.items():
            img = preparar(pasta / arquivo, para_ocr=local)[0]
            ini = time.time()
            leitura = reader.read(img, tipo)
            soma_t += time.time() - ini
            obtido = _so_digitos(leitura.valor)
            if obtido == _so_digitos(esperado):
                acertos += 1
            if not obtido:
                naorec += 1
            soma_cer += cer_digitos(esperado, obtido)
        n = max(1, len(esperados))
        saida.append(
            {
                "motor": motor_id,
                "acerto_%": round(100 * acertos / n, 1),
                "cer_digito": round(soma_cer / n, 3),
                "nao_reconhecido": naorec,
                "seg_por_arq": round(soma_t / n, 2),
            }
        )
    return saida


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark de motores de OCR do leitor-lote")
    ap.add_argument("--pasta", required=True, type=Path)
    ap.add_argument("--gabarito", required=True, type=Path)
    ap.add_argument("--tipo", required=True)
    ap.add_argument("--motores", required=True, help="lista separada por virgula")
    args = ap.parse_args()

    linhas = rodar(args.pasta, args.gabarito, args.tipo, args.motores.split(","))
    for linha in linhas:
        print(linha)
    destino = Path("bench") / f"resultado-{time.strftime('%Y-%m-%d')}.csv"
    destino.parent.mkdir(exist_ok=True)
    with destino.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(f"gravado: {destino}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_benchmark.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add bench/ tests/test_benchmark.py
git commit -m "feat: bench/benchmark.py (acerto %, CER de digito, nao-reconhecido, tempo)"
```

---

### Task 16: README + varredura final

**Files:**
- Create: `README.md`
- Modify: nenhum de código.

**Interfaces:**
- Consumes: todo o projeto.
- Produces: documentação de instalação/uso/build.

- [ ] **Step 1: Escrever `README.md`**

````markdown
# leitor-lote

Lê uma pasta de canhotos (imagens `.jpg/.png` e PDFs), extrai o número de cada um
(OCR ou IA, motor escolhível), valida, e grava cópias renomeadas + `resultado.csv`
+ `log.txt`. Roda 100% na máquina — sem upload, sem servidor.

## Uso (executável)

1. Baixe o zip do [Releases](https://github.com/GabrielFerrazzzzz/leitor-lote/releases) e extraia.
2. Rode `leitor-lote.exe`. Na 1ª vez o Windows mostra o SmartScreen —
   **Mais informações → Executar assim mesmo**.
3. Escolha a pasta, o tipo de leitura, o motor e o modo, e clique **Rodar**.
4. O resultado fica em `<pasta>/saida/`.

### Motores

| Motor | Chave? | Observação |
|---|---|---|
| `tesseract` | não | embutido; bom no número impresso |
| `paddleocr` | não | embutido; melhor OCR tradicional grátis |
| `trocr` | não | baixa ~1,3 GB no 1º uso (precisa de internet uma vez) |
| `openai:gpt-5-mini` / `openai:gpt-5` | sim | cole a chave em **Configurar chaves…** |
| `mistral-ocr` | sim | idem |

### Modos

- `ocr` — só o motor local escolhido.
- `ia` — só o motor de API escolhido.
- `auto` — tenta o OCR local; se reprovar na validação ou a confiança for baixa,
  refaz com `openai:gpt-5-mini` (se houver chave).

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
    "motor": "paddleocr",
    "prompt": "Leia APENAS o número de 6 dígitos...",
    "campos": [{ "nome": "numero", "tamanho": 6 }],
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
    --tipo canhoto --motores tesseract,paddleocr,trocr,openai:gpt-5-mini,mistral-ocr
```

`gabarito.csv`: colunas `arquivo,esperado` (dígitos esperados). Saída: tabela no
terminal + `bench/resultado-<data>.csv`.
````

- [ ] **Step 2: Rodar a suíte inteira**

Run: `uv run pytest -v`
Expected: PASS (todos os testes não-`manual`).

- [ ] **Step 3: Lint final**

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README (uso do exe, motores, modos, tipos.json, dev, build, benchmark)"
```

---

## Self-Review

**1. Spec coverage**

| Requisito do spec | Task |
|---|---|
| Ler pasta local de imagens/PDFs | 12 (`_arquivos`, `EXT_OK`) |
| Sem backend / sem chave embutida | Global Constraints; 4, 10, 11, 13 (testes de não-vazamento) |
| Motor escolhível por tipo + sobreposto na janela | 4 (`Tipo.motor`), 6 (`resolve`), 13 (`opcoes_motor`, combos) |
| Modo grátis sem chave (Tesseract/Paddle) | 7, 8 |
| `Reading{valor, confianca, motor, bruto}` | 2, 6 |
| `preprocess`: EXIF, ≤2000px/q82, PDF→páginas, threshold/deskew (só inclinação pequena) | 5 |
| Temporários do `preprocess` limpos (`descartar` no `finally` da pipeline) | 5 (fn) + 12 (chamada) |
| Validação por `tipo.campos` + faixa `seq±intervalo` | 3 |
| `modo auto` com fallback pra IA; sem confiança → só `not aprovado` | 12 |
| Concorrência limitada (default 5) | 12 (`ThreadPoolExecutor`, teste de limite) |
| `output`: cópias renomeadas, colisão `_2/_3`, `ERRO_`, CSV UTF-8-BOM, log | 13 |
| `config` local + `tipos.json` por URL com fallback | 4 |
| Readers: Tesseract, PaddleOCR, TrOCR (download sob demanda), OpenAI (porta `lerArquivoComIA`), Mistral OCR | 7, 8, 9, 10, 11 |
| Janela Tkinter única | 13 |
| PyInstaller `--onedir` + GitHub Actions no tag | 14 |
| `bench/benchmark.py` (acerto, CER de dígito, tempo) | 15 |
| README com SmartScreen, motores, modos, dev, build | 16 |
| Fora de escopo: EasyOCR, auto-updater, CLI, keyring, multi-OS | respeitado (nenhuma task os introduz) |

Sem lacunas.

**2. Placeholder scan**

Sem `TBD`/`TODO`/"implemente depois". Todo step de código tem o código completo. O único identificador externo não resolvido é a conta GitHub `GabrielFerrazzzzz` na `tipos_url`/README — vem do spec (§ "conta GabrielFerrazzzzz … confirmar no push"), então é intencional, não placeholder.

**3. Type consistency**

- `Reading(valor, confianca, motor, bruto)` — idêntico em models (T2), base (T6), readers (T7–T11), pipeline (T12).
- `Tipo(id, nome, prompt, modo, motor, campos, formato_exemplo)` — T2, consumido por T3/T4/T12/T13 com os mesmos nomes.
- `avaliar(r, tipo, seq_esperada, intervalo_maximo) -> ResultadoValidado(texto_lido, aprovado, motivo)` — T3, chamado igual em T12.
- `resolve(motor_id, config)` / `disponivel(motor_id, config)` — T6, usados com essa assinatura em T12 e T13.
- `preparar(arquivo, *, para_ocr) -> list[PreparedImage]` — T5, chamado com kwarg `para_ocr=` em T12 e (posicional via `para_ocr=local`) em T15.
- `rodar(p, cfg, tipos, progresso, cancel=None)` — T12, chamado igual em T13 (`gui`).
- `gravar(linhas, pasta_saida)` — T13; `pasta_entrada` derivado de `pasta_saida.parent` (consistente com o spec `pasta_saida = pasta_entrada/"saida"`).
- `LinhaResultado(arquivo, texto_lido, confianca, motor, status, erro)` — T2, produzido em T12, consumido em T13/`output`.

Sem divergência de nomes.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-03-leitor-lote.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
