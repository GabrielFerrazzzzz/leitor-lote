from __future__ import annotations

from typing import Protocol, runtime_checkable

from leitor_lote.models import PreparedImage, Reading, Tipo


@runtime_checkable
class Reader(Protocol):
    id: str
    requer_chave: bool

    def disponivel(self, config) -> bool: ...

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading: ...
