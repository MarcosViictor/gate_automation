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
from commands.gate_state_monitor import GateStateMonitor, GATE_OPEN, GATE_CLOSED
from commands.gate_operation_coordinator import GateOperationCoordinator
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
        from models.driver import Driver, DriverRepository
        from models.vehicle import Vehicle, VehicleRepository
        
        tags_repo = TagRepository(db)
        drivers_repo = DriverRepository(db)
        vehicles_repo = VehicleRepository(db)
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Tag antiga
        tags_repo.upsert(Tag(server_id=99204, tag_code="01E28069150000401D63E8C9", driver_id=None, is_active=True, updated_at=now_str))
        
        # Inserindo motorista ritinha
        drivers_repo.upsert(Driver(server_id=99901, name="ritinha", is_active=True, updated_at=now_str))
        active_drivers = drivers_repo.find_all_active()
        ritinha_driver = next((d for d in active_drivers if d.name == "ritinha"), None)
        ritinha_id = ritinha_driver.id if ritinha_driver else None
        
        # Inserindo tag ritinha
        tags_repo.upsert(Tag(server_id=99205, tag_code="01E28069150000401D63E8C5", driver_id=ritinha_id, is_active=True, updated_at=now_str))
        ritinha_tag = tags_repo.find_by_code("01E28069150000401D63E8C5")
        
        if ritinha_tag:
            # Inserindo veículo ritinha
            vehicles_repo.upsert(Vehicle(server_id=103, plate="RIT-0000", model="carro ritinha", tag_id=ritinha_tag.id, is_active=True, updated_at=now_str))
            
        logger.info("Tags padroes garantidas no banco local como ativas (inclui ritinha).")
    except Exception as e:
        logger.error("Erro ao garantir tag do usuario no banco: %s", e)

    if config.SEED_TEST_DATA:
        _seed_test_data(db)

    gate = GateController()
    gate_monitor = GateStateMonitor()
    gate_coordinator = GateOperationCoordinator(gate, gate_monitor)
    
    sync = SyncController(db)
    auth = AuthController(db, mode="online")
    
    # Timer state variables for auto-close
    gate_timer = None
    gate_timer_lock = threading.Lock()

    def close_gate():
        nonlocal gate_timer
        logger.info("⏰ Temporizador expirou. Iniciando processo de FECHAR o portão.")
        gate_coordinator.trigger_gate(GATE_CLOSED)
        with gate_timer_lock:
            gate_timer = None

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
        nonlocal gate_timer
        logger.info("Leitura: Tag=%s, Direction=%s", tag_code, direction)
        result = auth.process(tag_code, direction)

        # Comentado o código original conforme solicitado
        # if result.authorized:
        #     logger.info("🔓 ACESSO AUTORIZADO para a tag %s", tag_code)
        #     gate.open()
        # else:
        #     logger.warning("🔒 ACESSO NEGADO para a tag %s. Motivo: %s", tag_code, result.reason)
        #     
        # # Agendar atualização da UI na thread principal se a tela estiver ativa
        # if app:
        #     app.after(0, lambda: [
        #         app.refresh_all_tabs(),
        #         app.update_gate_status(result.authorized)
        #     ])
        #     
        #     # Fecha o portão visualmente depois do tempo
        #     if result.authorized:
        #         app.after(config.GATE_OPEN_DURATION * 1000, lambda: app.update_gate_status(False))

        # Nova funcionalidade de temporizador de 1:30 para fechar o portão
        if result.authorized:
            logger.info("🔓 ACESSO AUTORIZADO para a tag %s", tag_code)
            logger.info("Evento marcado: AGUARDANDO_ABERTURA")
            
            def track_passage_lifecycle():
                wait_time = 0
                import time
                while gate_monitor.get_state() != GATE_OPEN and wait_time < (config.GATE_MAX_RETRY_ATTEMPTS * config.GATE_PULSE_RESPONSE_SECONDS + 5):
                    time.sleep(1)
                    wait_time += 1
                
                if gate_monitor.get_state() == GATE_OPEN:
                    logger.info("Evento marcado: AGUARDANDO_PASSAGEM")
                    time.sleep(config.GATE_PASSAGE_CONFIRMATION_SECONDS)
                    logger.warning("Passagem nao confirmada dentro da janela configurada")
                    logger.info("Evento marcado: PASSAGEM_NAO_CONFIRMADA")

            threading.Thread(target=track_passage_lifecycle, daemon=True).start()
            
            with gate_timer_lock:
                if gate_timer is not None:
                    logger.info("Reiniciando o temporizador de 1:30 para fechar o portão.")
                    gate_timer.cancel()
                    gate_timer = None
                else:
                    logger.info("Iniciando processo de ABRIR o portão.")
                    gate_coordinator.trigger_gate(GATE_OPEN)
                
                # Agenda o fechamento do portão para 90 segundos (1:30)
                gate_timer = threading.Timer(90.0, close_gate)
                gate_timer.start()
        else:
            logger.warning("🔒 ACESSO NEGADO para a tag %s. Motivo: %s", tag_code, result.reason)

        if app:
            app.after(0, lambda: [
                app.refresh_all_tabs()
                # UI gate status update happens via monitor callbacks now
            ])

    def handle_sync():
        logger.info("Forçando sincronização manual...")
        sync.sync_now()
        if app:
            app.after(0, lambda: app.refresh_all_tabs())

    # Create Tkinter UI if not headless
    if not headless:
        app = MainWindow(
            db=db,
            on_sync=handle_sync,
            on_save_ports=handle_save_ports,
            on_mock_tag=handle_tag
        )
        
        def ui_state_update(state: str):
            if app:
                app.after(0, lambda: app.update_gate_status(state))
                
        gate_coordinator.on_state_update = ui_state_update
    else:
        app = None
        gate_coordinator.on_state_update = lambda state: logger.info(f"UI Mock Update: {state}")

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
    gate_monitor.start()

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
        
        # Cancela temporizador ativo no desligamento
        with gate_timer_lock:
            if gate_timer:
                gate_timer.cancel()
                
        gate_monitor.stop()
        gate.cleanup()
        db.close()
        logger.info("Desligamento completo.")

if __name__ == "__main__":
    main()
