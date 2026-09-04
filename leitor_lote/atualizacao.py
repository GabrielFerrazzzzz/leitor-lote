from __future__ import annotations

import httpx

URL_RELEASE_LATEST = "https://api.github.com/repos/GabrielFerrazzzzz/leitor-lote/releases/latest"
URL_INSTALADOR = (
    "https://github.com/GabrielFerrazzzzz/leitor-lote/releases/latest/download/"
    "leitor-lote-setup.exe"
)


def versao_mais_recente() -> str | None:
    """Consulta o release mais recente do repositório no GitHub e retorna a versão
    (sem o 'v' inicial, ex. "0.2.0"). Retorna None em qualquer falha — rede fora do
    ar, resposta não-200, JSON malformado, chave ausente — nunca lança."""
    try:
        resp = httpx.get(URL_RELEASE_LATEST, timeout=5.0)
        resp.raise_for_status()
        tag = resp.json()["tag_name"]
        if not isinstance(tag, str):
            return None
        return tag.removeprefix("v")
    except Exception:  # noqa: BLE001
        return None


def _partes_versao(versao: str) -> tuple[int, ...] | None:
    partes = versao.strip().split(".")
    if not partes or any(not p.isdigit() for p in partes):
        return None
    return tuple(int(p) for p in partes)


def versao_e_mais_nova(atual: str, remota: str) -> bool:
    """Compara duas versões "X.Y.Z"-like como tuplas de inteiros (partes que faltam
    viram 0). Se `atual` ou `remota` não parsear como versão limpa (só dígitos
    separados por ponto), retorna False em vez de lançar."""
    a = _partes_versao(atual)
    r = _partes_versao(remota)
    if a is None or r is None:
        return False
    n = max(len(a), len(r))
    a = a + (0,) * (n - len(a))
    r = r + (0,) * (n - len(r))
    return r > a
