from __future__ import annotations
import customtkinter as ctk
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from controllers.auth_controller import AuthController, AuthResult
    from commands.rfid_reader import RFIDReader
    from commands.gate_controller import GateController


class GateMonitorView(ctk.CTkFrame):
    """
    Tela principal – exibida em tempo real na frente do portão.

    Layout:
    ┌──────────────────────────────────────────┐
    │   STATUS DO PORTÃO  [FECHADO / ABERTO]   │
    ├───────────────────┬──────────────────────┤
    │   Última leitura  │   Resultado          │
    │   Tag / Motorista │   AUTORIZADO / NEGADO│
    ├───────────────────┴──────────────────────┤
    │   Botão "Simular tag" (modo mock)        │
    └──────────────────────────────────────────┘
    """

    _GATE_CLOSED_COLOR = "#e74c3c"
    _GATE_OPEN_COLOR = "#2ecc71"
    _AUTH_COLOR = "#2ecc71"
    _DENY_COLOR = "#e74c3c"

    def __init__(
        self,
        parent,
        auth_controller: "AuthController",
        gate_controller: "GateController",
        rfid_reader: "RFIDReader",
    ):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._auth = auth_controller
        self._gate = gate_controller
        self._rfid = rfid_reader

        self._gate_open = False

        self._build_ui()

        # Registra callback para quando o leitor detectar uma tag
        self._rfid._on_tag = self._on_tag_read

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Título da tela ---
        ctk.CTkLabel(
            self, text="Monitor do Portão",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=30, pady=(20, 10))

        # --- Painel central ---
        center = ctk.CTkFrame(self)
        center.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        center.grid_columnconfigure((0, 1), weight=1)
        center.grid_rowconfigure(0, weight=1)

        # Card: Status do portão
        self._build_gate_card(center)

        # Card: Última leitura
        self._build_reading_card(center)

        # --- Rodapé: modo mock ---
        self._build_footer()

    def _build_gate_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=16)
        card.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        card.grid_rowconfigure((0, 1, 2), weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="STATUS DO PORTÃO",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray60",
        ).grid(row=0, column=0, pady=(20, 0))

        self._gate_status_label = ctk.CTkLabel(
            card, text="FECHADO",
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color=self._GATE_CLOSED_COLOR,
        )
        self._gate_status_label.grid(row=1, column=0)

        self._gate_time_label = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        )
        self._gate_time_label.grid(row=2, column=0, pady=(0, 20))

    def _build_reading_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=16)
        card.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        card.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="ÚLTIMA LEITURA",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray60",
        ).grid(row=0, column=0, pady=(20, 0))

        self._result_label = ctk.CTkLabel(
            card, text="—",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="gray50",
        )
        self._result_label.grid(row=1, column=0)

        self._tag_label = ctk.CTkLabel(
            card, text="Aguardando tag...",
            font=ctk.CTkFont(size=13),
            text_color="gray60",
        )
        self._tag_label.grid(row=2, column=0)

        self._driver_label = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self._driver_label.grid(row=3, column=0)

        self._reason_label = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        )
        self._reason_label.grid(row=4, column=0, pady=(0, 20))

    def _build_footer(self):
        import config as cfg
        if not cfg.MOCK_HARDWARE:
            return

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 20))

        ctk.CTkLabel(
            footer, text="Modo desenvolvimento – simule uma leitura:",
            font=ctk.CTkFont(size=12), text_color="gray50",
        ).pack(side="left", padx=(0, 10))

        self._mock_entry = ctk.CTkEntry(footer, placeholder_text="Código da tag", width=160)
        self._mock_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            footer, text="Simular Leitura", width=140,
            command=self._simulate_tag,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------
    def _simulate_tag(self):
        tag_code = self._mock_entry.get().strip()
        if tag_code:
            self._rfid.simulate(tag_code)
            self._mock_entry.delete(0, "end")

    def _on_tag_read(self, tag_code: str):
        """Chamado pela thread do leitor RFID – delega para a thread da UI."""
        self.after(0, lambda: self._process_tag(tag_code))

    def _process_tag(self, tag_code: str):
        result = self._auth.process(tag_code)
        self._update_reading_card(result)

        if result.authorized:
            self._show_gate_open()
            self._gate.open()

    # ------------------------------------------------------------------
    # Atualização dos widgets
    # ------------------------------------------------------------------
    def _update_reading_card(self, result: "AuthResult"):
        if result.authorized:
            self._result_label.configure(text="AUTORIZADO", text_color=self._AUTH_COLOR)
            self._driver_label.configure(text=result.driver_name or "")
        else:
            self._result_label.configure(text="NEGADO", text_color=self._DENY_COLOR)
            self._driver_label.configure(text="")

        self._tag_label.configure(text=f"Tag: {result.tag_code}")
        self._reason_label.configure(text=result.reason or "")

    def _show_gate_open(self):
        import config as cfg
        self._gate_open = True
        self._gate_status_label.configure(text="ABERTO", text_color=self._GATE_OPEN_COLOR)
        self._gate_time_label.configure(
            text=f"Aberto às {datetime.now().strftime('%H:%M:%S')}"
        )
        # Fecha visualmente após o tempo configurado
        self.after(cfg.GATE_OPEN_DURATION * 1000, self._show_gate_closed)

    def _show_gate_closed(self):
        self._gate_open = False
        self._gate_status_label.configure(text="FECHADO", text_color=self._GATE_CLOSED_COLOR)
        self._gate_time_label.configure(
            text=f"Fechado às {datetime.now().strftime('%H:%M:%S')}"
        )
