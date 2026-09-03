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


def test_campo_default_tamanho():
    assert Campo(nome="numero").tamanho == 6


def test_tipo_com_campos():
    t = Tipo(
        id="canhoto",
        nome="Canhoto",
        prompt="leia o numero",
        modo="auto",
        motor="paddleocr",
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
        motor_id="paddleocr",
        modo="auto",
        seq_esperada=None,
        intervalo_maximo=None,
    )
