from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from leitor_lote import config as cfgmod
from leitor_lote.models import ParametrosRodada
from leitor_lote.pipeline import rodar
from leitor_lote.readers import LOCAIS, MOTORES_IDS, disponivel


def opcoes_motor(modo: str, cfg: cfgmod.Config) -> list[tuple[str, bool]]:
    quer_local = modo in ("ocr", "auto")
    ids = [m for m in MOTORES_IDS if (m.split(":")[0] in LOCAIS) == quer_local]
    return [(m, disponivel(m, cfg)) for m in ids]


def montar_parametros(
    pasta: str, tipo_id: str, motor_id: str, modo: str, seq: str, intervalo: str
) -> ParametrosRodada:
    return ParametrosRodada(
        pasta_entrada=Path(pasta),
        tipo_id=tipo_id,
        motor_id=motor_id,
        modo=modo,  # type: ignore[arg-type]
        seq_esperada=int(seq) if seq.strip() else None,
        intervalo_maximo=int(intervalo) if intervalo.strip() else None,
    )


def rodar_janela() -> None:  # pragma: no cover - exercitado manualmente
    cfg = cfgmod.carregar()
    tipos = cfgmod.buscar_tipos(cfg)
    cancel = threading.Event()

    root = tk.Tk()
    root.title("leitor-lote")
    root.geometry("460x360")

    pasta_var = tk.StringVar(value=cfg.ultima_pasta or "")
    tipo_var = tk.StringVar(value=next(iter(tipos)))
    modo_var = tk.StringVar(value=tipos[tipo_var.get()].modo)
    motor_var = tk.StringVar(value=tipos[tipo_var.get()].motor)
    seq_var = tk.StringVar()
    int_var = tk.StringVar()

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    def escolher_pasta() -> None:
        d = filedialog.askdirectory(initialdir=pasta_var.get() or None)
        if d:
            pasta_var.set(d)

    ttk.Label(frm, text="Pasta").grid(row=0, column=0, sticky="w")
    ttk.Entry(frm, textvariable=pasta_var, width=36).grid(row=0, column=1)
    ttk.Button(frm, text="Procurar", command=escolher_pasta).grid(row=0, column=2)

    ttk.Label(frm, text="Tipo").grid(row=1, column=0, sticky="w")
    cb_tipo = ttk.Combobox(frm, textvariable=tipo_var, values=list(tipos), state="readonly")
    cb_tipo.grid(row=1, column=1, columnspan=2, sticky="we")

    ttk.Label(frm, text="Modo").grid(row=2, column=0, sticky="w")
    cb_modo = ttk.Combobox(frm, textvariable=modo_var, values=["ocr", "ia", "auto"],
                           state="readonly")
    cb_modo.grid(row=2, column=1, columnspan=2, sticky="we")

    ttk.Label(frm, text="Motor").grid(row=3, column=0, sticky="w")
    cb_motor = ttk.Combobox(frm, textvariable=motor_var, state="readonly")
    cb_motor.grid(row=3, column=1, columnspan=2, sticky="we")

    def atualizar_motores(*_a) -> None:
        opts = opcoes_motor(modo_var.get(), cfg)
        cb_motor["values"] = [m for m, _ in opts]
        habilitados = [m for m, ok in opts if ok]
        if motor_var.get() not in habilitados and habilitados:
            motor_var.set(habilitados[0])

    def ao_trocar_tipo(*_a) -> None:
        t = tipos[tipo_var.get()]
        modo_var.set(t.modo)
        motor_var.set(t.motor)
        atualizar_motores()

    tipo_var.trace_add("write", ao_trocar_tipo)
    modo_var.trace_add("write", atualizar_motores)
    atualizar_motores()

    ttk.Label(frm, text="Sequência esperada").grid(row=4, column=0, sticky="w")
    ttk.Entry(frm, textvariable=seq_var).grid(row=4, column=1, columnspan=2, sticky="we")
    ttk.Label(frm, text="Intervalo máximo").grid(row=5, column=0, sticky="w")
    ttk.Entry(frm, textvariable=int_var).grid(row=5, column=1, columnspan=2, sticky="we")

    def configurar_chaves() -> None:
        d = tk.Toplevel(root)
        d.title("Chaves")
        o = tk.StringVar(value=cfg.chave_openai or "")
        m = tk.StringVar(value=cfg.chave_mistral or "")
        ttk.Label(d, text="OpenAI").grid(row=0, column=0)
        ttk.Entry(d, textvariable=o, show="*", width=40).grid(row=0, column=1)
        ttk.Label(d, text="Mistral").grid(row=1, column=0)
        ttk.Entry(d, textvariable=m, show="*", width=40).grid(row=1, column=1)

        def salvar_() -> None:
            cfg.chave_openai = o.get().strip() or None
            cfg.chave_mistral = m.get().strip() or None
            cfgmod.salvar(cfg)
            atualizar_motores()
            d.destroy()

        ttk.Button(d, text="Salvar", command=salvar_).grid(row=2, column=0, columnspan=2)

    ttk.Button(frm, text="Configurar chaves…", command=configurar_chaves).grid(
        row=6, column=0, columnspan=3, pady=(8, 0)
    )

    barra = ttk.Progressbar(frm, maximum=100)
    barra.grid(row=7, column=0, columnspan=3, sticky="we", pady=8)
    status = ttk.Label(frm, text="")
    status.grid(row=8, column=0, columnspan=3)
    btn = ttk.Button(frm, text="Rodar")
    btn.grid(row=9, column=0, columnspan=3)

    def progresso(feitos: int, total: int) -> None:
        pct = 0 if total == 0 else int(100 * feitos / total)
        root.after(0, lambda: (barra.config(value=pct), status.config(text=f"{feitos} de {total}")))

    def concluir(linhas) -> None:
        from leitor_lote.output import gravar

        saida = Path(pasta_var.get()) / "saida"
        gravar(linhas, saida)
        ok = sum(1 for x in linhas if x.status == "ok")
        nr = sum(1 for x in linhas if x.status == "nao_reconhecido")
        er = sum(1 for x in linhas if x.status == "erro")
        cfg.ultima_pasta = pasta_var.get()
        cfgmod.salvar(cfg)
        root.after(0, lambda: _fim(saida, ok, nr, er))

    def _fim(saida: Path, ok: int, nr: int, er: int) -> None:
        status.config(text=f"Concluído — {ok} ok, {nr} não reconhecidos, {er} erros")
        btn.config(text="Abrir pasta de saída", command=lambda: _abrir(saida), state="normal")

    def _abrir(p: Path) -> None:
        import os

        os.startfile(p)  # Windows: abre a pasta no Explorer

    def executar() -> None:
        if not pasta_var.get() or not Path(pasta_var.get()).is_dir():
            messagebox.showerror("leitor-lote", "Escolha uma pasta válida.")
            return
        btn.config(state="disabled")
        p = montar_parametros(
            pasta_var.get(), tipo_var.get(), motor_var.get(), modo_var.get(),
            seq_var.get(), int_var.get(),
        )

        def trabalho() -> None:
            linhas = rodar(p, cfg, tipos, progresso, cancel)
            concluir(linhas)

        threading.Thread(target=trabalho, daemon=True).start()

    btn.config(command=executar)
    root.mainloop()
