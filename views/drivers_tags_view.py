from __future__ import annotations
import customtkinter as ctk

from models.database import Database
from models.driver import DriverRepository
from models.tag import TagRepository


class DriversTagsView(ctk.CTkFrame):
    """
    Tela de consulta de Motoristas e Tags.

    Layout:
    ┌──────────────────────┬─────────────────────────┐
    │  Lista de motoristas │  Tags do motorista       │
    │  (clique p/ ver tags)│  selecionado             │
    └──────────────────────┴─────────────────────────┘

    Obs.: cadastro e edição são feitos no sistema principal (servidor).
    Aqui é exibido apenas o espelho do backup local.
    """

    def __init__(self, parent):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._db: Database | None = None
        self._driver_repo: DriverRepository | None = None
        self._tag_repo: TagRepository | None = None
        self._selected_driver_id: int | None = None
        self._build_ui()

    def set_database(self, db: Database):
        self._db = db
        self._driver_repo = DriverRepository(db)
        self._tag_repo = TagRepository(db)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=30, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Motoristas & Tags",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="Atualizar", width=110,
            command=self.on_show,
        ).grid(row=0, column=1, sticky="e")

        # Painel esquerdo – lista de motoristas
        self._build_drivers_panel()

        # Painel direito – tags do motorista selecionado
        self._build_tags_panel()

    def _build_drivers_panel(self):
        panel = ctk.CTkFrame(self, corner_radius=12)
        panel.grid(row=1, column=0, sticky="nsew", padx=(30, 8), pady=(0, 20))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Motoristas",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="gray60",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        ctk.CTkFrame(panel, height=1, fg_color="gray30").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(40, 0)
        )

        self._drivers_list = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self._drivers_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._drivers_list.grid_columnconfigure(0, weight=1)

        self._drivers_count = ctk.CTkLabel(
            panel, text="", font=ctk.CTkFont(size=11), text_color="gray50"
        )
        self._drivers_count.grid(row=2, column=0, sticky="e", padx=16, pady=(0, 10))

    def _build_tags_panel(self):
        panel = ctk.CTkFrame(self, corner_radius=12)
        panel.grid(row=1, column=1, sticky="nsew", padx=(8, 30), pady=(0, 20))
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        self._tags_title = ctk.CTkLabel(
            panel,
            text="Tags",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="gray60",
        )
        self._tags_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        ctk.CTkFrame(panel, height=1, fg_color="gray30").grid(
            row=1, column=0, sticky="ew", padx=16
        )

        self._tags_list = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self._tags_list.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self._tags_list.grid_columnconfigure(0, weight=1)

        # Mensagem inicial
        ctk.CTkLabel(
            self._tags_list,
            text="Selecione um motorista para ver as tags.",
            text_color="gray50",
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=0, pady=30)

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def on_show(self):
        self._load_drivers()

    def _load_drivers(self):
        for widget in self._drivers_list.winfo_children():
            widget.destroy()

        if self._driver_repo is None:
            return

        drivers = self._driver_repo.find_all_active()

        if not drivers:
            ctk.CTkLabel(
                self._drivers_list,
                text="Nenhum motorista cadastrado.",
                text_color="gray50",
                font=ctk.CTkFont(size=13),
            ).grid(row=0, column=0, pady=30)
            self._drivers_count.configure(text="0 motoristas")
            return

        for idx, driver in enumerate(drivers):
            card = ctk.CTkFrame(
                self._drivers_list,
                corner_radius=8,
                fg_color=("gray88", "gray22"),
                cursor="hand2",
            )
            card.grid(row=idx, column=0, sticky="ew", pady=3)
            card.grid_columnconfigure(0, weight=1)

            name_lbl = ctk.CTkLabel(
                card,
                text=driver.name,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            )
            name_lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 2))

            info_parts = []
            if driver.cpf:
                info_parts.append(f"CPF: {driver.cpf}")
            if driver.phone:
                info_parts.append(driver.phone)
            if not driver.is_active:
                info_parts.append("INATIVO")

            if info_parts:
                ctk.CTkLabel(
                    card,
                    text="  ".join(info_parts),
                    font=ctk.CTkFont(size=11),
                    text_color="gray55",
                    anchor="w",
                ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

            # Bind clique em todo o card
            for widget in [card, name_lbl]:
                widget.bind("<Button-1>", lambda e, d=driver: self._select_driver(d))

        self._drivers_count.configure(text=f"{len(drivers)} motorista(s)")

    def _select_driver(self, driver):
        self._selected_driver_id = driver.id
        self._tags_title.configure(
            text=f"Tags — {driver.name}",
            text_color=("gray20", "gray90"),
        )
        self._load_tags(driver.id)

    def _load_tags(self, driver_id: int):
        for widget in self._tags_list.winfo_children():
            widget.destroy()

        if self._tag_repo is None:
            return

        tags = self._tag_repo.find_by_driver_id(driver_id)

        if not tags:
            ctk.CTkLabel(
                self._tags_list,
                text="Nenhuma tag vinculada a este motorista.",
                text_color="gray50",
                font=ctk.CTkFont(size=13),
            ).grid(row=0, column=0, pady=30)
            return

        # Cabeçalho da tabela
        header = ctk.CTkFrame(self._tags_list, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 2))
        header.grid_columnconfigure(0, weight=3)
        header.grid_columnconfigure(1, weight=1)

        for col, text in enumerate(["Código da Tag", "Status"]):
            ctk.CTkLabel(
                header, text=text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="gray55",
            ).grid(row=0, column=col, sticky="w", padx=8)

        for idx, tag in enumerate(tags):
            row_color = ("gray88", "gray22") if idx % 2 == 0 else ("gray83", "gray18")
            row = ctk.CTkFrame(self._tags_list, corner_radius=6, fg_color=row_color)
            row.grid(row=idx + 1, column=0, sticky="ew", pady=2, padx=4)
            row.grid_columnconfigure(0, weight=3)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row,
                text=tag.tag_code,
                font=ctk.CTkFont(size=13, family="monospace"),
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=12, pady=8)

            status_text = "Ativa" if tag.is_active else "Inativa"
            status_color = "#2ecc71" if tag.is_active else "#e74c3c"
            ctk.CTkLabel(
                row,
                text=status_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=status_color,
            ).grid(row=0, column=1, sticky="w", padx=8, pady=8)
