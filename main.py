"""
Ponto de entrada da aplicação Gate Automation.

Execução:
    python main.py

Variáveis de ambiente opcionais:
    MOCK_HARDWARE=true         Roda sem GPIO/serial (padrão: true)
    SERVER_BASE_URL=http://... Endereço do servidor local
    RFID_PORT=/dev/ttyUSB0     Porta serial do leitor RFID
"""
import logging
import customtkinter as ctk

import config
from models.database import Database
from controllers.auth_controller import AuthController
from controllers.sync_controller import SyncController
from commands.rfid_reader import RFIDReader
from commands.gate_controller import GateController
from views.main_window import MainWindow

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    # ------------------------------------------------------------------
    # 1. Banco de dados local (SQLite – backup offline)
    # ------------------------------------------------------------------
    db = Database()
    db.create_tables()

    # ------------------------------------------------------------------
    # 2. Hardware
    # ------------------------------------------------------------------
    gate = GateController()

    # ------------------------------------------------------------------
    # 3. Controllers
    # ------------------------------------------------------------------
    sync = SyncController(db)
    auth = AuthController(db, mode="online")

    # ------------------------------------------------------------------
    # 4. Leitor RFID
    # ------------------------------------------------------------------
    rfid = RFIDReader(on_tag=lambda _: None)  # callback real definido na view

    # ------------------------------------------------------------------
    # 5. Interface gráfica
    # ------------------------------------------------------------------
    ctk.set_appearance_mode(config.THEME)
    ctk.set_default_color_theme(config.COLOR_SCHEME)

    window = MainWindow(
        auth_controller=auth,
        sync_controller=sync,
        rfid_reader=rfid,
        gate_controller=gate,
    )

    # Injeta DB nas views que precisam
    window._views["logs"].set_database(db)
    window._views["drivers"].set_database(db)
    window._views["schedules"].set_database(db)
    window._views["status"].set_database(db)

    # Conecta atualização de status de rede à janela
    sync._on_status_change = lambda online: (
        window.update_connection_status(online),
        setattr(auth, "mode", "online" if online else "offline"),
    )

    # ------------------------------------------------------------------
    # 6. Inicia serviços em background
    # ------------------------------------------------------------------
    rfid.start()
    sync.start()
    sync.sync_now()  # sincronização inicial imediata

    # ------------------------------------------------------------------
    # 7. Loop da interface
    # ------------------------------------------------------------------
    window.mainloop()

    db.close()


if __name__ == "__main__":
    main()
