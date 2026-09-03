import re

import pytest

from leitor_lote.models import Campo, PreparedImage, Tipo
from leitor_lote.readers import rapidocr_reader
from leitor_lote.readers.rapidocr_reader import RapidOcrReader

TIPO = Tipo(id="canhoto", nome="C", prompt="", modo="ocr", motor="rapidocr",
            campos=(Campo("numero", 6),))


def _img(tmp_path):
    from PIL import Image

    p = tmp_path / "x.jpg"
    Image.new("RGB", (200, 60), "white").save(p)
    return PreparedImage(bytes_=b"x", mimetype="image/jpeg", largura=200, altura=60, caminho_tmp=p)


def test_read_junta_linhas_e_media_de_score(tmp_path, monkeypatch):
    class _Eng:
        def __call__(self, caminho):
            linhas = [[[[0, 0]], "NF 3494", 0.9], [[[0, 0]], "98", 0.8]]
            return linhas, [0.1, 0.0, 0.2]

    monkeypatch.setattr(rapidocr_reader, "_engine", lambda: _Eng())
    r = RapidOcrReader().read(_img(tmp_path), TIPO)
    assert r.valor == "NF 3494\n98"
    assert abs(r.confianca - 0.85) < 1e-6
    assert r.motor == "rapidocr"


def test_read_sem_deteccao_devolve_vazio(tmp_path, monkeypatch):
    class _Eng:
        def __call__(self, caminho):
            return None, []  # RapidOCR devolve None quando não acha nada

    monkeypatch.setattr(rapidocr_reader, "_engine", lambda: _Eng())
    r = RapidOcrReader().read(_img(tmp_path), TIPO)
    assert r.valor == ""
    assert r.confianca is None


@pytest.mark.manual
def test_read_real(tmp_path):
    from PIL import Image, ImageDraw

    p = tmp_path / "n.jpg"
    img = Image.new("RGB", (240, 80), "white")
    ImageDraw.Draw(img).text((20, 25), "349498", fill="black")
    img.save(p)
    pi = PreparedImage(bytes_=p.read_bytes(), mimetype="image/jpeg", largura=240, altura=80,
                       caminho_tmp=p)
    r = RapidOcrReader().read(pi, TIPO)
    assert "349498" in re.sub(r"\D", "", r.valor)
