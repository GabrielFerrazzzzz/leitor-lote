"""Login opcional na Soma. Com uma sessão válida, o motor "soma" manda cada
imagem direto pro worker da Soma ler (chave da OpenAI fica no servidor) --
o mesmo login do site automacoes-soma. Sem isso, o app segue 100% local.

Nada aqui toca no banco/Storage do Supabase além do próprio /auth (login e
refresh de token). A anon key abaixo é pública (a mesma que o site embute)."""
from __future__ import annotations

import base64

import httpx

SUPABASE_URL = "https://qsqlhsqzcfrlqkyehpjt.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFzcWxoc3F6"
    "Y2ZybHFreWVocGp0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3NDQ0ODgsImV4cCI6MjA5NTMyMDQ4OH0"
    ".hxR8Fq15fOhAeCkfJ8vHzjFw5umEFObDew28K46pUFw"
)
WORKER_URL = "https://leitura-soma-worker.aavihi.easypanel.host"


class SomaAuthError(RuntimeError):
    """Login/refresh recusado pela Soma (credencial errada, token expirado)."""


def _post_auth(caminho: str, corpo: dict) -> dict:
    r = httpx.post(
        f"{SUPABASE_URL}/auth/v1/{caminho}",
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json=corpo,
        timeout=15.0,
    )
    dados = r.json() if r.content else {}
    if r.status_code != 200 or "access_token" not in dados:
        msg = dados.get("error_description") or dados.get("msg") or f"HTTP {r.status_code}"
        raise SomaAuthError(msg)
    return dados


def login(email: str, senha: str) -> dict:
    """Devolve {'email', 'access_token', 'refresh_token'}. Levanta SomaAuthError."""
    d = _post_auth("token?grant_type=password", {"email": email, "password": senha})
    return {
        "email": (d.get("user") or {}).get("email") or email,
        "access_token": d["access_token"],
        "refresh_token": d["refresh_token"],
    }


def refresh(refresh_token: str) -> dict:
    """Renova a sessão a partir do refresh_token. Levanta SomaAuthError."""
    d = _post_auth("token?grant_type=refresh_token", {"refresh_token": refresh_token})
    return {
        "email": (d.get("user") or {}).get("email"),
        "access_token": d["access_token"],
        "refresh_token": d["refresh_token"],
    }


def ler_imagem(dados: bytes, prompt: str, token: str, nome: str = "imagem.jpg") -> str:
    """Manda a imagem pro worker da Soma ler. Devolve o texto (número(s)).
    Levanta SomaAuthError em 401 (token inválido) e RuntimeError no resto."""
    r = httpx.post(
        f"{WORKER_URL}/ler",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "image/jpeg",
            "X-Prompt": base64.b64encode(prompt.encode("utf-8")).decode("ascii"),
            "X-Filename": nome,
        },
        content=dados,
        timeout=120.0,
    )
    corpo = r.json() if r.content else {}
    if r.status_code == 401:
        raise SomaAuthError(corpo.get("erro") or "login expirado")
    if r.status_code != 200 or "numero" not in corpo:
        raise RuntimeError(corpo.get("erro") or f"worker HTTP {r.status_code}")
    return str(corpo["numero"]).strip()
