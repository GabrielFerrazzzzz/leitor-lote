from __future__ import annotations

import re

from leitor_lote.models import Reading, Tipo


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def _janelas(digitos: str, n: int) -> list[str]:
    return [digitos[i : i + n] for i in range(len(digitos) - n + 1)]


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

    faixa = None
    if seq_esperada is not None and intervalo_maximo is not None:
        faixa = (seq_esperada - intervalo_maximo, seq_esperada + intervalo_maximo)

    linhas = [ln.strip() for ln in r.valor.replace(" - ", "\n").splitlines() if ln.strip()]
    linhas = linhas or [r.valor]

    usadas: set[int] = set()
    escolhidos: list[str] = []
    for campo in tipo.campos:
        alvo = campo.tamanho
        cands: list[tuple[str, int, bool]] = []  # (numero, idx_linha, linha_limpa)
        for i, ln in enumerate(linhas):
            if i in usadas:
                continue
            d = _digitos(ln)
            if len(d) == alvo:
                cands.append((d, i, True))
            else:
                cands.extend((w, i, False) for w in _janelas(d, alvo))

        def rank(c: tuple[str, int, bool], campo=campo) -> tuple[bool, bool]:
            num, _, limpa = c
            na_faixa = bool(faixa and campo.sequencial and faixa[0] <= int(num) <= faixa[1])
            return (na_faixa, limpa)  # maior = melhor

        if cands:
            num, idx, _ = max(cands, key=rank)
            escolhidos.append(num)
            usadas.add(idx)
        else:
            escolhidos.append("")  # nada plausível -> avaliar() marca "Não reconhecido"

    return Reading(
        valor=" - ".join(escolhidos), confianca=r.confianca, motor=r.motor, bruto=r.bruto
    )
