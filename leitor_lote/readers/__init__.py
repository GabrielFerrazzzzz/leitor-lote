from __future__ import annotations

import shutil

from leitor_lote.readers.base import Reader

MOTORES_IDS: list[str] = [
    "tesseract",
    "rapidocr",
    "openai:gpt-5-mini",
    "openai:gpt-5",
    "mistral-ocr",
]
LOCAIS: set[str] = {"tesseract", "rapidocr"}


def resolve(motor_id: str, config) -> Reader:
    base, _, modelo = motor_id.partition(":")
    if base == "tesseract":
        from leitor_lote.readers.tesseract_reader import TesseractReader

        return TesseractReader()
    if base == "rapidocr":
        from leitor_lote.readers.rapidocr_reader import RapidOcrReader

        return RapidOcrReader()
    if base == "openai":
        from leitor_lote.readers.openai_reader import OpenAIReader

        return OpenAIReader(modelo=modelo or "gpt-5-mini", chave=config.chave_openai)
    if base == "mistral-ocr":
        from leitor_lote.readers.mistral_reader import MistralOcrReader

        return MistralOcrReader(chave=config.chave_mistral)
    raise ValueError(f"motor desconhecido: {motor_id}")


def disponivel(motor_id: str, config) -> bool:
    base = motor_id.split(":")[0]
    if base == "openai":
        return bool(config.chave_openai)
    if base == "mistral-ocr":
        return bool(config.chave_mistral)
    if base == "tesseract":
        return shutil.which("tesseract") is not None
    return True
