"""
Ponto de entrada da aplicação Gate Automation.

Execução:
    python main.py

Variáveis de ambiente opcionais:
    MOCK_HARDWARE=true         Roda sem GPIO/serial (padrão: true)
    SEED_TEST_DATA=true        Semeia dados locais de teste (padrão: true em mock)
    SERVER_BASE_URL=http://... Endereço do servidor local
    RFID_PORT=/dev/ttyUSB0     Porta serial do leitor RFID
"""
from datetime import date, datetime
import logging
import customtkinter as ctk

import config
from models.database import Database
from models.driver import Driver, DriverRepository
from models.tag import Tag, TagRepository
from models.schedule import Schedule, ScheduleRepository
from controllers.auth_controller import AuthController
from controllers.sync_controller import SyncController
from commands.rfid_reader import RFIDReader
from commands.gate_controller import GateController
from views.main_window import MainWindow

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _seed_test_data(db: Database) -> None:
    """
    Semeia dados locais para testes de autorizacao.

    - Tag liberada: 01000000000000000000000158
    - Tags inativas: 01000000000000000000000159 e 01000000000000000000000160

    Operacao idempotente (usa server_id fixo via upsert).
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = date.today().isoformat()

    drivers = DriverRepository(db)
    tags = TagRepository(db)
    schedules = ScheduleRepository(db)

    drivers.upsert(
        Driver(
            server_id=99001,
            name="Alex Liberado",
            cpf="000.000.000-01",
            phone="(11) 90000-0001",
            is_active=True,
            updated_at=now,
        )
    )
    drivers.upsert(
        Driver(
            server_id=99002,
            name="Bruno Teste",
            cpf="000.000.000-02",
            phone="(11) 90000-0002",
            is_active=True,
            updated_at=now,
        )
    )

    row_allowed = db.fetchone("SELECT id FROM drivers WHERE server_id = ?", (99001,))
    row_inactive = db.fetchone("SELECT id FROM drivers WHERE server_id = ?", (99002,))
    if row_allowed is None or row_inactive is None:
        logger.warning("Nao foi possivel preparar drivers de teste")
        return

    allowed_driver_id = row_allowed["id"]
    inactive_driver_id = row_inactive["id"]

    schedules.upsert(
        Schedule(
            server_id=99101,
            driver_id=allowed_driver_id,
            scheduled_date=today,
            time_start="00:00",
            time_end="23:59",
            is_active=True,
            updated_at=now,
        )
    )

    tags.upsert(
        Tag(
            server_id=99201,
            tag_code="01000000000000000000000158",
            driver_id=allowed_driver_id,
            is_active=True,
            updated_at=now,
        )
    )
    tags.upsert(
        Tag(
            server_id=99202,
            tag_code="01000000000000000000000159",
            driver_id=inactive_driver_id,
            is_active=False,
            updated_at=now,
        )
    )
    tags.upsert(
        Tag(
            server_id=99203,
            tag_code="01000000000000000000000160",
            driver_id=inactive_driver_id,
            is_active=False,
            updated_at=now,
        )
    )

    logger.info(
        (
            "Dados de teste prontos: liberada=%s inativas=[%s, %s]"
        ),
        "01000000000000000000000158",
        "01000000000000000000000159",
        "01000000000000000000000160",
    )


def main():
    # ------------------------------------------------------------------
    # 1. Banco de dados local (SQLite – backup offline)
    # ------------------------------------------------------------------
    db = Database()
    db.create_tables()

    # Dados locais de teste (mock)
    if config.SEED_TEST_DATA:
        _seed_test_data(db)

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
