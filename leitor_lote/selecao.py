from __future__ import annotations

import re

from leitor_lote.models import Campo, Reading, Tipo


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def _janelas(digitos: str, n: int) -> list[str]:
    return [digitos[i : i + n] for i in range(len(digitos) - n + 1)]


# CNPJ/CPF nunca é o número do documento -- exclui a linha inteira da disputa
# (achado real: "No. 3$5277" perdeu um dígito no OCR (virou 5 dígitos, sem
# candidato), e sobrou só o CNPJ do rodapé pra gerar janelas de 6 dígitos,
# escolhendo um trecho dele por eliminação).
_RE_ID_FISCAL = re.compile(r"\bcnpj\b|\bcpf\b", re.IGNORECASE)

# rótulo "No."/"Nº"/"N°" do número do documento (presente em ~todo canhoto real
# testado) -- desempata quando mais de uma linha tem dígitos plausíveis.
_RE_ANCORA_NUMERO = re.compile(r"\bno\.?(?=\d|\s|$|[:\-–])|nº|n°", re.IGNORECASE)


def _tem_ancora(linhas: list[str], i: int) -> bool:
    """True se a linha `i` (ou a anterior, quando ela só tem o rótulo sem
    dígitos -- caso comum em DANFE, 'No.' numa linha e o número na próxima)
    traz o rótulo do número do documento."""
    if _RE_ANCORA_NUMERO.search(linhas[i]):
        return True
    anterior = linhas[i - 1] if i > 0 else ""
    return bool(anterior) and not _digitos(anterior) and bool(_RE_ANCORA_NUMERO.search(anterior))


def _valores_chave_offset(linhas: list[str], campo: Campo) -> list[str]:
    """Acha, em cada linha com dígitos suficientes pra ser uma chave de acesso
    (NF-e/CT-e, sempre `chave_tamanho` dígitos), o pedaço de `tamanho` dígitos
    que começa na posição 1-indexada `offset` dentro dela. Uma linha só rende
    um valor; `repete=True` em quem chama decide se usa todos ou só o 1º."""
    achados: list[str] = []
    for ln in linhas:
        d = _digitos(ln)
        if len(d) < campo.chave_tamanho:
            continue
        chave = d[: campo.chave_tamanho]
        inicio = campo.offset - 1
        pedaco = chave[inicio : inicio + campo.tamanho]
        if len(pedaco) == campo.tamanho:
            achados.append(pedaco)
    return achados


def escolher(
    r: Reading, tipo: Tipo, seq_esperada: int | None, intervalo_maximo: int | None
) -> Reading:
    n = len(tipo.campos)
    # caminho IA: o motor já entregou a resposta estruturada ("<a> - <b>", cada
    # parte com exatamente os dígitos do campo) -> repassa intacto
    partes = [p.strip() for p in r.valor.split(" - ")]
    if len(partes) == n and all(
        len(_digitos(p)) == c.tamanho for p, c in zip(partes, tipo.campos)
    ):
        return r

    # caminho IA: campo único repetido (ex. várias chaves na mesma página) e o
    # motor já entregou "<a> | <b>" estruturado -> repassa intacto
    if n == 1 and tipo.campos[0].repete:
        pecas = [p.strip() for p in r.valor.split(" | ") if p.strip()]
        if pecas and all(len(_digitos(p)) == tipo.campos[0].tamanho for p in pecas):
            return r

    faixa = None
    if seq_esperada is not None and intervalo_maximo is not None:
        faixa = (seq_esperada - intervalo_maximo, seq_esperada + intervalo_maximo)

    linhas = [ln.strip() for ln in r.valor.replace(" - ", "\n").splitlines() if ln.strip()]
    linhas = linhas or [r.valor]

    usadas: set[int] = set()
    escolhidos: list[str] = []
    for campo in tipo.campos:
        if campo.estrategia in ("chave_offset", "chave_offset_ou_digitos"):
            achados = _valores_chave_offset(linhas, campo)
            # achou uma chave de 44 dígitos -> é um documento tipo Ativa, usa isso.
            # "chave_offset" puro sempre decide aqui (mesmo sem achar nada, vira
            # "Não reconhecido" no avaliar); "chave_offset_ou_digitos" só decide
            # aqui quando ACHOU algo -- sem achar, cai pro caminho de dígitos
            # abaixo (não é um documento Ativa, é um canhoto comum).
            if achados or campo.estrategia == "chave_offset":
                escolhidos.append(" | ".join(achados) if campo.repete else
                                  (achados[0] if achados else ""))
                continue

        alvo = campo.tamanho
        cands: list[tuple[str, int, bool]] = []  # (numero, idx_linha, linha_limpa)
        for i, ln in enumerate(linhas):
            if i in usadas or _RE_ID_FISCAL.search(ln):
                continue
            d = _digitos(ln)
            if len(d) == alvo:
                cands.append((d, i, True))
            else:
                cands.extend((w, i, False) for w in _janelas(d, alvo))

        def rank(c: tuple[str, int, bool], campo=campo) -> tuple[bool, bool, bool]:
            num, idx, limpa = c
            na_faixa = bool(faixa and campo.sequencial and faixa[0] <= int(num) <= faixa[1])
            return (na_faixa, _tem_ancora(linhas, idx), limpa)  # maior = melhor

        if cands:
            num, idx, _ = max(cands, key=rank)
            escolhidos.append(num)
            usadas.add(idx)
        else:
            escolhidos.append("")  # nada plausível -> avaliar() marca "Não reconhecido"

    return Reading(
        valor=" - ".join(escolhidos), confianca=r.confianca, motor=r.motor, bruto=r.bruto
    )
