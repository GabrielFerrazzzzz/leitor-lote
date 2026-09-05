from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from leitor_lote import __version__, atualizacao, soma
from leitor_lote import config as cfgmod
from leitor_lote.models import LinhaResultado, ParametrosRodada
from leitor_lote.output import copiar_um, exportar_csv
from leitor_lote.pipeline import rodar
from leitor_lote.readers import LOCAIS, MOTORES_IDS, disponivel


def opcoes_motor(modo: str, cfg: cfgmod.Config) -> list[tuple[str, bool]]:
    quer_local = modo in ("ocr", "auto")
    ids = [m for m in MOTORES_IDS if (m.split(":")[0] in LOCAIS) == quer_local]
    return [(m, disponivel(m, cfg)) for m in ids]


def montar_parametros(
    pasta: str, tipo_id: str, motor_id: str, modo: str, seq: str, intervalo: str,
    motor_fallback: str | None = None,
) -> ParametrosRodada:
    return ParametrosRodada(
        pasta_entrada=Path(pasta),
        tipo_id=tipo_id,
        motor_id=motor_id,
        modo=modo,  # type: ignore[arg-type]
        seq_esperada=int(seq) if seq.strip() else None,
        intervalo_maximo=int(intervalo) if intervalo.strip() else None,
        motor_fallback=motor_fallback or None,
    )


def _estilizar_treeview_escuro() -> None:
    """Deixa o ttk.Treeview (única peça que não é CustomTkinter) com uma paleta
    escura coerente com o resto da janela, em vez de uma ilha clara."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Treeview",
        background="#2b2b2b",
        foreground="#dce4ee",
        fieldbackground="#2b2b2b",
        borderwidth=0,
        rowheight=22,
    )
    style.map(
        "Treeview",
        background=[("selected", "#1f6aa5")],
        foreground=[("selected", "#dce4ee")],
    )
    style.configure(
        "Treeview.Heading",
        background="#212121",
        foreground="#dce4ee",
        borderwidth=0,
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", "#2b2b2b")])
    # a barra de rolagem do Treeview também não é CustomTkinter — sem isso ficaria
    # cinza-claro padrão do tema "clam", destoando do resto escuro.
    style.configure(
        "Vertical.TScrollbar",
        background="#3a3a3a",
        troughcolor="#212121",
        bordercolor="#212121",
        arrowcolor="#dce4ee",
    )
    style.map("Vertical.TScrollbar", background=[("active", "#4a4a4a")])


def rodar_janela() -> None:  # pragma: no cover - exercitado manualmente
    cfg = cfgmod.carregar()
    tipos = cfgmod.buscar_tipos(cfg)
    cancel = threading.Event()
    ultimas_linhas: list[LinhaResultado] = []

    ctk.set_appearance_mode("dark")

    root = ctk.CTk()
    root.title("leitor-lote")
    root.geometry("640x520")
    root.minsize(600, 470)

    # --- banner de atualização disponível (fica oculto até a checagem achar algo) ---
    banner = ctk.CTkFrame(root, fg_color="#1e2f3f", corner_radius=0)
    banner_label = ctk.CTkLabel(
        banner, text="", text_color="#eaf2f8", font=ctk.CTkFont(weight="bold")
    )
    banner_label.pack(side="left", padx=(14, 8), pady=8)
    banner_btn = ctk.CTkButton(
        banner,
        text="Atualizar",
        width=100,
        command=lambda: webbrowser.open(atualizacao.URL_INSTALADOR),
    )
    banner_btn.pack(side="right", padx=14, pady=8)

    frm = ctk.CTkFrame(root)
    frm.pack(fill="both", expand=True, padx=14, pady=14)
    frm.grid_columnconfigure(1, weight=1)

    def _mostrar_banner_atualizacao(remota: str) -> None:
        banner_label.configure(text=f"Nova versão {remota} disponível")
        banner.pack(side="top", fill="x", before=frm)

    def _checar_atualizacao() -> None:
        remota = atualizacao.versao_mais_recente()
        if remota and atualizacao.versao_e_mais_nova(__version__, remota):
            root.after(0, lambda: _mostrar_banner_atualizacao(remota))

    threading.Thread(target=_checar_atualizacao, daemon=True).start()

    pasta_var = tk.StringVar(value=cfg.ultima_pasta or "")
    tipo_var = tk.StringVar(value=next(iter(tipos)))
    motor_var = tk.StringVar(value=tipos[tipo_var.get()].motor)
    fallback_var = tk.BooleanVar(value=tipos[tipo_var.get()].modo != "ocr")
    fb_motor_var = tk.BooleanVar(value=False)   # "tentar com outro motor" ligado?
    fb_motor_which = tk.StringVar()             # qual motor tentar
    seq_var = tk.StringVar()
    int_var = tk.StringVar()

    def escolher_pasta() -> None:
        d = filedialog.askdirectory(initialdir=pasta_var.get() or None)
        if d:
            pasta_var.set(d)

    ctk.CTkLabel(frm, text="Pasta").grid(row=0, column=0, sticky="w", pady=4)
    ctk.CTkEntry(frm, textvariable=pasta_var).grid(row=0, column=1, sticky="we", padx=6)
    ctk.CTkButton(frm, text="Procurar", width=90, command=escolher_pasta).grid(row=0, column=2)

    ctk.CTkLabel(frm, text="Tipo").grid(row=1, column=0, sticky="w", pady=4)
    cb_tipo = ctk.CTkComboBox(frm, variable=tipo_var, values=list(tipos), state="readonly")
    cb_tipo.grid(row=1, column=1, columnspan=2, sticky="we", padx=6)

    ctk.CTkLabel(frm, text="Motor").grid(row=2, column=0, sticky="w", pady=4)
    cb_motor = ctk.CTkComboBox(frm, variable=motor_var, state="readonly")
    cb_motor.grid(row=2, column=1, columnspan=2, sticky="we", padx=6)

    chk_fallback = ctk.CTkCheckBox(
        frm,
        text="Se não reconhecer, tentar de novo com IA",
        variable=fallback_var,
        onvalue=True,
        offvalue=False,
    )
    chk_fallback.grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 4))

    chk_fb_motor = ctk.CTkCheckBox(
        frm,
        text="Se não reconhecer, tentar com outro motor",
        variable=fb_motor_var,
        onvalue=True,
        offvalue=False,
    )
    chk_fb_motor.grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 2))
    cb_fb_motor = ctk.CTkComboBox(frm, variable=fb_motor_which, state="readonly")
    cb_fb_motor.grid(row=5, column=0, columnspan=3, sticky="we", padx=(24, 6), pady=(0, 6))

    def _motor_e_local(motor_id: str) -> bool:
        return motor_id.split(":")[0] in LOCAIS

    def modo_efetivo() -> str:
        """Traduz Motor + checkbox de fallback para o `modo` interno que o pipeline
        espera ("ocr"/"ia"/"auto") — ver ParametrosRodada.modo."""
        if _motor_e_local(motor_var.get()):
            return "auto" if fallback_var.get() else "ocr"
        return "ia"

    def atualizar_visibilidade_fallback(*_a) -> None:
        local = _motor_e_local(motor_var.get())
        (chk_fallback.grid if local else chk_fallback.grid_remove)()
        (chk_fb_motor.grid if local else chk_fb_motor.grid_remove)()
        if local and fb_motor_var.get():
            cb_fb_motor.grid()
        else:
            cb_fb_motor.grid_remove()

    def opcoes_completas() -> list[tuple[str, bool]]:
        # une motores locais (ocr) e de API (ia) num único combo — opcoes_motor
        # continua igual, só é chamada duas vezes e o resultado é mesclado.
        return opcoes_motor("ocr", cfg) + opcoes_motor("ia", cfg)

    def atualizar_motores(*_a) -> None:
        opts = opcoes_completas()
        habilitados = [m for m, ok in opts if ok]
        # só mostra o que dá pra usar; se nada tem chave, mostra todos (o Rodar avisa)
        cb_motor.configure(values=habilitados or [m for m, _ in opts])
        if motor_var.get() not in habilitados and habilitados:
            motor_var.set(habilitados[0])
        # fallback só pode ser um motor DIFERENTE do principal (e que dá pra usar).
        # Sem nenhum (ex.: só rapidocr, sem tesseract no PATH nem chave de API) ->
        # desabilita o checkbox pra não sobrar um combo vazio.
        outros = [m for m in habilitados if m != motor_var.get()]
        cb_fb_motor.configure(values=outros)
        if fb_motor_which.get() not in outros:
            fb_motor_which.set(outros[0] if outros else "")
        if outros:
            chk_fb_motor.configure(state="normal")
        else:
            fb_motor_var.set(False)
            chk_fb_motor.configure(state="disabled")
        atualizar_visibilidade_fallback()

    def ao_trocar_tipo(*_a) -> None:
        t = tipos[tipo_var.get()]
        motor_var.set(t.motor)
        fallback_var.set(t.modo != "ocr")
        atualizar_motores()

    tipo_var.trace_add("write", ao_trocar_tipo)
    motor_var.trace_add("write", atualizar_motores)
    fb_motor_var.trace_add("write", atualizar_visibilidade_fallback)
    atualizar_motores()

    ctk.CTkLabel(frm, text="Sequência esperada").grid(row=6, column=0, sticky="w", pady=4)
    ctk.CTkEntry(frm, textvariable=seq_var).grid(row=6, column=1, columnspan=2, sticky="we", padx=6)
    ctk.CTkLabel(frm, text="Intervalo máximo").grid(row=7, column=0, sticky="w", pady=4)
    ctk.CTkEntry(frm, textvariable=int_var).grid(row=7, column=1, columnspan=2, sticky="we", padx=6)

    def configurar_chaves() -> None:
        d = ctk.CTkToplevel(root)
        d.title("Chaves")
        d.geometry("400x180")
        o = tk.StringVar(value=cfg.chave_openai or "")
        m = tk.StringVar(value=cfg.chave_mistral or "")
        ctk.CTkLabel(d, text="OpenAI").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(d, textvariable=o, show="*", width=220).grid(row=0, column=1, padx=10, pady=10)
        ctk.CTkLabel(d, text="Mistral").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(d, textvariable=m, show="*", width=220).grid(row=1, column=1, padx=10, pady=10)

        def salvar_() -> None:
            cfg.chave_openai = o.get().strip() or None
            cfg.chave_mistral = m.get().strip() or None
            cfgmod.salvar(cfg)
            atualizar_motores()
            d.destroy()

        ctk.CTkButton(d, text="Salvar", command=salvar_).grid(row=2, column=0, columnspan=2, pady=10)

    def _atualizar_soma_btn() -> None:
        if cfg.soma_token:
            soma_btn.configure(text=f"Soma: {cfg.soma_email or 'conectado'}  ✕", command=sair_soma)
        else:
            soma_btn.configure(text="Entrar na Soma…", command=entrar_soma)

    def sair_soma() -> None:
        cfg.soma_email = cfg.soma_token = cfg.soma_refresh = None
        cfgmod.salvar(cfg)
        _atualizar_soma_btn()
        atualizar_motores()

    def entrar_soma() -> None:
        d = ctk.CTkToplevel(root)
        d.title("Entrar na Soma")
        d.geometry("380x210")
        d.transient(root)
        email = tk.StringVar(value=cfg.soma_email or "")
        senha = tk.StringVar()
        erro = ctk.CTkLabel(d, text="", text_color="#e06c75")
        ctk.CTkLabel(d, text="Mesmo login do site da Soma").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 4), sticky="w"
        )
        ctk.CTkLabel(d, text="E-mail").grid(row=1, column=0, padx=12, pady=6, sticky="w")
        ent_e = ctk.CTkEntry(d, textvariable=email, width=210)
        ent_e.grid(row=1, column=1, padx=12, pady=6)
        ctk.CTkLabel(d, text="Senha").grid(row=2, column=0, padx=12, pady=6, sticky="w")
        ctk.CTkEntry(d, textvariable=senha, show="*", width=210).grid(row=2, column=1, padx=12, pady=6)
        erro.grid(row=3, column=0, columnspan=2, padx=12)

        def entrar_() -> None:
            try:
                sessao = soma.login(email.get().strip(), senha.get())
            except Exception as e:  # noqa: BLE001
                erro.configure(text=str(e)[:120])
                return
            cfg.soma_email = sessao["email"]
            cfg.soma_token = sessao["access_token"]
            cfg.soma_refresh = sessao["refresh_token"]
            cfgmod.salvar(cfg)
            _atualizar_soma_btn()
            atualizar_motores()
            motor_var.set("soma")  # logou = quer usar a Soma
            d.destroy()

        ctk.CTkButton(d, text="Entrar", command=entrar_).grid(
            row=4, column=0, columnspan=2, pady=12
        )
        ent_e.focus_set()

    cfg_row = ctk.CTkFrame(frm, fg_color="transparent")
    cfg_row.grid(row=8, column=0, columnspan=3, pady=(8, 0))
    ctk.CTkButton(cfg_row, text="Configurar chaves…", command=configurar_chaves, width=175).pack(
        side="left", padx=4
    )
    soma_btn = ctk.CTkButton(cfg_row, text="Entrar na Soma…", command=entrar_soma, width=175)
    soma_btn.pack(side="left", padx=4)
    _atualizar_soma_btn()

    barra = ctk.CTkProgressBar(frm)
    barra.set(0)
    barra.grid(row=9, column=0, columnspan=3, sticky="we", pady=8)
    status = ctk.CTkLabel(frm, text="")
    status.grid(row=10, column=0, columnspan=3)
    btn = ctk.CTkButton(frm, text="Rodar")
    btn.grid(row=11, column=0, columnspan=3, pady=(0, 8))

    # --- resultados: nada fica visível na janela principal durante/após a
    # rodada -- só a contagem em `status`. A tabela de verdade só aparece
    # (janela separada) quando o usuário pede pra exportar, não antes.
    def _mostrar_resultados(linhas: list[LinhaResultado]) -> None:
        janela = ctk.CTkToplevel(root)
        janela.title("Resultados")
        janela.geometry("900x460")
        janela.transient(root)

        _estilizar_treeview_escuro()
        colunas = ("arquivo", "lido", "confianca", "motor", "status")
        titulos = {
            "arquivo": "Arquivo",
            "lido": "Lido",
            "confianca": "Confiança",
            "motor": "Motor",
            "status": "Status",
        }
        tree = ttk.Treeview(janela, columns=colunas, show="headings")
        for c in colunas:
            tree.heading(c, text=titulos[c])
            tree.column(c, width=150, anchor="w")
        vsb = ttk.Scrollbar(janela, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        vsb.pack(side="left", fill="y", pady=12, padx=(0, 12))

        for linha in linhas:
            conf = "" if linha.confianca is None else f"{linha.confianca:.3f}"
            tree.insert(
                "", "end", values=(linha.arquivo, linha.texto_lido, conf, linha.motor, linha.status)
            )

    def _exportar_csv_click() -> None:
        if not ultimas_linhas:
            return
        caminho = filedialog.asksaveasfilename(
            title="Exportar CSV",
            defaultextension=".csv",
            initialfile="resultado.csv",
            filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        exportar_csv(ultimas_linhas, Path(caminho))
        _mostrar_resultados(ultimas_linhas)

    btn_exportar = ctk.CTkButton(
        frm, text="Exportar CSV…", command=_exportar_csv_click, state="disabled"
    )
    btn_exportar.grid(row=12, column=0, columnspan=3, pady=(0, 4))

    def progresso(feitos: int, total: int) -> None:
        frac = 0.0 if total == 0 else feitos / total
        root.after(0, lambda: (barra.set(frac), status.configure(text=f"{feitos} de {total}")))

    def _erro_fatal(msg: str) -> None:
        status.configure(text="Falhou")
        messagebox.showerror("leitor-lote", f"A rodada falhou:\n{msg}")
        btn.configure(text="Rodar", command=executar, state="normal")

    def _abrir(p: Path) -> None:
        import os

        os.startfile(p)  # Windows

    def executar() -> None:
        pasta = pasta_var.get()
        if not pasta or not Path(pasta).is_dir():
            messagebox.showerror("leitor-lote", "Escolha uma pasta válida.")
            return
        cancel.clear()
        saida = Path(pasta) / "saida"
        saida.mkdir(parents=True, exist_ok=True)
        p = montar_parametros(
            pasta, tipo_var.get(), motor_var.get(), modo_efetivo(),
            seq_var.get(), int_var.get(),
            fb_motor_which.get() if fb_motor_var.get() else None,
        )
        cfg.ultima_pasta = pasta
        cfgmod.salvar(cfg)
        btn.configure(text="Cancelar", command=cancel.set)  # segue habilitado durante a rodada
        btn_exportar.configure(state="disabled")

        # renomeia cada arquivo assim que a leitura DELE termina, não só no
        # final -- se cancelar no meio, o que já terminou já está renomeado
        # na pasta de saída (ver output.copiar_um / pipeline.rodar).
        usados: dict[str, int] = {}
        renomeados = {"n": 0}

        def ao_completar(linha: LinhaResultado) -> None:
            copiar_um(linha, Path(pasta), saida, usados)
            if linha.erro != "cancelado":
                renomeados["n"] += 1

        def _fim(linhas: list[LinhaResultado]) -> None:
            ok = sum(1 for x in linhas if x.status == "ok")
            nr = sum(1 for x in linhas if x.status == "nao_reconhecido")
            er = sum(1 for x in linhas if x.status == "erro")
            status.configure(text=f"Concluído — {ok} ok, {nr} não reconhecidos, {er} erros")
            btn.configure(text="Abrir pasta de saída", command=lambda: _abrir(saida), state="normal")
            btn_exportar.configure(state="normal")

        def _cancelado(linhas: list[LinhaResultado]) -> None:
            status.configure(text=f"Cancelado — {renomeados['n']} já renomeados antes de parar")
            btn.configure(text="Rodar", command=executar, state="normal")
            btn_exportar.configure(state="normal" if linhas else "disabled")

        def trabalho() -> None:
            try:
                linhas = rodar(p, cfg, tipos, progresso, cancel, ao_completar=ao_completar)
                ultimas_linhas.clear()
                ultimas_linhas.extend(linhas)
                if cancel.is_set():
                    root.after(0, lambda: _cancelado(linhas))
                    return
                root.after(0, lambda: _fim(linhas))
            except Exception as e:  # noqa: BLE001
                root.after(0, lambda err=e: _erro_fatal(str(err)))

        threading.Thread(target=trabalho, daemon=True).start()

    btn.configure(command=executar)
    root.mainloop()
