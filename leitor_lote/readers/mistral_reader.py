from __future__ import annotations

import base64

import httpx

from leitor_lote.models import PreparedImage, Reading, Tipo

URL = "https://api.mistral.ai/v1/ocr"


class MistralOcrReader:
    id = "mistral-ocr"
    requer_chave = True

    def __init__(self, chave: str | None = None):
        self.chave = chave

    def disponivel(self, config) -> bool:
        return bool(self.chave or (config and config.chave_mistral))

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        data_url = f"data:{imagem.mimetype};base64,{base64.b64encode(imagem.bytes_).decode()}"
        body = {
            "model": "mistral-ocr-latest",
            "document": {"type": "image_url", "image_url": data_url},
        }
        headers = {"Authorization": f"Bearer {self.chave}", "Content-Type": "application/json"}
        r = httpx.post(URL, json=body, headers=headers, timeout=60.0)
        r.raise_for_status()
        texto = "\n".join(p.get("markdown", "") for p in r.json().get("pages", [])).strip()
        valor = texto
        return Reading(valor=valor, confianca=None, motor="mistral-ocr", bruto=texto)
