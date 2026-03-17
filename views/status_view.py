from __future__ import annotations
import customtkinter as ctk
from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from controllers.sync_controller import SyncController


class StatusView(ctk.CTkFrame):
    """
    Exibe informações sobre o estado do sistema:
    - Conexão com o servidor
    - Último horário de sincronização
    - Totais do banco local (tags, motoristas, agendamentos hoje)
    - Configurações de hardware
    """

    def __init__(self, parent, sync_controller: "SyncController"):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._sync = sync_controller
        self._db = None
        self._build_ui()

    def set_database(self, db):
        self._db = db

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="Status do Sistema",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=30, pady=(20, 10))

        # Card: Conexão
        self._conn_card = self._make_card("Conexão com Servidor")
        self._conn_card.grid(row=1, column=0, sticky="nsew", padx=(30, 10), pady=10)
        self._conn_status_lbl = self._add_metric(self._conn_card, "Status", "—")
        self._conn_sync_lbl = self._add_metric(self._conn_card, "Último sync", "—")
        self._add_sync_button(self._conn_card)

        # Card: Banco local
        self._db_card = self._make_card("Banco de Dados Local")
        self._db_card.grid(row=1, column=1, sticky="nsew", padx=(10, 30), pady=10)
        self._db_tags_lbl = self._add_metric(self._db_card, "Tags ativas", "—")
        self._db_drivers_lbl = self._add_metric(self._db_card, "Motoristas ativos", "—")
        self._db_schedules_lbl = self._add_metric(self._db_card, "Agendamentos hoje", "—")

        # Card: Hardware
        hw_card = self._make_card("Hardware")
        hw_card.grid(row=2, column=0, columnspan=2, sticky="ew", padx=30, pady=(0, 20))
        self._add_metric(hw_card, "Modo",
                         "DESENVOLVIMENTO (mock)" if config.MOCK_HARDWARE else "PRODUÇÃO")
        self._add_metric(hw_card, "Porta RFID", config.RFID_PORT)
        self._add_metric(hw_card, "Pino GPIO do relé", str(config.GATE_RELAY_PIN))
        self._add_metric(hw_card, "Servidor", config.SERVER_BASE_URL)

    # ------------------------------------------------------------------
    # Helpers de construção
    # ------------------------------------------------------------------
    def _make_card(self, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self, corner_radius=16)
        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray60",
        ).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkFrame(card, height=1, fg_color="gray30").pack(fill="x", padx=20)
        return card

    def _add_metric(
        self, card: ctk.CTkFrame, label: str, value: str
    ) -> ctk.CTkLabel:
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(row, text=label + ":", text_color="gray60",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        val_lbl = ctk.CTkLabel(row, text=value, font=ctk.CTkFont(size=13, weight="bold"))
        val_lbl.pack(side="right")
        return val_lbl

    def _add_sync_button(self, card: ctk.CTkFrame):
        ctk.CTkButton(
            card, text="Sincronizar agora", width=160,
            command=self._force_sync,
        ).pack(anchor="w", padx=20, pady=(8, 16))

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def on_show(self):
        self._refresh_connection()
        self._refresh_db_stats()

    def _refresh_connection(self):
        online = self._sync.is_online
        self._conn_status_lbl.configure(
            text="ONLINE" if online else "OFFLINE",
            text_color="#2ecc71" if online else "#e74c3c",
        )
        self._conn_sync_lbl.configure(text=self._sync.last_sync or "Nunca")

    def _refresh_db_stats(self):
        if self._db is None:
            return
        from models.tag import TagRepository
        from models.driver import DriverRepository
        from models.schedule import ScheduleRepository

        self._db_tags_lbl.configure(text=str(TagRepository(self._db).count()))
        self._db_drivers_lbl.configure(text=str(DriverRepository(self._db).count()))
        self._db_schedules_lbl.configure(text=str(ScheduleRepository(self._db).count_today()))

    def _force_sync(self):
        self._conn_status_lbl.configure(text="Sincronizando...", text_color="gray60")
        self.after(100, self._do_sync)

    def _do_sync(self):
        self._sync.sync_now()
        self._refresh_connection()
        self._refresh_db_stats()
