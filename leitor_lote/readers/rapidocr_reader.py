from __future__ import annotations

from functools import cache

from leitor_lote.models import PreparedImage, Reading, Tipo


@cache
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


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
