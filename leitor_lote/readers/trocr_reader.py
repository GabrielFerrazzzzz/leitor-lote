from __future__ import annotations

import os
import threading
from pathlib import Path

from PIL import Image

from leitor_lote.models import PreparedImage, Reading, Tipo

MODEL_ID = "microsoft/trocr-large-handwritten"
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "leitor-lote" / "models"

_pipe_lock = threading.Lock()
_pipe_instancia = None


def _pipe():
    # mesmo risco do RapidOCR (ver rapidocr_reader.py): sem lock, os workers da
    # 1a rodada correriam pra carregar o modelo (aqui, 1.3GB) ao mesmo tempo.
    global _pipe_instancia
    if _pipe_instancia is None:
        with _pipe_lock:
            if _pipe_instancia is None:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel

                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                proc = TrOCRProcessor.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
                model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
                _pipe_instancia = (proc, model)
    return _pipe_instancia


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
