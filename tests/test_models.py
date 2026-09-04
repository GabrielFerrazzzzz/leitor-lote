from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from leitor_lote.models import (
    Campo,
    LinhaResultado,
    ParametrosRodada,
    PreparedImage,
    Reading,
    ResultadoValidado,
    Tipo,
)


def test_reading_frozen():
    r = Reading(valor="349498", confianca=0.9, motor="fake", bruto="349498")
    assert r.valor == "349498"
    with pytest.raises(FrozenInstanceError):
        r.valor = "x"  # frozen


def test_campo_defaults():
    c = Campo(nome="numero")
    assert c.tamanho == 6
    assert c.sequencial is False
    assert c.estrategia == "digitos"
    assert c.chave_tamanho == 44
    assert c.offset == 1
    assert c.repete is False
    assert Campo(nome="nota", sequencial=True).sequencial is True


def test_campo_chave_offset():
    c = Campo(
        nome="nota", tamanho=6, estrategia="chave_offset", chave_tamanho=44, offset=29, repete=True
    )
    assert c.estrategia == "chave_offset"
    assert c.offset == 29
    assert c.repete is True


def test_tipo_com_campos():
    t = Tipo(
        id="canhoto",
        nome="Canhoto",
        prompt="leia o numero",
        modo="auto",
        motor="rapidocr",
        campos=(Campo("numero", 6),),
    )
    assert t.formato_exemplo == ""
    assert t.campos[0].tamanho == 6


def test_demais_dataclasses_constroem():
    PreparedImage(bytes_=b"x", mimetype="image/jpeg", largura=1, altura=2, caminho_tmp=Path("a"))
    ResultadoValidado(texto_lido="349498", aprovado=True, motivo=None)
    LinhaResultado(
        arquivo="a.jpg", texto_lido="349498", confianca=None, motor="fake", status="ok", erro=None
    )
    ParametrosRodada(
        pasta_entrada=Path("."),
        tipo_id="canhoto",
        motor_id="rapidocr",
        modo="auto",
        seq_esperada=None,
        intervalo_maximo=None,
    )
