from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Modo = Literal["ocr", "ia", "auto"]
Status = Literal["ok", "nao_reconhecido", "erro"]


@dataclass(frozen=True)
class Reading:
    valor: str
    confianca: float | None
    motor: str
    bruto: str


@dataclass(frozen=True)
class PreparedImage:
    bytes_: bytes
    mimetype: str
    largura: int
    altura: int
    caminho_tmp: Path


@dataclass(frozen=True)
class Campo:
    nome: str
    tamanho: int = 6


@dataclass(frozen=True)
class Tipo:
    id: str
    nome: str
    prompt: str
    modo: Modo
    motor: str
    campos: tuple[Campo, ...]
    formato_exemplo: str = ""


@dataclass(frozen=True)
class ResultadoValidado:
    texto_lido: str
    aprovado: bool
    motivo: str | None


@dataclass(frozen=True)
class LinhaResultado:
    arquivo: str
    texto_lido: str
    confianca: float | None
    motor: str
    status: Status
    erro: str | None


@dataclass(frozen=True)
class ParametrosRodada:
    pasta_entrada: Path
    tipo_id: str
    motor_id: str
    modo: Modo
    seq_esperada: int | None
    intervalo_maximo: int | None
