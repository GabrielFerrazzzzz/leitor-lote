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
