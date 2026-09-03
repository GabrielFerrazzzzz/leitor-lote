from leitor_lote.models import Campo, Reading, Tipo
from leitor_lote.validate import avaliar

CANHOTO = Tipo(id="canhoto", nome="Canhoto", prompt="", modo="auto", motor="rapidocr",
               campos=(Campo("numero", 6),))
PEDIDO = Tipo(id="pedido", nome="Pedido", prompt="", modo="auto", motor="rapidocr",
              campos=(Campo("documento", 6), Campo("nota", 6)))
PEDIDO_SEQ = Tipo(id="pedido", nome="Pedido", prompt="", modo="auto", motor="rapidocr",
                  campos=(Campo("documento", 6, sequencial=False),
                          Campo("nota", 6, sequencial=True)))


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


def test_faixa_exige_ambos_parametros():
    # só seq, sem intervalo -> a regra de faixa é pulada
    v = avaliar(_r("803464"), CANHOTO, 383400, None)
    assert v.aprovado is True


def test_faixa_limite_inclusivo():
    v = avaliar(_r("384400"), CANHOTO, 383400, 1000)  # exatamente seq + intervalo
    assert v.aprovado is True


def test_faixa_so_no_campo_sequencial():
    # documento longe da sequência NÃO reprova; nota fora da faixa reprova
    ok = avaliar(_r("999999 - 383462"), PEDIDO_SEQ, 383400, 1000)
    assert ok.texto_lido == "999999 - 383462"
    assert ok.aprovado is True
    ruim = avaliar(_r("999999 - 803464"), PEDIDO_SEQ, 383400, 1000)
    assert ruim.texto_lido == "999999 - Não reconhecido"
    assert ruim.aprovado is False
