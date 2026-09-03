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


def test_carregar_config_corrompido_reescreve_default(_paths):
    _paths.mkdir(parents=True, exist_ok=True)
    cfgmod.CONFIG_PATH.write_text("{ not json", "utf-8")
    c = cfgmod.carregar()
    assert isinstance(c, cfgmod.Config)
    assert c.concorrencia == 5
    # o arquivo corrompido foi reescrito com JSON válido
    assert json.loads(cfgmod.CONFIG_PATH.read_text("utf-8"))["concorrencia"] == 5


def test_carregar_coage_concorrencia_invalida(_paths):
    _paths.mkdir(parents=True, exist_ok=True)
    cfgmod.CONFIG_PATH.write_text(json.dumps({"concorrencia": "cinco"}), "utf-8")
    assert cfgmod.carregar().concorrencia == 5


def test_chave_nunca_alem_do_config(_paths):
    # a chave mora no config.json e em lugar nenhum mais; garante que salvar()
    # nao vaza pra stdout/log (aqui: nao ha outra escrita)
    c = cfgmod.carregar()
    c.chave_openai = "sk-secreta"
    cfgmod.salvar(c)
    conteudo = cfgmod.CONFIG_PATH.read_text("utf-8")
    assert "sk-secreta" in conteudo  # esperado: SÓ aqui
    assert json.loads(conteudo)["chave_openai"] == "sk-secreta"
