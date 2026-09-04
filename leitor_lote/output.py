from __future__ import annotations

import csv
import re
import shutil
import unicodedata
from pathlib import Path

from leitor_lote.models import LinhaResultado

COLUNAS = ["arquivo", "texto_lido", "confianca", "motor", "status", "erro"]


def limpar_nome(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9]+", "_", s.upper()).strip("_")
    return s or "SEM_LEITURA"


def _nome_unico(base: str, ext: str, usados: dict[str, int]) -> str:
    n = usados.get(base, 0) + 1
    usados[base] = n
    return f"{base}{ext}" if n == 1 else f"{base}_{n}{ext}"


def copiar_arquivos(linhas: list[LinhaResultado], pasta_saida: Path) -> None:
    """Copia cada arquivo lido para `pasta_saida` com o nome renomeado (número lido,
    ou ERRO_<nome original> quando a leitura falhou). Não grava CSV nem log — só cópias."""
    pasta_entrada = pasta_saida.parent
    pasta_saida.mkdir(parents=True, exist_ok=True)
    usados: dict[str, int] = {}

    for linha in linhas:
        origem = pasta_entrada / linha.arquivo
        if not origem.exists():
            continue
        if linha.status == "erro":
            base = "ERRO_" + limpar_nome(Path(linha.arquivo).stem)
        else:
            base = limpar_nome(linha.texto_lido)
        destino = pasta_saida / _nome_unico(base, origem.suffix.lower(), usados)
        shutil.copy2(origem, destino)


def exportar_csv(linhas: list[LinhaResultado], caminho_csv: Path) -> None:
    """Grava `linhas` como CSV (utf-8-sig, mesmo cabeçalho de sempre) no caminho
    escolhido pelo usuário — livre, não precisa estar dentro de `pasta_saida`."""
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    with caminho_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUNAS)
        for linha in linhas:
            w.writerow(
                [
                    linha.arquivo,
                    linha.texto_lido,
                    "" if linha.confianca is None else f"{linha.confianca:.3f}",
                    linha.motor,
                    linha.status,
                    linha.erro or "",
                ]
            )
