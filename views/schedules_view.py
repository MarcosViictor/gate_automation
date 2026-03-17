from __future__ import annotations
import customtkinter as ctk
from datetime import date

from models.database import Database
from models.schedule import ScheduleRepository


class SchedulesView(ctk.CTkFrame):
    """
    Tela de consulta de agendamentos registrados no banco local.

    Exibe todos os agendamentos com filtro por data.
    O agendamento do dia atual é destacado.
    """

    _ACTIVE_COLOR = "#2ecc71"
    _INACTIVE_COLOR = "#e74c3c"
    _TODAY_ROW = ("##e8f8f0", "#1a3a2a")  # destaque para agendamentos de hoje

    def __init__(self, parent):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._db: Database | None = None
        self._repo: ScheduleRepository | None = None
        self._filter_date: str = date.today().isoformat()
        self._build_ui()

    def set_database(self, db: Database):
        self._db = db
        self._repo = ScheduleRepository(db)

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
            text="Agendamentos",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="Atualizar", width=110,
            command=self.on_show,
        ).grid(row=0, column=1, sticky="e")

        # Barra de filtros
        self._build_filter_bar()

        # Tabela
        self._build_table_header()

        # Área rolável de linhas
        self._rows_frame = ctk.CTkScrollableFrame(self)
        self._rows_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 10))
        self._rows_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Rodapé
        self._footer_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color="gray50"
        )
        self._footer_label.grid(row=3, column=0, sticky="e", padx=30, pady=(0, 12))

    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self, corner_radius=10)
        bar.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 10))

        ctk.CTkLabel(
            bar, text="Filtrar por data:",
            font=ctk.CTkFont(size=13), text_color="gray60",
        ).pack(side="left", padx=(16, 8), pady=10)

        self._date_entry = ctk.CTkEntry(
            bar,
            placeholder_text="AAAA-MM-DD",
            width=130,
        )
        self._date_entry.insert(0, self._filter_date)
        self._date_entry.pack(side="left", pady=10)

        ctk.CTkButton(
            bar, text="Filtrar", width=80,
            command=self._apply_filter,
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            bar, text="Hoje", width=70,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray80"),
            command=self._filter_today,
        ).pack(side="left", pady=10)

        # Contadores rápidos
        self._today_count_lbl = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=12), text_color="gray50",
        )
        self._today_count_lbl.pack(side="right", padx=16, pady=10)

    def _build_table_header(self):
        cols = ctk.CTkFrame(self, corner_radius=8, fg_color=("gray80", "gray25"))
        cols.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 0))
        cols.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        headers = ["Motorista", "Data", "Início", "Fim", "Status"]
        for i, text in enumerate(headers):
            ctk.CTkLabel(
                cols, text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray20", "gray80"),
            ).grid(row=0, column=i, padx=12, pady=8, sticky="w")

        # O scrollable frame precisa ficar na row=2 depois do header,
        # então reposicionamos abaixo via grid_rowconfigure
        cols.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 2))
        self._rows_frame = ctk.CTkScrollableFrame(self)
        self._rows_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 10))
        self._rows_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------
    def _apply_filter(self):
        raw = self._date_entry.get().strip()
        self._filter_date = raw if raw else date.today().isoformat()
        self._load_data()

    def _filter_today(self):
        today = date.today().isoformat()
        self._filter_date = today
        self._date_entry.delete(0, "end")
        self._date_entry.insert(0, today)
        self._load_data()

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def on_show(self):
        self._load_data()

    def _load_data(self):
        for widget in self._rows_frame.winfo_children():
            widget.destroy()

        if self._repo is None:
            self._show_empty("Banco de dados não inicializado.")
            return

        # Busca por data específica ou todos
        is_all = not self._filter_date
        if self._filter_date:
            schedules = self._repo.find_all_for_date(self._filter_date)
            # Adiciona driver_name via find_all para reaproveitarmos o JOIN
        else:
            schedules = []

        # Para ter o nome do motorista, usamos find_all e filtramos em Python
        all_schedules = self._repo.find_all(limit=500)
        if self._filter_date:
            schedules = [s for s in all_schedules if s.scheduled_date == self._filter_date]
        else:
            schedules = all_schedules

        if not schedules:
            self._show_empty(
                f"Nenhum agendamento para {self._filter_date}."
                if self._filter_date else "Nenhum agendamento cadastrado."
            )
            today_total = self._repo.count_today()
            self._update_footer(0, today_total)
            return

        today = date.today().isoformat()

        for idx, sched in enumerate(schedules):
            is_today = sched.scheduled_date == today
            if is_today:
                row_color = ("#d4f5e3", "#1e3d2f")
            elif idx % 2 == 0:
                row_color = ("gray90", "gray18")
            else:
                row_color = ("gray85", "gray15")

            row = ctk.CTkFrame(self._rows_frame, corner_radius=6, fg_color=row_color)
            row.grid(row=idx, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

            driver_name = getattr(sched, "_driver_name", "—")
            status_text = "Ativo" if sched.is_active else "Inativo"
            status_color = self._ACTIVE_COLOR if sched.is_active else self._INACTIVE_COLOR

            cells = [
                (driver_name, None, ctk.CTkFont(size=13, weight="bold")),
                (self._fmt_date(sched.scheduled_date), None, ctk.CTkFont(size=13)),
                (sched.time_start, None, ctk.CTkFont(size=13)),
                (sched.time_end, None, ctk.CTkFont(size=13)),
                (status_text, status_color, ctk.CTkFont(size=12, weight="bold")),
            ]

            for col, (val, color, font) in enumerate(cells):
                ctk.CTkLabel(
                    row, text=val,
                    font=font,
                    text_color=color or ("gray10", "gray90"),
                ).grid(row=0, column=col, padx=12, pady=8, sticky="w")

            # Badge "HOJE" na linha do dia atual
            if is_today:
                badge = ctk.CTkLabel(
                    row, text=" HOJE ",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="white",
                    fg_color="#27ae60",
                    corner_radius=4,
                )
                badge.grid(row=0, column=5, padx=(0, 12), pady=8, sticky="e")

        today_total = self._repo.count_today()
        self._update_footer(len(schedules), today_total)

    def _show_empty(self, message: str):
        ctk.CTkLabel(
            self._rows_frame, text=message,
            text_color="gray50", font=ctk.CTkFont(size=14),
        ).grid(row=0, column=0, pady=40, columnspan=5)

    def _update_footer(self, shown: int, today_total: int):
        self._footer_label.configure(
            text=f"{shown} agendamento(s) exibido(s) · {today_total} hoje"
        )
        self._today_count_lbl.configure(text=f"{today_total} agendamento(s) hoje")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _fmt_date(iso: str) -> str:
        """Converte 'YYYY-MM-DD' → 'DD/MM/YYYY'."""
        try:
            parts = iso.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            return iso
