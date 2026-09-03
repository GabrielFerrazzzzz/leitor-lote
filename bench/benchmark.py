from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from leitor_lote import config as cfgmod
from leitor_lote.preprocess import preparar
from leitor_lote.readers import LOCAIS, resolve

_LOCAIS_BASE = LOCAIS


def lev(a: str, b: str) -> int:
    linha = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, linha[0] = linha[0], i
        for j, cb in enumerate(b, 1):
            prev, linha[j] = linha[j], min(linha[j] + 1, linha[j - 1] + 1, prev + (ca != cb))
    return linha[-1]


def _so_digitos(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def cer_digitos(esperado: str, obtido: str) -> float:
    e, o = _so_digitos(esperado), _so_digitos(obtido)
    return lev(e, o) / max(1, len(e))


def _gabarito(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig") as f:
        return {r["arquivo"]: r.get("esperado", "") for r in csv.DictReader(f)}


def _tipo(tipo_id: str):
    cfg = cfgmod.carregar()
    return cfgmod.buscar_tipos(cfg)[tipo_id]


def rodar(pasta: Path, gabarito: Path, tipo_id: str, motores: list[str]) -> list[dict]:
    cfg = cfgmod.carregar()
    tipo = _tipo(tipo_id)
    esperados = _gabarito(gabarito)
    saida: list[dict] = []
    for motor_id in motores:
        reader = resolve(motor_id, cfg)
        local = motor_id.split(":")[0] in _LOCAIS_BASE
        acertos = naorec = 0
        soma_cer = soma_t = 0.0
        for arquivo, esperado in esperados.items():
            img = preparar(pasta / arquivo, para_ocr=local)[0]
            ini = time.time()
            leitura = reader.read(img, tipo)
            soma_t += time.time() - ini
            obtido = _so_digitos(leitura.valor)
            if obtido == _so_digitos(esperado):
                acertos += 1
            if not obtido:
                naorec += 1
            soma_cer += cer_digitos(esperado, obtido)
        n = max(1, len(esperados))
        saida.append(
            {
                "motor": motor_id,
                "acerto_%": round(100 * acertos / n, 1),
                "cer_digito": round(soma_cer / n, 3),
                "nao_reconhecido": naorec,
                "seg_por_arq": round(soma_t / n, 2),
            }
        )
    return saida


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark de motores de OCR do leitor-lote")
    ap.add_argument("--pasta", required=True, type=Path)
    ap.add_argument("--gabarito", required=True, type=Path)
    ap.add_argument("--tipo", required=True)
    ap.add_argument("--motores", required=True, help="lista separada por virgula")
    args = ap.parse_args()

    linhas = rodar(args.pasta, args.gabarito, args.tipo, args.motores.split(","))
    for linha in linhas:
        print(linha)
    destino = Path("bench") / f"resultado-{time.strftime('%Y-%m-%d')}.csv"
    destino.parent.mkdir(exist_ok=True)
    with destino.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(f"gravado: {destino}")


if __name__ == "__main__":
    main()
