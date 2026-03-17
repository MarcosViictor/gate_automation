from __future__ import annotations
import customtkinter as ctk
from datetime import datetime

from models.database import Database
from models.access_log import AccessLogRepository


class AccessLogView(ctk.CTkFrame):
    """
    Exibe o histórico de acessos (autorizados e negados) em lista rolável.
    Os dados são lidos diretamente do banco local.
    """

    def __init__(self, parent):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._db: Database | None = None
        self._repo: AccessLogRepository | None = None
        self._build_ui()

    def set_database(self, db: Database):
        """Injeta o banco de dados (chamado pelo main.py após inicialização)."""
        self._db = db
        self._repo = AccessLogRepository(db)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Log de Acessos",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="Atualizar", width=110,
            command=self.on_show,
        ).grid(row=0, column=1, sticky="e")

        # Tabela (header fixo)
        self._build_table_header()

        # Área rolável de linhas
        self._rows_frame = ctk.CTkScrollableFrame(self)
        self._rows_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 20))
        self._rows_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Rodapé com contador
        self._count_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color="gray50"
        )
        self._count_label.grid(row=3, column=0, sticky="e", padx=30, pady=(0, 10))

    def _build_table_header(self):
        cols = ctk.CTkFrame(self, corner_radius=8, fg_color=("gray80", "gray25"))
        cols.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 2))
        cols.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        headers = ["Data / Hora", "Tag", "Motorista", "Resultado", "Modo"]
        for i, text in enumerate(headers):
            ctk.CTkLabel(
                cols, text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="gray60",
            ).grid(row=0, column=i, padx=8, pady=8, sticky="w")

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def on_show(self):
        """Recarrega os dados ao exibir a view."""
        for widget in self._rows_frame.winfo_children():
            widget.destroy()

        if self._repo is None:
            self._show_empty("Banco de dados não inicializado.")
            return

        logs = self._repo.find_recent(limit=100)
        if not logs:
            self._show_empty("Nenhum registro encontrado.")
            return

        for idx, log in enumerate(logs):
            driver_name = getattr(log, "_driver_name", None) or "—"
            row_color = ("gray90", "gray18") if idx % 2 == 0 else ("gray85", "gray15")

            row_frame = ctk.CTkFrame(self._rows_frame, fg_color=row_color, corner_radius=6)
            row_frame.grid(row=idx, column=0, sticky="ew", pady=2)
            row_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

            values = [
                log.timestamp or "—",
                log.tag_code,
                driver_name,
                "AUTORIZADO" if log.authorized else "NEGADO",
                log.mode.upper(),
            ]
            colors = [None, None, None,
                      "#2ecc71" if log.authorized else "#e74c3c", None]

            for col, (val, color) in enumerate(zip(values, colors)):
                ctk.CTkLabel(
                    row_frame, text=val,
                    font=ctk.CTkFont(size=12),
                    text_color=color or ("gray10", "gray90"),
                ).grid(row=0, column=col, padx=8, pady=6, sticky="w")

        total = self._repo.count_today()
        self._count_label.configure(text=f"{len(logs)} registros exibidos · {total} hoje")

    def _show_empty(self, message: str):
        ctk.CTkLabel(
            self._rows_frame, text=message,
            text_color="gray50", font=ctk.CTkFont(size=14),
        ).grid(row=0, column=0, pady=40)
