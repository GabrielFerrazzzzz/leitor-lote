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


def copiar_um(
    linha: LinhaResultado, pasta_entrada: Path, pasta_saida: Path, usados: dict[str, int]
) -> None:
    """Copia UM arquivo lido pra `pasta_saida` com o nome renomeado. `usados` é
    compartilhado entre chamadas (mesmo dict) pra dedupe funcionar no lote inteiro,
    mesmo chamando arquivo por arquivo conforme cada leitura termina. Pula
    "cancelado" (arquivo nunca foi lido de verdade -- não é erro de leitura,
    é só o que sobrou na fila quando o usuário cancelou; não faz sentido copiar
    como ERRO_)."""
    if linha.erro == "cancelado":
        return
    origem = pasta_entrada / linha.arquivo
    if not origem.exists():
        return
    ext = origem.suffix.lower()
    if linha.status == "erro":
        base = "ERRO_" + limpar_nome(Path(linha.arquivo).stem)
    else:
        base = limpar_nome(linha.texto_lido)
    # trava de segurança: um texto_lido gigante (ex.: OCR ruidoso num DANFE denso
    # devolvendo dezenas de "chaves") geraria um nome que estoura o limite de
    # caminho do Windows -> shutil.copy2 dava [WinError 3] e derrubava o lote todo.
    limite = max(8, 240 - len(str(pasta_saida)) - len(ext) - 5)  # 5 = "/", "_NN"
    base = base[:limite]
    destino = pasta_saida / _nome_unico(base, ext, usados)
    try:
        shutil.copy2(origem, destino)
    except OSError:
        pass  # um arquivo que não copia (nome/caminho, permissão) não para o lote


def copiar_arquivos(linhas: list[LinhaResultado], pasta_saida: Path) -> None:
    """Copia cada arquivo lido para `pasta_saida` com o nome renomeado (número lido,
    ou ERRO_<nome original> quando a leitura falhou). Não grava CSV nem log — só
    cópias. Usa `copiar_um` pra cada linha, todas de uma vez (quem quiser copiar
    conforme cada leitura termina, sem esperar o lote todo, chama `copiar_um`
    diretamente -- ver gui.py)."""
    pasta_entrada = pasta_saida.parent
    pasta_saida.mkdir(parents=True, exist_ok=True)
    usados: dict[str, int] = {}
    for linha in linhas:
        copiar_um(linha, pasta_entrada, pasta_saida, usados)


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
