import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from models.database import Database
from models.access_log import AccessLogRepository

class MainWindow(tk.Tk):
    def __init__(self, db: Database, on_sync: Callable, on_save_ports: Callable, on_mock_tag: Callable):
        super().__init__()
        self.db = db
        self.logs_repo = AccessLogRepository(db)
        self.on_sync = on_sync
        self.on_save_ports = on_save_ports
        self.on_mock_tag = on_mock_tag

        self.title("Gate Automation Monitor")
        self.geometry("650x500")
        self.configure(bg="#f4f6f8")
        
        # Usar o tema clam como base e estilizá-lo
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        # Configurações globais de estilo
        style.configure(".", font=("Segoe UI", 10), background="#f4f6f8", foreground="#333333")
        style.configure("TNotebook", background="#e9ecef", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[15, 5], background="#dee2e6")
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#0056b3")])
        
        style.configure("Card.TFrame", background="#ffffff", borderwidth=1, relief="solid", bordercolor="#dee2e6")
        
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#0d6efd", foreground="white", padding=6)
        style.map("Primary.TButton", background=[("active", "#0b5ed7")])
        
        style.configure("Success.TLabel", font=("Segoe UI", 14, "bold"), foreground="#198754", background="#ffffff")
        style.configure("Danger.TLabel", font=("Segoe UI", 14, "bold"), foreground="#dc3545", background="#ffffff")
        style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"), foreground="#6c757d", background="#ffffff")

        style.configure("Treeview", font=("Segoe UI", 10), rowheight=25, borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#f8f9fa", foreground="#495057")
        style.map("Treeview", background=[("selected", "#e7f1ff")], foreground=[("selected", "#0c63e4")])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both', padx=15, pady=15)

        self._build_monitor_tab()
        self._build_vehicles_tab()
        self._build_tags_tab()
        self._build_readers_tab()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_monitor_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Monitor")

        # Top Bar (Status and Sync) - Styled as a Card
        top_frame = ttk.Frame(tab, style="Card.TFrame")
        top_frame.pack(fill='x', padx=10, pady=10)

        inner_top = ttk.Frame(top_frame, style="Card.TFrame")
        inner_top.pack(fill='x', padx=15, pady=10)

        self.lbl_gate_status = ttk.Label(inner_top, text="PORTÃO FECHADO", style="Status.TLabel")
        self.lbl_gate_status.pack(side='left')

        # Separator
        ttk.Label(inner_top, text=" | ", style="Status.TLabel").pack(side='left', padx=10)

        self.lbl_net_status = ttk.Label(inner_top, text="● OFFLINE", style="Danger.TLabel")
        self.lbl_net_status.pack(side='left')

        btn_sync = ttk.Button(inner_top, text="⟳ Sincronizar Agora", style="Primary.TButton", command=self.on_sync)
        btn_sync.pack(side='right')

        # Treeview Container
        tree_frame = ttk.Frame(tab, style="Card.TFrame")
        tree_frame.pack(expand=True, fill='both', padx=10, pady=(0, 10))

        # Treeview para Logs
        columns = ("time", "tag", "vehicle", "portaria", "dir", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        self.tree.heading("time", text="Horário")
        self.tree.heading("tag", text="Tag")
        self.tree.heading("vehicle", text="Veículo")
        self.tree.heading("portaria", text="Portaria")
        self.tree.heading("dir", text="Direção")
        self.tree.heading("status", text="Status")
        
        self.tree.column("time", width=120)
        self.tree.column("tag", width=150)
        self.tree.column("vehicle", width=130)
        self.tree.column("portaria", width=65, anchor='center')
        self.tree.column("dir", width=65, anchor='center')
        self.tree.column("status", width=180)

        self.tree.pack(expand=True, fill='both', padx=2, pady=2)

        # Mock frame for testing directly from UI
        mock_frame = ttk.Frame(tab, style="Card.TFrame")
        mock_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        inner_mock = ttk.Frame(mock_frame, style="Card.TFrame")
        inner_mock.pack(fill='x', padx=10, pady=8)
        
        ttk.Label(inner_mock, text="Simulador (ex: IN:0100...):", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(side='left', padx=(0, 10))
        self.ent_mock = ttk.Entry(inner_mock, width=30, font=("Consolas", 10))
        self.ent_mock.pack(side='left', fill='x', expand=True, padx=5)
        self.ent_mock.bind('<Return>', lambda e: self._handle_mock())
        ttk.Button(inner_mock, text="Ler Tag", command=self._handle_mock).pack(side='right', padx=5)

        self.refresh_logs()

    def _handle_mock(self):
        val = self.ent_mock.get().strip()
        if val:
            if val.startswith("IN:"):
                self.on_mock_tag(val[3:], "IN")
            elif val.startswith("OUT:"):
                self.on_mock_tag(val[4:], "OUT")
            else:
                self.on_mock_tag(val, "IN")
            self.ent_mock.delete(0, tk.END)

    def _build_readers_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Leitores (Configuração)")

        frame = ttk.Frame(tab, style="Card.TFrame")
        frame.pack(fill='x', padx=15, pady=20)
        
        inner_config = ttk.Frame(frame, style="Card.TFrame")
        inner_config.pack(fill='both', padx=20, pady=20)

        ttk.Label(inner_config, text="Configuração das Portas Seriais", font=("Segoe UI", 14, "bold"), background="#ffffff", foreground="#0056b3").grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 15))

        port_in = self.db.get_setting("RFID_PORT_IN", "/dev/ttyUSB0")
        port_out = self.db.get_setting("RFID_PORT_OUT", "/dev/ttyUSB1")

        ttk.Label(inner_config, text="Leitor Entrada (IN):", background="#ffffff", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky='w', pady=10)
        self.ent_port_in = ttk.Entry(inner_config, width=35, font=("Consolas", 10))
        self.ent_port_in.insert(0, port_in)
        self.ent_port_in.grid(row=1, column=1, padx=15, pady=10)

        ttk.Label(inner_config, text="Leitor Saída (OUT):", background="#ffffff", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky='w', pady=10)
        self.ent_port_out = ttk.Entry(inner_config, width=35, font=("Consolas", 10))
        self.ent_port_out.insert(0, port_out)
        self.ent_port_out.grid(row=2, column=1, padx=15, pady=10)

        btn_save = ttk.Button(inner_config, text="✓ Salvar e Reiniciar Leitores", style="Primary.TButton", command=self._save_ports)
        btn_save.grid(row=3, column=1, sticky='e', pady=(20, 0))

    def _save_ports(self):
        port_in = self.ent_port_in.get().strip()
        port_out = self.ent_port_out.get().strip()
        self.db.set_setting("RFID_PORT_IN", port_in)
        self.db.set_setting("RFID_PORT_OUT", port_out)
        self.on_save_ports(port_in, port_out)
        messagebox.showinfo("Sucesso", "Portas salvas e leitores reiniciados com sucesso!")

    def refresh_logs(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        logs = self.logs_repo.find_recent(limit=15)
        for log in logs:
            sync_label = "Sincronizado" if log.synced else "Offline"
            status = f"{'AUTORIZADO' if log.authorized else f'NEGADO ({log.reason})'} ({sync_label})"
            vehicle_info = f"{log.vehicle_plate} ({log.vehicle_model})" if log.vehicle_plate else "-"
            portaria_info = str(log.portaria_id) if log.portaria_id is not None else "-"
            self.tree.insert("", "end", values=(
                log.timestamp,
                log.tag_code,
                vehicle_info,
                portaria_info,
                log.direction,
                status
            ))

    def update_gate_status(self, is_open: bool):
        if is_open:
            self.lbl_gate_status.config(text="PORTÃO ABERTO", style="Success.TLabel")
        else:
            self.lbl_gate_status.config(text="PORTÃO FECHADO", style="Status.TLabel")

    def update_net_status(self, is_online: bool):
        if is_online:
            self.lbl_net_status.config(text="● ONLINE", style="Success.TLabel")
        else:
            self.lbl_net_status.config(text="● OFFLINE", style="Danger.TLabel")

    def _build_vehicles_tab(self):
        from models.vehicle import VehicleRepository
        self.vehicle_repo = VehicleRepository(self.db)
        
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Veículos")

        frame = ttk.Frame(tab, style="Card.TFrame")
        frame.pack(expand=True, fill='both', padx=10, pady=10)

        columns = ("plate", "model", "portaria", "tag", "status")
        self.tree_vehicles = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree_vehicles.heading("plate", text="Placa")
        self.tree_vehicles.heading("model", text="Modelo")
        self.tree_vehicles.heading("portaria", text="Portaria ID")
        self.tree_vehicles.heading("tag", text="Tag Código")
        self.tree_vehicles.heading("status", text="Status")

        self.tree_vehicles.column("plate", width=100)
        self.tree_vehicles.column("model", width=150)
        self.tree_vehicles.column("portaria", width=100, anchor='center')
        self.tree_vehicles.column("tag", width=200)
        self.tree_vehicles.column("status", width=100, anchor='center')

        self.tree_vehicles.pack(expand=True, fill='both', padx=2, pady=2)
        
        btn_refresh = ttk.Button(tab, text="⟳ Atualizar Lista", command=self.refresh_vehicles)
        btn_refresh.pack(pady=5)

        self.refresh_vehicles()

    def refresh_vehicles(self):
        for item in self.tree_vehicles.get_children():
            self.tree_vehicles.delete(item)
        
        vehicles = self.vehicle_repo.find_all()
        for v in vehicles:
            status = "Ativo" if v.is_active else "Inativo"
            self.tree_vehicles.insert("", "end", values=(
                v.plate,
                v.model or "-",
                v.portaria_id or "-",
                v.tag_code or "Não vinculada",
                status
            ))

    def _build_tags_tab(self):
        from models.tag import TagRepository
        self.tag_repo = TagRepository(self.db)

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Tags")

        frame = ttk.Frame(tab, style="Card.TFrame")
        frame.pack(expand=True, fill='both', padx=10, pady=10)

        columns = ("code", "status")
        self.tree_tags = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree_tags.heading("code", text="Tag Código")
        self.tree_tags.heading("status", text="Status")

        self.tree_tags.column("code", width=300)
        self.tree_tags.column("status", width=150, anchor='center')

        self.tree_tags.pack(expand=True, fill='both', padx=2, pady=2)
        
        btn_refresh = ttk.Button(tab, text="⟳ Atualizar Lista", command=self.refresh_tags)
        btn_refresh.pack(pady=5)

        self.refresh_tags()

    def refresh_tags(self):
        for item in self.tree_tags.get_children():
            self.tree_tags.delete(item)
        
        tags = self.tag_repo.find_all()
        for t in tags:
            status = "Ativa" if t.is_active else "Inativa"
            self.tree_tags.insert("", "end", values=(
                t.tag_code,
                status
            ))

    def refresh_all_tabs(self):
        self.refresh_logs()
        if hasattr(self, 'refresh_vehicles'):
            self.refresh_vehicles()
        if hasattr(self, 'refresh_tags'):
            self.refresh_tags()

    def on_close(self):
        self.destroy()
