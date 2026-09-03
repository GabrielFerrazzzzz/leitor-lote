from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from leitor_lote.config import Config
from leitor_lote.models import LinhaResultado, ParametrosRodada, Tipo
from leitor_lote.preprocess import descartar, preparar
from leitor_lote.readers import disponivel, resolve
from leitor_lote.validate import avaliar

EXT_OK: set[str] = {".jpg", ".jpeg", ".png", ".pdf"}


def _arquivos(pasta: Path) -> list[Path]:
    return sorted(
        p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXT_OK
    )


def _melhor_de_paginas(reader, paginas, tipo, p):
    melhor = None
    for img in paginas:
        leitura = reader.read(img, tipo)
        v = avaliar(leitura, tipo, p.seq_esperada, p.intervalo_maximo)
        if v.aprovado:
            return leitura, v
        melhor = melhor or (leitura, v)
    return melhor


def _ler_um(arquivo: Path, p: ParametrosRodada, cfg: Config, tipo: Tipo,
            cancel: threading.Event) -> LinhaResultado:
    if cancel.is_set():
        return LinhaResultado(arquivo.name, "", None, "", "erro", "cancelado")
    preparados: list = []
    try:
        paginas = preparar(arquivo, para_ocr=p.modo != "ia")
        preparados.extend(paginas)
        reader = resolve(p.motor_id, cfg)
        leitura, v = _melhor_de_paginas(reader, paginas, tipo, p)

        if p.modo == "auto":
            baixa_conf = leitura.confianca is not None and leitura.confianca < cfg.limiar_confianca
            if (not v.aprovado or baixa_conf) and disponivel(cfg.motor_ia_fallback, cfg):
                r2 = resolve(cfg.motor_ia_fallback, cfg)
                paginas_ia = preparar(arquivo, para_ocr=False)
                preparados.extend(paginas_ia)
                res2 = _melhor_de_paginas(r2, paginas_ia, tipo, p)
                if res2 and (res2[1].aprovado or not v.aprovado):
                    leitura, v = res2

        status = "ok" if v.aprovado else "nao_reconhecido"
        return LinhaResultado(arquivo.name, v.texto_lido, leitura.confianca, leitura.motor,
                              status, None)
    except Exception as e:  # noqa: BLE001
        return LinhaResultado(arquivo.name, "", None, "", "erro", str(e))
    finally:
        descartar(preparados)


def rodar(
    p: ParametrosRodada,
    cfg: Config,
    tipos: dict[str, Tipo],
    progresso: Callable[[int, int], None],
    cancel: threading.Event | None = None,
) -> list[LinhaResultado]:
    cancel = cancel or threading.Event()
    tipo = tipos[p.tipo_id]
    arquivos = _arquivos(p.pasta_entrada)
    total = len(arquivos)
    progresso(0, total)

    resultados: list[LinhaResultado] = []
    feitos = 0
    with ThreadPoolExecutor(max_workers=max(1, cfg.concorrencia)) as ex:
        futs = [ex.submit(_ler_um, a, p, cfg, tipo, cancel) for a in arquivos]
        for fut in as_completed(futs):
            resultados.append(fut.result())
            feitos += 1
            progresso(feitos, total)

    resultados.sort(key=lambda r: r.arquivo)
    return resultados
