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
