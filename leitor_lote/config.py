from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from leitor_lote.models import Campo, Tipo

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "leitor-lote"
CONFIG_PATH = APP_DIR / "config.json"
FALLBACK_PATH = Path(__file__).with_name("tipos.fallback.json")


@dataclass
class Config:
    chave_openai: str | None = None
    chave_mistral: str | None = None
    ultima_pasta: str | None = None
    motor_padrao: str | None = None
    concorrencia: int = 5
    limiar_confianca: float = 0.6
    motor_ia_fallback: str = "openai:gpt-5-mini"
    tipos_url: str = "https://raw.githubusercontent.com/GabrielFerrazzzzz/leitor-lote/main/tipos.json"


def carregar() -> Config:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            c = Config()
            salvar(c)
            return c
        campos = Config.__dataclass_fields__
        c = Config(**{k: v for k, v in data.items() if k in campos})
        try:
            c.concorrencia = int(c.concorrencia)
        except (TypeError, ValueError):
            c.concorrencia = 5
        try:
            c.limiar_confianca = float(c.limiar_confianca)
        except (TypeError, ValueError):
            c.limiar_confianca = 0.6
        return c
    c = Config()
    salvar(c)
    return c


def salvar(c: Config) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(c), indent=2, ensure_ascii=False), "utf-8")


def _parse_tipos(raw: list[dict]) -> dict[str, Tipo]:
    out: dict[str, Tipo] = {}
    for t in raw:
        campos_raw = t.get("campos") or [{"nome": "numero", "tamanho": 6, "sequencial": True}]
        campos = tuple(
            Campo(
                nome=c["nome"],
                tamanho=int(c.get("tamanho", 6)),
                sequencial=bool(c.get("sequencial", False)),
            )
            for c in campos_raw
        )
        out[t["id"]] = Tipo(
            id=t["id"],
            nome=t["nome"],
            prompt=t["prompt"],
            modo=t.get("modo", "auto"),
            motor=t.get("motor", "rapidocr"),
            campos=campos,
            formato_exemplo=t.get("formato_exemplo", ""),
        )
    return out


def buscar_tipos(cfg: Config) -> dict[str, Tipo]:
    try:
        resp = httpx.get(cfg.tipos_url, timeout=5.0)
        resp.raise_for_status()
        return _parse_tipos(resp.json())
    except Exception:  # noqa: BLE001
        return _parse_tipos(json.loads(FALLBACK_PATH.read_text("utf-8")))
