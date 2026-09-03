import threading
from pathlib import Path

import pytest
from PIL import Image

from leitor_lote import pipeline
from leitor_lote.config import Config
from leitor_lote.models import Campo, ParametrosRodada, PreparedImage, Reading, Tipo

CANHOTO = Tipo(id="canhoto", nome="C", prompt="", modo="auto", motor="rapidocr",
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


def _params(pasta, modo="ocr", motor="rapidocr"):
    return ParametrosRodada(pasta_entrada=pasta, tipo_id="canhoto", motor_id=motor, modo=modo,
                            seq_esperada=None, intervalo_maximo=None)


def test_ok_simples(tmp_path, monkeypatch):
    pasta = _pasta(tmp_path, 3)
    monkeypatch.setattr(pipeline, "preparar", lambda *a, **k: _prepared(tmp_path))

    class _R:
        def read(self, img, tipo):
            return Reading(valor="349498", confianca=0.9, motor="rapidocr", bruto="")

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
            return Reading(valor="12", confianca=0.2, motor="rapidocr", bruto="")

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
            return Reading(valor="349498", confianca=0.9, motor="rapidocr", bruto="")

    monkeypatch.setattr(pipeline, "resolve", lambda mid, cfg: _R())
    pipeline.rodar(_params(pasta), Config(concorrencia=3), TIPOS, lambda f, t: None)
    assert ativos["max"] <= 3


def test_ia_sem_chave_erra_claro(tmp_path):
    pasta = _pasta(tmp_path, 1)
    with pytest.raises(ValueError):
        pipeline.rodar(
            _params(pasta, modo="ia", motor="openai:gpt-5-mini"),
            Config(),
            TIPOS,
            lambda f, t: None,
        )


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
                            Reading(valor="349498", confianca=0.9, motor="rapidocr", bruto="")})())
    descartados = []
    monkeypatch.setattr(pipeline, "descartar", lambda imgs: descartados.append(list(imgs)))
    pipeline.rodar(_params(pasta), Config(), TIPOS, lambda f, t: None)
    assert len(descartados) == 3  # um finally por arquivo
    assert all(len(lote) >= 1 for lote in descartados)
