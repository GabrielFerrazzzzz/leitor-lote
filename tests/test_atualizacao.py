from __future__ import annotations

import httpx

from leitor_lote import atualizacao

# --- versao_e_mais_nova (pura) ---


def test_versao_e_mais_nova_maior():
    assert atualizacao.versao_e_mais_nova("0.1.2", "0.2.0") is True


def test_versao_e_mais_nova_igual():
    assert atualizacao.versao_e_mais_nova("0.2.0", "0.2.0") is False


def test_versao_e_mais_nova_menor():
    assert atualizacao.versao_e_mais_nova("0.2.0", "0.1.9") is False


def test_versao_e_mais_nova_padding_de_partes_faltando():
    assert atualizacao.versao_e_mais_nova("1.2", "1.2.1") is True
    assert atualizacao.versao_e_mais_nova("1.2.0", "1.2") is False
    assert atualizacao.versao_e_mais_nova("1.2", "1.2.0") is False


def test_versao_e_mais_nova_entrada_invalida_nao_lanca():
    assert atualizacao.versao_e_mais_nova("abc", "0.1.0") is False
    assert atualizacao.versao_e_mais_nova("0.1.0", "abc") is False
    assert atualizacao.versao_e_mais_nova("", "") is False
    assert atualizacao.versao_e_mais_nova("0.1.0-beta", "0.2.0") is False


# --- versao_mais_recente (httpx.get monkeypatchado) ---


class _FakeResp:
    def __init__(self, tag=None, status_ok=True, json_erro=False):
        self._tag = tag
        self._status_ok = status_ok
        self._json_erro = json_erro

    def raise_for_status(self):
        if not self._status_ok:
            raise httpx.HTTPStatusError("erro http", request=None, response=None)

    def json(self):
        if self._json_erro:
            raise ValueError("json invalido")
        return {"tag_name": self._tag} if self._tag is not None else {}


def test_versao_mais_recente_sucesso(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout=5.0: _FakeResp(tag="v0.2.0"))
    assert atualizacao.versao_mais_recente() == "0.2.0"


def test_versao_mais_recente_sem_prefixo_v(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout=5.0: _FakeResp(tag="0.2.0"))
    assert atualizacao.versao_mais_recente() == "0.2.0"


def test_versao_mais_recente_erro_de_rede_nao_lanca(monkeypatch):
    def _fake_get(url, timeout=5.0):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(httpx, "get", _fake_get)
    assert atualizacao.versao_mais_recente() is None


def test_versao_mais_recente_status_nao_200_nao_lanca(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda url, timeout=5.0: _FakeResp(tag="v0.2.0", status_ok=False)
    )
    assert atualizacao.versao_mais_recente() is None


def test_versao_mais_recente_json_malformado_nao_lanca(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout=5.0: _FakeResp(json_erro=True))
    assert atualizacao.versao_mais_recente() is None


def test_versao_mais_recente_sem_tag_name_nao_lanca(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout=5.0: _FakeResp(tag=None))
    assert atualizacao.versao_mais_recente() is None
