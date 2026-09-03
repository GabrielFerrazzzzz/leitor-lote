from __future__ import annotations

import os
from functools import cache
from pathlib import Path

from PIL import Image

from leitor_lote.models import PreparedImage, Reading, Tipo

MODEL_ID = "microsoft/trocr-large-handwritten"
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "leitor-lote" / "models"


@cache
def _pipe():
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    proc = TrOCRProcessor.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
    return proc, model


class TrOcrReader:
    id = "trocr"
    requer_chave = False

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        proc, model = _pipe()
        with Image.open(imagem.caminho_tmp) as img:
            rgb = img.convert("RGB")
        pixel_values = proc(images=rgb, return_tensors="pt").pixel_values
        ids = model.generate(pixel_values, max_new_tokens=32)
        texto = proc.batch_decode(ids, skip_special_tokens=True)[0]
        valor = texto
        return Reading(valor=valor, confianca=None, motor="trocr", bruto=texto)
