from __future__ import annotations

import threading

from leitor_lote.models import PreparedImage, Reading, Tipo

_engine_lock = threading.Lock()
_engine_instancia = None


def _engine():
    # sem lock, os N workers da 1a rodada corririam pra construir o RapidOCR()
    # ao mesmo tempo (cada um carregando o modelo ONNX do zero) -- é isso que
    # trava a janela por alguns segundos no início. Com o lock, só o primeiro
    # carrega; os outros esperam e reusam a mesma instância.
    global _engine_instancia
    if _engine_instancia is None:
        with _engine_lock:
            if _engine_instancia is None:
                from rapidocr_onnxruntime import RapidOCR

                _engine_instancia = RapidOCR()
    return _engine_instancia


class RapidOcrReader:
    id = "rapidocr"
    requer_chave = False

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        resultado, _ = _engine()(str(imagem.caminho_tmp))
        linhas = resultado or []
        textos = [linha[1] for linha in linhas]
        scores = [float(linha[2]) for linha in linhas]
        valor = "\n".join(textos)
        conf = (sum(scores) / len(scores)) if scores else None
        return Reading(valor=valor, confianca=conf, motor="rapidocr", bruto=str(linhas))
