from __future__ import annotations
import customtkinter as ctk
from typing import TYPE_CHECKING

from views.gate_monitor_view import GateMonitorView
from views.access_log_view import AccessLogView
from views.status_view import StatusView
from views.drivers_tags_view import DriversTagsView
from views.schedules_view import SchedulesView
import config

if TYPE_CHECKING:
    from controllers.auth_controller import AuthController
    from controllers.sync_controller import SyncController
    from commands.rfid_reader import RFIDReader
    from commands.gate_controller import GateController


class MainWindow(ctk.CTk):
    """
    Janela principal da aplicação.

    Estrutura:
    ┌──────────────┬──────────────────────────────┐
    │   Sidebar    │        Área de conteúdo       │
    │  (navegação) │     (views intercambiáveis)   │
    └──────────────┴──────────────────────────────┘
    """

    def __init__(
        self,
        auth_controller: "AuthController",
        sync_controller: "SyncController",
        rfid_reader: "RFIDReader",
        gate_controller: "GateController",
    ):
        super().__init__()

        self._auth = auth_controller
        self._sync = sync_controller
        self._rfid = rfid_reader
        self._gate = gate_controller

        self._configure_window()
        self._build_sidebar()
        self._build_content_area()
        self._show_view("monitor")

    # ------------------------------------------------------------------
    # Configuração da janela
    # ------------------------------------------------------------------
    def _configure_window(self):
        self.title(config.APP_TITLE)
        self.geometry(config.APP_GEOMETRY)
        self.resizable(True, True)
        ctk.set_appearance_mode(config.THEME)
        ctk.set_default_color_theme(config.COLOR_SCHEME)

        # Permite fechar com limpeza de recursos
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def _build_sidebar(self):
        self._sidebar = ctk.CTkFrame(self, width=180, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Logo / título
        ctk.CTkLabel(
            self._sidebar,
            text="Gate\nAutomation",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(30, 20), padx=20)

        ctk.CTkFrame(self._sidebar, height=2, fg_color="gray30").pack(
            fill="x", padx=15, pady=(0, 15)
        )

        # Botões de navegação
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("monitor", "  Monitor"),
            ("logs", "  Acessos"),
            ("drivers", "  Motoristas"),
            ("schedules", "  Agendamentos"),
            ("status", "  Sistema"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self._sidebar,
                text=label,
                anchor="w",
                height=40,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda k=key: self._show_view(k),
            )
            btn.pack(fill="x", padx=10, pady=4)
            self._nav_buttons[key] = btn

        # Indicador de status de conexão (canto inferior da sidebar)
        self._sidebar.pack_propagate(False)
        self._conn_label = ctk.CTkLabel(
            self._sidebar,
            text="● OFFLINE",
            font=ctk.CTkFont(size=12),
            text_color="#e74c3c",
        )
        self._conn_label.pack(side="bottom", pady=20)

    # ------------------------------------------------------------------
    # Área de conteúdo
    # ------------------------------------------------------------------
    def _build_content_area(self):
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.pack(side="right", fill="both", expand=True)

        # Instancia as cinco views
        self._views: dict[str, ctk.CTkFrame] = {
            "monitor": GateMonitorView(
                self._content,
                auth_controller=self._auth,
                gate_controller=self._gate,
                rfid_reader=self._rfid,
            ),
            "logs": AccessLogView(self._content),
            "drivers": DriversTagsView(self._content),
            "schedules": SchedulesView(self._content),
            "status": StatusView(self._content, sync_controller=self._sync),
        }

        for view in self._views.values():
            view.place(relx=0, rely=0, relwidth=1, relheight=1)

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    def _show_view(self, key: str):
        # Destaca o botão ativo
        for k, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=("gray75", "gray30") if k == key else "transparent"
            )

        view = self._views.get(key)
        if view:
            view.lift()
            if hasattr(view, "on_show"):
                view.on_show()

    # ------------------------------------------------------------------
    # Atualiza indicador de conexão (chamado pelo SyncController)
    # ------------------------------------------------------------------
    def update_connection_status(self, is_online: bool):
        if is_online:
            self._conn_label.configure(text="● ONLINE", text_color="#2ecc71")
        else:
            self._conn_label.configure(text="● OFFLINE", text_color="#e74c3c")

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------
    def _on_close(self):
        self._rfid.stop()
        self._sync.stop()
        self._gate.cleanup()
        self.destroy()
