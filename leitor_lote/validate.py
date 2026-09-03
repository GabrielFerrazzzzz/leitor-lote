from __future__ import annotations

import re

from leitor_lote.models import Reading, ResultadoValidado, Tipo

NAO_RECONHECIDO = "Não reconhecido"


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def avaliar(
    r: Reading,
    tipo: Tipo,
    seq_esperada: int | None,
    intervalo_maximo: int | None,
) -> ResultadoValidado:
    partes = [p.strip() for p in r.valor.split(" - ")]
    n = len(tipo.campos)
    if len(partes) < n:
        partes = partes + [""] * (n - len(partes))

    checa_faixa = seq_esperada is not None and intervalo_maximo is not None
    algum_sequencial = any(c.sequencial for c in tipo.campos)

    saidas: list[str] = []
    motivos: list[str] = []
    for campo, parte in zip(tipo.campos, partes[:n]):
        d = _digitos(parte)
        if len(d) != campo.tamanho:
            saidas.append(NAO_RECONHECIDO)
            motivos.append(f"{campo.nome}: {len(d)} dígitos (esperado {campo.tamanho})")
            continue
        aplica_faixa = checa_faixa and (campo.sequencial or not algum_sequencial)
        if aplica_faixa:
            valor = int(d)
            lo, hi = seq_esperada - intervalo_maximo, seq_esperada + intervalo_maximo
            if not (lo <= valor <= hi):
                saidas.append(NAO_RECONHECIDO)
                motivos.append(f"{campo.nome}: {valor} fora de {seq_esperada}±{intervalo_maximo}")
                continue
        saidas.append(d)

    aprovado = all(s != NAO_RECONHECIDO for s in saidas)
    return ResultadoValidado(
        texto_lido=" - ".join(saidas),
        aprovado=aprovado,
        motivo="; ".join(motivos) if motivos else None,
    )
