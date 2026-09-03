from __future__ import annotations

from leitor_lote.readers.base import Reader

MOTORES_IDS: list[str] = [
    "tesseract",
    "paddleocr",
    "trocr",
    "openai:gpt-5-mini",
    "openai:gpt-5",
    "mistral-ocr",
]
LOCAIS: set[str] = {"tesseract", "paddleocr", "trocr"}


def resolve(motor_id: str, config) -> Reader:
    base, _, modelo = motor_id.partition(":")
    if base == "tesseract":
        from leitor_lote.readers.tesseract_reader import TesseractReader

        return TesseractReader()
    if base == "paddleocr":
        from leitor_lote.readers.paddleocr_reader import PaddleOcrReader

        return PaddleOcrReader()
    if base == "trocr":
        from leitor_lote.readers.trocr_reader import TrOcrReader

        return TrOcrReader()
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
    return True
