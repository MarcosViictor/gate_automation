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
    from models.vehicle import Vehicle, VehicleRepository
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags = TagRepository(db)
    vehicles = VehicleRepository(db)

    tags.upsert(Tag(server_id=99201, tag_code="01000000000000000000000158", driver_id=None, is_active=True, updated_at=now))
    tags.upsert(Tag(server_id=99202, tag_code="01000000000000000000000159", driver_id=None, is_active=False, updated_at=now))
    tags.upsert(Tag(server_id=99203, tag_code="01000000000000000000000160", driver_id=None, is_active=False, updated_at=now))
    tags.upsert(Tag(server_id=99204, tag_code="01E28069150000401D63E8C9", driver_id=None, is_active=True, updated_at=now))

    # Fetch seeded tag IDs to associate with vehicles
    t1 = tags.find_by_code("01000000000000000000000158")
    t2 = tags.find_by_code("01E28069150000401D63E8C9")

    if t1:
        vehicles.upsert(Vehicle(server_id=101, plate="ABC-1234", model="Toyota Hilux", portaria_id=1, tag_id=t1.id, is_active=True, updated_at=now))
    if t2:
        vehicles.upsert(Vehicle(server_id=102, plate="XYZ-9876", model="Honda Civic", portaria_id=2, tag_id=t2.id, is_active=True, updated_at=now))

def main():
    logger.info("Iniciando Gate Automation...")

    import os
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    
    # Detecção automática de ambiente sem display no Linux
    if not headless and sys.platform.startswith("linux") and not os.getenv("DISPLAY"):
        logger.info("Nenhuma variável DISPLAY detectada no Linux. Ativando modo headless automaticamente.")
        headless = True

    db = Database()
    db.create_tables()

    # Garante que a tag do usuário esteja sempre cadastrada e ativa no banco de dados local
    try:
        tags_repo = TagRepository(db)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tags_repo.upsert(Tag(server_id=99204, tag_code="01E28069150000401D63E8C9", driver_id=None, is_active=True, updated_at=now_str))
        logger.info("Tag 01E28069150000401D63E8C9 garantida no banco local como ativa.")
    except Exception as e:
        logger.error("Erro ao garantir tag do usuário no banco: %s", e)

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
        # reader_out = RFIDReader("OUT", port_out, handle_tag)
        reader_in.start()
        # reader_out.start()

    def handle_save_ports(port_in: str, port_out: str):
        start_readers(port_in, port_out)

    def handle_tag(tag_code: str, direction: str):
        logger.info("Leitura: Tag=%s, Direction=%s", tag_code, direction)
        result = auth.process(tag_code, direction)

        if result.authorized:
            logger.info("🔓 ACESSO AUTORIZADO para a tag %s", tag_code)
            gate.open()
        else:
            logger.warning("🔒 ACESSO NEGADO para a tag %s. Motivo: %s", tag_code, result.reason)
            
        # Agendar atualização da UI na thread principal se a tela estiver ativa
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

    # Create Tkinter UI if not headless
    if not headless:
        app = MainWindow(
            db=db,
            on_sync=handle_sync,
            on_save_ports=handle_save_ports,
            on_mock_tag=handle_tag
        )
    else:
        app = None

    # Sync status callback
    def update_mode(online: bool):
        auth.mode = "online" if online else "offline"
        if app:
            app.after(0, lambda: app.update_net_status(online))

    sync._on_status_change = update_mode

    # Read ports from DB
    port_in = db.get_setting("RFID_PORT_IN", config.RFID_PORT_IN)
    port_out = db.get_setting("RFID_PORT_OUT", config.RFID_PORT_OUT)
    
    # Start background tasks
    start_readers(port_in, port_out)
    sync.start()

    # Start loop
    try:
        if headless:
            logger.info("Serviço iniciado com sucesso em modo HEADLESS. Pressione Ctrl+C para encerrar.")
            exit_event = threading.Event()
            exit_event.wait()
        else:
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
