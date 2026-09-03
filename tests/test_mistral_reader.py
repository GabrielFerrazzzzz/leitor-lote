import re

import httpx

from leitor_lote.config import Config
from leitor_lote.models import Campo, PreparedImage, Tipo
from leitor_lote.readers.mistral_reader import MistralOcrReader

TIPO = Tipo(id="canhoto", nome="C", prompt="", modo="ia", motor="mistral-ocr",
            campos=(Campo("numero", 6),))
IMG = PreparedImage(bytes_=b"abc", mimetype="image/jpeg", largura=1, altura=1, caminho_tmp=None)


def test_read_junta_paginas(monkeypatch):
    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"pages": [{"markdown": "nota: 3494"}, {"markdown": "98 fim"}]}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    r = MistralOcrReader(chave="key").read(IMG, TIPO)
    assert r.valor == "nota: 3494\n98 fim"
    assert re.sub(r"\D", "", r.valor) == "349498"
    assert r.motor == "mistral-ocr"
    assert "key" not in r.bruto


def test_disponivel_exige_chave():
    assert MistralOcrReader(chave="k").disponivel(Config()) is True
    assert MistralOcrReader().disponivel(Config()) is False
