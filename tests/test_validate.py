from leitor_lote.models import Campo, Reading, Tipo
from leitor_lote.validate import avaliar

CANHOTO = Tipo(id="canhoto", nome="Canhoto", prompt="", modo="auto", motor="paddleocr",
               campos=(Campo("numero", 6),))
PEDIDO = Tipo(id="pedido", nome="Pedido", prompt="", modo="auto", motor="paddleocr",
              campos=(Campo("documento", 6), Campo("nota", 6)))


def _r(valor: str) -> Reading:
    return Reading(valor=valor, confianca=None, motor="fake", bruto=valor)


def test_canhoto_ok():
    v = avaliar(_r("349498"), CANHOTO, None, None)
    assert v.aprovado is True
    assert v.texto_lido == "349498"
    assert v.motivo is None


def test_canhoto_poucos_digitos():
    v = avaliar(_r("34949"), CANHOTO, None, None)
    assert v.aprovado is False
    assert v.texto_lido == "Não reconhecido"
    assert "5" in v.motivo


def test_canhoto_limpa_lixo_nao_digito():
    v = avaliar(_r("NF 349498 -"), CANHOTO, None, None)
    assert v.texto_lido == "349498"


def test_pedido_um_campo_sobrevive():
    v = avaliar(_r("349498 - 38346X"), PEDIDO, None, None)
    assert v.aprovado is False
    assert v.texto_lido == "349498 - Não reconhecido"


def test_faixa_dentro():
    v = avaliar(_r("383462"), CANHOTO, 383400, 1000)
    assert v.aprovado is True


def test_faixa_fora():
    v = avaliar(_r("803464"), CANHOTO, 383400, 1000)
    assert v.aprovado is False
    assert v.texto_lido == "Não reconhecido"
    assert "fora" in v.motivo
