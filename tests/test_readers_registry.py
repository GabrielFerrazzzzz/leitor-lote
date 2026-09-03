import pytest

from leitor_lote import readers
from leitor_lote.config import Config
from leitor_lote.readers.base import Reader
from tests.fakes import FakeReader


def test_fake_satisfaz_protocolo():
    assert isinstance(FakeReader(), Reader)


def test_resolve_local():
    r = readers.resolve("tesseract", Config())
    assert r.id == "tesseract"


def test_resolve_openai_com_modelo():
    r = readers.resolve("openai:gpt-5", Config(chave_openai="sk-x"))
    assert r.modelo == "gpt-5"


def test_resolve_desconhecido():
    with pytest.raises(ValueError):
        readers.resolve("xpto", Config())


def test_disponivel_por_chave():
    assert readers.disponivel("openai:gpt-5-mini", Config(chave_openai="sk-x")) is True
    assert readers.disponivel("openai:gpt-5-mini", Config()) is False
    assert readers.disponivel("mistral-ocr", Config()) is False
    assert readers.disponivel("rapidocr", Config()) is True
