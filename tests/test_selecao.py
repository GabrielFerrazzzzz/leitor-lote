from leitor_lote.models import Campo, Reading, Tipo
from leitor_lote.selecao import escolher

CANHOTO = Tipo(id="canhoto", nome="Canhoto", prompt="", modo="auto", motor="rapidocr",
               campos=(Campo("numero", 6, sequencial=True),))
PEDIDO = Tipo(id="pedido", nome="Pedido", prompt="", modo="auto", motor="rapidocr",
              campos=(Campo("documento", 6, sequencial=False),
                      Campo("nota", 6, sequencial=True)))
CAMPO_CHAVE = Campo("nota", tamanho=6, estrategia="chave_offset", chave_tamanho=44, offset=29,
                     repete=True)
CANHOTO_ATIVA = Tipo(id="canhoto_ativa", nome="Canhoto Ativa", prompt="", modo="auto",
                     motor="rapidocr", campos=(CAMPO_CHAVE,))

# chave sintética de 44 dígitos onde os dígitos 29-34 (1-indexado) sao "321342" e
# 387125 -- não depende de conseguir ler os dígitos exatos de uma foto real, só
# fixa a regra "posição 29, 6 dígitos" que o Gabriel descreveu.
_PREFIXO_28 = "1" * 28
_SUFIXO_10 = "9" * 10
CHAVE_1 = _PREFIXO_28 + "321342" + _SUFIXO_10
CHAVE_2 = _PREFIXO_28 + "387125" + _SUFIXO_10
assert len(CHAVE_1) == 44 and len(CHAVE_2) == 44


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


def test_chave_offset_uma_ocorrencia():
    entrada = f"Chave de acesso\n{CHAVE_1}\nCNPJ 12.345.678/0001-99"
    saida = escolher(_r(entrada), CANHOTO_ATIVA, None, None)
    assert saida.valor == "321342"


def test_chave_offset_varias_ocorrencias_junta_com_pipe():
    entrada = f"{CHAVE_1}\ntexto no meio\n{CHAVE_2}"
    saida = escolher(_r(entrada), CANHOTO_ATIVA, None, None)
    assert saida.valor == "321342 | 387125"


def test_chave_offset_nada_encontrado_devolve_vazio():
    saida = escolher(_r("sem chave nenhuma aqui, só um cnpj 12345678000199"), CANHOTO_ATIVA,
                     None, None)
    assert saida.valor == ""


def test_chave_offset_ia_ja_estruturado_passa_intacto():
    r = Reading(valor="321342 | 387125", confianca=0.95, motor="openai:gpt-5-mini",
                bruto="321342 | 387125")
    saida = escolher(r, CANHOTO_ATIVA, None, None)
    assert saida.valor == "321342 | 387125"
    assert saida is r
