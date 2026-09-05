from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from leitor_lote.config import Config
from leitor_lote.models import LinhaResultado, ParametrosRodada, Tipo
from leitor_lote.preprocess import descartar, preparar
from leitor_lote.readers import LOCAIS, disponivel, resolve
from leitor_lote.selecao import escolher
from leitor_lote.validate import avaliar

EXT_OK: set[str] = {".jpg", ".jpeg", ".png", ".pdf"}


def _arquivos(pasta: Path) -> list[Path]:
    return sorted(
        p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXT_OK
    )


def _melhor_de_paginas(reader, paginas, tipo, p):
    melhor = None
    for img in paginas:
        bruta = reader.read(img, tipo)
        leitura = escolher(bruta, tipo, p.seq_esperada, p.intervalo_maximo)
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

        # fallback 1: outro motor escolhido pelo usuário (antes da IA). Só quando
        # o principal não reconheceu. Se o motor de fallback for local, reusa as
        # páginas já preparadas pra OCR; se for de IA, prepara sem OCR.
        fb = p.motor_fallback
        if not v.aprovado and fb and fb != p.motor_id and disponivel(fb, cfg):
            fb_local = fb.split(":")[0] in LOCAIS
            if fb_local and p.modo != "ia":  # `paginas` já está preparado pra OCR
                paginas_fb = paginas
            else:
                paginas_fb = preparar(arquivo, para_ocr=fb_local)
                preparados.extend(paginas_fb)
            res_fb = _melhor_de_paginas(resolve(fb, cfg), paginas_fb, tipo, p)
            if res_fb and (res_fb[1].aprovado or not v.aprovado):
                leitura, v = res_fb

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
    ao_completar: Callable[[LinhaResultado], None] | None = None,
) -> list[LinhaResultado]:
    """Roda a leitura de todos os arquivos da pasta (em paralelo, `cfg.concorrencia`
    workers) e devolve a lista completa ordenada por nome. `ao_completar`, se dado,
    é chamado uma vez por arquivo assim que a leitura DELE termina (não espera o
    lote todo) -- é a deixa pra quem chama já ir copiando/renomeando arquivo por
    arquivo, em vez de só no final. A chamada acontece sempre na mesma thread que
    chamou `rodar()` (o loop `as_completed` abaixo é sequencial), nunca em paralelo
    entre si, então quem implementa `ao_completar` não precisa de lock próprio."""
    if not disponivel(p.motor_id, cfg):
        raise ValueError(
            f"O motor {p.motor_id} precisa de uma chave de API. Use 'Configurar chaves…'."
        )
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
            linha = fut.result()
            resultados.append(linha)
            feitos += 1
            progresso(feitos, total)
            if ao_completar is not None:
                ao_completar(linha)

    resultados.sort(key=lambda r: r.arquivo)
    return resultados
