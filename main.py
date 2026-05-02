"""
Ponto de entrada da aplicação Gate Automation (Tkinter Lightweight GUI).

Execução:
    python main.py

Variáveis de ambiente opcionais:
    MOCK_HARDWARE=true         Roda sem GPIO/serial (padrão: false)
    SEED_TEST_DATA=true        Semeia dados locais de teste (padrão: true em mock)
"""
import sys
import threading
from datetime import datetime
import logging

import config
from models.database import Database
from models.tag import Tag, TagRepository
from controllers.auth_controller import AuthController
from controllers.sync_controller import SyncController
from commands.rfid_reader import RFIDReader
from commands.gate_controller import GateController
from views.main_window import MainWindow

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def _seed_test_data(db: Database) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags = TagRepository(db)

    tags.upsert(Tag(server_id=99201, tag_code="01000000000000000000000158", driver_id=None, is_active=True, updated_at=now))
    tags.upsert(Tag(server_id=99202, tag_code="01000000000000000000000159", driver_id=None, is_active=False, updated_at=now))
    tags.upsert(Tag(server_id=99203, tag_code="01000000000000000000000160", driver_id=None, is_active=False, updated_at=now))

def main():
    logger.info("Iniciando Gate Automation Tkinter UI...")

    db = Database()
    db.create_tables()

    if config.SEED_TEST_DATA:
        _seed_test_data(db)

    gate = GateController()
    sync = SyncController(db)
    auth = AuthController(db, mode="online")
    
    # Readers variables
    reader_in = None
    reader_out = None

    def start_readers(port_in: str, port_out: str):
        nonlocal reader_in, reader_out
        if reader_in: reader_in.stop()
        if reader_out: reader_out.stop()
        
        reader_in = RFIDReader("IN", port_in, handle_tag)
        reader_out = RFIDReader("OUT", port_out, handle_tag)
        reader_in.start()
        reader_out.start()

    def handle_save_ports(port_in: str, port_out: str):
        start_readers(port_in, port_out)

    def handle_tag(tag_code: str, direction: str):
        logger.info("Leitura: Tag=%s, Direction=%s", tag_code, direction)
        result = auth.process(tag_code, direction)

        if result.authorized:
            gate.open()
            
        # Agendar atualização da UI na thread principal
        if app:
            app.after(0, lambda: [
                app.refresh_logs(),
                app.update_gate_status(result.authorized)
            ])
            
            # Fecha o portão visualmente depois do tempo
            if result.authorized:
                app.after(config.GATE_OPEN_DURATION * 1000, lambda: app.update_gate_status(False))

    def handle_sync():
        logger.info("Forçando sincronização manual...")
        sync._sync_cycle()

    # Create Tkinter UI
    app = MainWindow(
        db=db,
        on_sync=handle_sync,
        on_save_ports=handle_save_ports,
        on_mock_tag=handle_tag
    )

    # Sync status callback
    def update_mode(online: bool):
        auth.mode = "online" if online else "offline"
        app.after(0, lambda: app.update_net_status(online))

    sync._on_status_change = update_mode

    # Read ports from DB
    port_in = db.get_setting("RFID_PORT_IN", config.RFID_PORT_IN)
    port_out = db.get_setting("RFID_PORT_OUT", config.RFID_PORT_OUT)
    
    # Start background tasks
    start_readers(port_in, port_out)
    sync.start()

    # Start UI Loop
    try:
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Sinal recebido.")
    finally:
        logger.info("Encerrando serviços...")
        if reader_in: reader_in.stop()
        if reader_out: reader_out.stop()
        sync.stop()
        gate.cleanup()
        db.close()
        logger.info("Desligamento completo.")

if __name__ == "__main__":
    main()
