import httpx

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
