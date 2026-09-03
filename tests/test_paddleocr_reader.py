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
