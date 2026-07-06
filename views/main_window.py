import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Callable

from controllers.auth_controller import AccessDecision


class MainWindow(tk.Tk):
    def __init__(
        self,
        on_save_config: Callable[[dict], None],
        on_mock_tag: Callable[[str, str], None],
        on_test_connection: Callable[[], tuple],
        initial_config: dict,
    ):
        super().__init__()
        self.on_save_config = on_save_config
        self.on_mock_tag = on_mock_tag
        self.on_test_connection = on_test_connection
        self.cfg = initial_config

        self.title("Gate Automation — Thin Client")
        self.geometry("640x460")

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Success.TLabel", font=("Segoe UI", 13, "bold"), foreground="#10b981")
        style.configure("Danger.TLabel", font=("Segoe UI", 13, "bold"), foreground="#ef4444")
        style.configure("Status.TLabel", font=("Segoe UI", 13, "bold"), foreground="#1e3a8a")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=12, pady=12)
        self._build_monitor_tab()
        self._build_config_tab()

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ------------------------------------------------------------------ Monitor
    def _build_monitor_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Monitor")

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=10, pady=10)
        self.lbl_gate = ttk.Label(top, text="PORTÃO FECHADO", style="Status.TLabel")
        self.lbl_gate.pack(side="left")
        ttk.Label(top, text="  |  ", style="Status.TLabel").pack(side="left")
        self.lbl_net = ttk.Label(top, text="● OFFLINE", style="Danger.TLabel")
        self.lbl_net.pack(side="left")

        cols = ("time", "tag", "dir", "status")
        self.tree = ttk.Treeview(tab, columns=cols, show="headings", height=10)
        for c, t, w in (("time", "Horário", 110), ("tag", "Tag", 240),
                        ("dir", "Direção", 70), ("status", "Resultado", 180)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center" if c == "dir" else "w")
        self.tree.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        sim = ttk.Frame(tab)
        sim.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(sim, text="Simular (ex: IN:0100... ou só o código):").pack(side="left", padx=(0, 8))
        self.ent_mock = ttk.Entry(sim, font=("Consolas", 10))
        self.ent_mock.pack(side="left", fill="x", expand=True, padx=5)
        self.ent_mock.bind("<Return>", lambda e: self._handle_mock())
        ttk.Button(sim, text="Ler Tag", command=self._handle_mock).pack(side="right", padx=5)

    def _handle_mock(self):
        val = self.ent_mock.get().strip()
        if not val:
            return
        if val.startswith("IN:"):
            self.on_mock_tag(val[3:], "IN")
        elif val.startswith("OUT:"):
            self.on_mock_tag(val[4:], "OUT")
        else:
            self.on_mock_tag(val, "IN")
        self.ent_mock.delete(0, tk.END)

    # ------------------------------------------------------------------ Config
    def _build_config_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Configurações")

        frame = ttk.Frame(tab)
        frame.pack(fill="both", padx=25, pady=25)

        ttk.Label(frame, text="Servidor local (sb-gatehouse)",
                  font=("Segoe UI", 13, "bold"), foreground="#1e3a8a").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self.ent_host = self._labeled_entry(frame, "IP do servidor:", 1, self.cfg["server_host"])
        self.ent_port = self._labeled_entry(frame, "Porta:", 2, self.cfg["server_port"])
        self.ent_in = self._labeled_entry(frame, "Leitor Entrada (IN):", 3, self.cfg["rfid_port_in"])
        self.ent_out = self._labeled_entry(frame, "Leitor Saída (OUT):", 4, self.cfg["rfid_port_out"])

        btns = ttk.Frame(frame)
        btns.grid(row=5, column=1, sticky="e", pady=(18, 0))
        ttk.Button(btns, text="Testar conexão", command=self._test_connection).pack(side="left", padx=6)
        ttk.Button(btns, text="✓ Salvar", command=self._save_config).pack(side="left")

    def _labeled_entry(self, parent, label, row, value):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8)
        ent = ttk.Entry(parent, width=32, font=("Consolas", 10))
        ent.insert(0, value or "")
        ent.grid(row=row, column=1, padx=12, pady=8)
        return ent

    def _collect_config(self) -> dict:
        return {
            "server_host": self.ent_host.get().strip(),
            "server_port": self.ent_port.get().strip(),
            "rfid_port_in": self.ent_in.get().strip(),
            "rfid_port_out": self.ent_out.get().strip(),
        }

    def _save_config(self):
        self.cfg = self._collect_config()
        self.on_save_config(self.cfg)
        messagebox.showinfo("Configurações", "Salvo no .env e leitores reiniciados.")

    def _test_connection(self):
        # Salva antes de testar, para usar o IP/porta digitados.
        self.on_save_config(self._collect_config())
        ok, msg = self.on_test_connection()
        if ok:
            messagebox.showinfo("Testar conexão", msg)
        else:
            messagebox.showerror("Testar conexão", msg)

    # ------------------------------------------------------------------ Updates
    @staticmethod
    def format_status(decision: AccessDecision) -> str:
        if decision.authorized:
            return "AUTORIZADO"
        return f"NEGADO ({decision.reason})" if decision.reason else "NEGADO"

    def add_read_row(self, decision: AccessDecision):
        self.tree.insert(
            "", 0,
            values=(datetime.now().strftime("%H:%M:%S"), decision.tag_code,
                    decision.direction, self.format_status(decision)),
        )
        children = self.tree.get_children()
        for extra in children[15:]:
            self.tree.delete(extra)

    def update_gate_status(self, is_open: bool):
        self.lbl_gate.config(
            text="PORTÃO ABERTO" if is_open else "PORTÃO FECHADO",
            style="Success.TLabel" if is_open else "Status.TLabel",
        )

    def update_net_status(self, is_online: bool):
        self.lbl_net.config(
            text="● ONLINE" if is_online else "● OFFLINE",
            style="Success.TLabel" if is_online else "Danger.TLabel",
        )
