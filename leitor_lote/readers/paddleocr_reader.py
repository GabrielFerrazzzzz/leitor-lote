from __future__ import annotations

from functools import cache

from leitor_lote.models import PreparedImage, Reading, Tipo


@cache
def _engine():
    from paddleocr import PaddleOCR

    return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)


class PaddleOcrReader:
    id = "paddleocr"
    requer_chave = False

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        res = _engine().ocr(str(imagem.caminho_tmp), cls=True)
        linhas = res[0] if res else []
        textos: list[str] = []
        scores: list[float] = []
        for _, (txt, score) in linhas:
            textos.append(txt)
            scores.append(float(score))
        valor = "".join(ch for ch in "".join(textos) if ch.isdigit())
        conf = (sum(scores) / len(scores)) if scores else None
        return Reading(valor=valor, confianca=conf, motor="paddleocr", bruto=str(linhas))
