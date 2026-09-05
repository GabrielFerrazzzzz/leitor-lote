from __future__ import annotations

import threading

from leitor_lote import soma
from leitor_lote.models import PreparedImage, Reading, Tipo

_refresh_lock = threading.Lock()


class SomaReader:
    """Motor "soma": manda a imagem pro worker da Soma ler (chave da OpenAI no
    servidor deles). Precisa de um login válido em `config` (cfg.soma_token).
    Em 401 tenta renovar o token uma vez, com lock (só um worker renova)."""

    id = "soma"
    requer_chave = False

    def __init__(self, config) -> None:
        self._cfg = config

    def disponivel(self, config) -> bool:
        return bool(config.soma_token)

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        try:
            texto = soma.ler_imagem(
                imagem.bytes_, tipo.prompt, self._cfg.soma_token, imagem.caminho_tmp.name
            )
        except soma.SomaAuthError:
            texto = self._retry_apos_refresh(imagem, tipo)
        return Reading(valor=texto, confianca=None, motor="soma", bruto=texto)

    def _retry_apos_refresh(self, imagem: PreparedImage, tipo: Tipo) -> str:
        token_ruim = self._cfg.soma_token
        with _refresh_lock:
            if self._cfg.soma_token == token_ruim:  # ninguém renovou ainda
                if not self._cfg.soma_refresh:
                    raise soma.SomaAuthError("sessão expirada -- entre na Soma de novo")
                nova = soma.refresh(self._cfg.soma_refresh)
                from leitor_lote import config as cfgmod

                self._cfg.soma_token = nova["access_token"]
                self._cfg.soma_refresh = nova["refresh_token"]
                cfgmod.salvar(self._cfg)
        return soma.ler_imagem(
            imagem.bytes_, tipo.prompt, self._cfg.soma_token, imagem.caminho_tmp.name
        )
