from leitor_lote.models import Campo, Reading, Tipo
from leitor_lote.selecao import escolher

CANHOTO = Tipo(id="canhoto", nome="Canhoto", prompt="", modo="auto", motor="rapidocr",
               campos=(Campo("numero", 6, sequencial=True),))
PEDIDO = Tipo(id="pedido", nome="Pedido", prompt="", modo="auto", motor="rapidocr",
              campos=(Campo("documento", 6, sequencial=False),
                      Campo("nota", 6, sequencial=True)))


def _r(valor: str, confianca: float | None = None, motor: str = "fake",
       bruto: str | None = None) -> Reading:
    return Reading(valor=valor, confianca=confianca, motor=motor,
                   bruto=valor if bruto is None else bruto)


def test_canhoto_extrai_de_pagina_ruidosa():
    entrada = "NF 349498\ncnpj 12.345.678/0001-99\n03/09/2026"
    assert escolher(_r(entrada), CANHOTO, None, None).valor == "349498"


def test_canhoto_so_janela_serve_pega_primeira():
    # digitos colados, nenhuma linha com exatamente 6 -> 1a janela de 6
    assert escolher(_r("3494981234"), CANHOTO, None, None).valor == "349498"


def test_canhoto_faixa_desempata_entre_janelas():
    # a linha tem duas janelas de 6 candidatas; so 382900 cai em 383400 +/- 1000
    saida = escolher(_r("382900 349498"), CANHOTO, 383400, 1000)
    assert saida.valor == "382900"


def test_pedido_dois_campos_linhas_distintas():
    saida = escolher(_r("doc 349498\nnota 383462"), PEDIDO, None, None)
    assert saida.valor == "349498 - 383462"


def test_pedido_ia_estruturado_passa_intacto():
    r = Reading(valor="349498 - 383462", confianca=0.99, motor="openai:gpt-5-mini",
                bruto="349498 - 383462")
    saida = escolher(r, PEDIDO, None, None)
    assert saida.valor == "349498 - 383462"
    assert saida is r


def test_nada_plausivel_devolve_vazio():
    saida = escolher(_r("sem numero aqui"), CANHOTO, None, None)
    assert saida.valor == ""


def test_preserva_confianca_motor_bruto():
    r = Reading(valor="NF 349498\nqtd 12", confianca=0.71, motor="tesseract", bruto="<<cru>>")
    saida = escolher(r, CANHOTO, None, None)
    assert saida.valor == "349498"
    assert saida.confianca == 0.71
    assert saida.motor == "tesseract"
    assert saida.bruto == "<<cru>>"
