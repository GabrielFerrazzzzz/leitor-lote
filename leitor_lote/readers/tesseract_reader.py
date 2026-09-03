from __future__ import annotations

import shutil

import pytesseract
from PIL import Image

from leitor_lote.models import PreparedImage, Reading, Tipo

_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789"


class TesseractReader:
    id = "tesseract"
    requer_chave = False

    def disponivel(self, config) -> bool:
        return shutil.which("tesseract") is not None

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        with Image.open(imagem.caminho_tmp) as img:
            data = pytesseract.image_to_data(
                img, config=_CONFIG, output_type=pytesseract.Output.DICT
            )
        tokens = [(t, c) for t, c in zip(data["text"], data["conf"]) if t.strip()]
        valor = " ".join(t for t, _ in tokens)
        confs = [int(c) for _, c in tokens if str(c).lstrip("-").isdigit() and int(c) >= 0]
        conf = (sum(confs) / len(confs) / 100.0) if confs else None
        return Reading(valor=valor, confianca=conf, motor="tesseract", bruto=repr(tokens))
