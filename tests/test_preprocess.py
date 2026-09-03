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
