from __future__ import annotations

import base64
import time

import httpx

from leitor_lote.models import PreparedImage, Reading, Tipo

URL = "https://api.openai.com/v1/responses"


class OpenAIReader:
    id = "openai"
    requer_chave = True

    def __init__(self, modelo: str = "gpt-5-mini", chave: str | None = None):
        self.modelo = modelo
        self.chave = chave

    def disponivel(self, config) -> bool:
        return bool(self.chave or (config and config.chave_openai))

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        data_url = f"data:{imagem.mimetype};base64,{base64.b64encode(imagem.bytes_).decode()}"
        body = {
            "model": self.modelo,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_image", "detail": "auto", "image_url": data_url},
                        {"type": "input_text", "text": tipo.prompt},
                    ],
                }
            ],
            "max_output_tokens": 300,
        }
        headers = {"Authorization": f"Bearer {self.chave}", "Content-Type": "application/json"}
        ultimo: Exception | None = None
        for tentativa in range(1, 4):
            try:
                r = httpx.post(URL, json=body, headers=headers, timeout=60.0)
                if (r.status_code == 429 or r.status_code >= 500) and tentativa < 3:
                    time.sleep(tentativa * 2)
                    continue
                r.raise_for_status()
                texto = r.json()["output"][0]["content"][0]["text"].strip()
                return Reading(
                    valor=texto, confianca=None, motor=f"openai:{self.modelo}", bruto=texto
                )
            except Exception as e:  # noqa: BLE001
                ultimo = e
                if tentativa < 3:
                    time.sleep(tentativa)
        raise RuntimeError(f"OpenAI falhou apos 3 tentativas: {ultimo}")
