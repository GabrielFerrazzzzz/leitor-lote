import httpx
import pytest

from leitor_lote import soma
from leitor_lote.config import Config
from leitor_lote.models import PreparedImage, Tipo
from leitor_lote.readers.soma_reader import SomaReader

TIPO = Tipo(id="canhoto", nome="C", prompt="leia o numero", modo="ia", motor="soma", campos=())


def _img(tmp_path):
    p = tmp_path / "x.jpg"
    p.write_bytes(b"JPEGBYTES")
    return PreparedImage(bytes_=b"JPEGBYTES", mimetype="image/jpeg", largura=1, altura=1,
                         caminho_tmp=p)


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.content = b"x"

    def json(self):
        return self._payload


def test_login_ok(monkeypatch):
    def fake_post(url, **kw):
        assert "grant_type=password" in url
        return _Resp(200, {"access_token": "AT", "refresh_token": "RT",
                           "user": {"email": "a@b.com"}})

    monkeypatch.setattr(httpx, "post", fake_post)
    s = soma.login("a@b.com", "senha")
    assert s == {"email": "a@b.com", "access_token": "AT", "refresh_token": "RT"}


def test_login_credencial_errada_levanta(monkeypatch):
    monkeypatch.setattr(httpx, "post",
                        lambda url, **kw: _Resp(400, {"error_description": "Invalid login"}))
    with pytest.raises(soma.SomaAuthError):
        soma.login("a@b.com", "errada")


def test_ler_imagem_manda_prompt_em_base64(monkeypatch):
    visto = {}

    def fake_post(url, **kw):
        visto["url"] = url
        visto["headers"] = kw["headers"]
        visto["content"] = kw["content"]
        return _Resp(200, {"numero": " 349498 "})

    monkeypatch.setattr(httpx, "post", fake_post)
    out = soma.ler_imagem(b"IMG", "leia o numero", "TOKEN", "foto.jpg")
    assert out == "349498"
    assert visto["url"].endswith("/ler")
    assert visto["headers"]["Authorization"] == "Bearer TOKEN"
    assert visto["content"] == b"IMG"
    import base64
    assert base64.b64decode(visto["headers"]["X-Prompt"]).decode() == "leia o numero"


def test_ler_imagem_401_levanta_auth_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kw: _Resp(401, {"erro": "expirado"}))
    with pytest.raises(soma.SomaAuthError):
        soma.ler_imagem(b"IMG", "p", "TOKEN")


def test_reader_disponivel_depende_do_token():
    assert SomaReader(Config()).disponivel(Config()) is False
    assert SomaReader(Config(soma_token="x")).disponivel(Config(soma_token="x")) is True


def test_reader_read_devolve_reading(monkeypatch, tmp_path):
    monkeypatch.setattr(soma, "ler_imagem", lambda *a, **k: "349498")
    r = SomaReader(Config(soma_token="AT")).read(_img(tmp_path), TIPO)
    assert r.valor == "349498"
    assert r.motor == "soma"


def test_reader_refaz_login_no_401(monkeypatch, tmp_path):
    monkeypatch.setattr("leitor_lote.config.salvar", lambda c: None)  # não escrever no disco
    cfg = Config(soma_token="VELHO", soma_refresh="RT")
    chamadas = {"n": 0}

    def fake_ler(dados, prompt, token, nome):
        chamadas["n"] += 1
        if token == "VELHO":
            raise soma.SomaAuthError("expirou")
        return "349498"

    monkeypatch.setattr(soma, "ler_imagem", fake_ler)
    monkeypatch.setattr(soma, "refresh",
                        lambda rt: {"email": "a@b", "access_token": "NOVO", "refresh_token": "RT2"})
    r = SomaReader(cfg).read(_img(tmp_path), TIPO)
    assert r.valor == "349498"
    assert cfg.soma_token == "NOVO"  # token renovado e persistido no cfg
    assert chamadas["n"] == 2
