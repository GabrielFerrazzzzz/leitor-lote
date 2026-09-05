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


def _tentar_secundario(motor_id, arquivo, paginas_ocr, principal_e_ocr,
                       p, cfg, tipo, preparados):
    """Tenta um motor secundário (fallback). Devolve (leitura, v) se rodou, ou
    None se o motor não está disponível OU se levantou exceção. Um fallback que
    quebra (ex.: TrOCR sem o modelo baixado, ou API sem rede) NÃO derruba o
    resultado do motor principal pra 'erro' -- só é ignorado."""
    if not motor_id or not disponivel(motor_id, cfg):
        return None
    try:
        local = motor_id.split(":")[0] in LOCAIS
        if local and principal_e_ocr:
            paginas = paginas_ocr  # reusa as páginas já preparadas pra OCR
        else:
            paginas = preparar(arquivo, para_ocr=local)
            preparados.extend(paginas)
        return _melhor_de_paginas(resolve(motor_id, cfg), paginas, tipo, p)
    except Exception:  # noqa: BLE001
        return None


def _ler_um(arquivo: Path, p: ParametrosRodada, cfg: Config, tipo: Tipo,
            cancel: threading.Event) -> LinhaResultado:
    if cancel.is_set():
        return LinhaResultado(arquivo.name, "", None, "", "erro", "cancelado")
    preparados: list = []
    try:
        principal_e_ocr = p.modo != "ia"
        paginas = preparar(arquivo, para_ocr=principal_e_ocr)
        preparados.extend(paginas)
        leitura, v = _melhor_de_paginas(resolve(p.motor_id, cfg), paginas, tipo, p)

        # fallback 1: outro motor escolhido pelo usuário (antes da IA), só quando
        # o principal não reconheceu. Se esse motor quebrar, mantém o resultado
        # do principal (ver _tentar_secundario).
        if not v.aprovado and p.motor_fallback and p.motor_fallback != p.motor_id:
            res_fb = _tentar_secundario(p.motor_fallback, arquivo, paginas,
                                        principal_e_ocr, p, cfg, tipo, preparados)
            if res_fb and (res_fb[1].aprovado or not v.aprovado):
                leitura, v = res_fb

        # fallback 2: IA (modo auto) — inalterado, só passou a usar o helper
        if p.modo == "auto":
            baixa_conf = leitura.confianca is not None and leitura.confianca < cfg.limiar_confianca
            if not v.aprovado or baixa_conf:
                res2 = _tentar_secundario(cfg.motor_ia_fallback, arquivo, paginas,
                                          principal_e_ocr, p, cfg, tipo, preparados)
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
