from __future__ import annotations
import threading
import time
import logging
from datetime import datetime
from typing import Callable

import requests

import config
from models.database import Database
from models.tag import Tag, TagRepository
from models.driver import Driver, DriverRepository
from models.schedule import Schedule, ScheduleRepository
from models.access_log import AccessLogRepository

logger = logging.getLogger(__name__)


class SyncController:
    """
    Sincroniza o banco de dados local com o servidor.

    - Pull: baixa tags, motoristas e agendamentos do servidor.
    - Push: envia logs de acesso pendentes para o servidor.
    - Executa em thread de fundo com intervalo configurável.
    """

    def __init__(self, db: Database, on_status_change: Callable[[bool], None] | None = None):
        self._db = db
        self._tags = TagRepository(db)
        self._drivers = DriverRepository(db)
        self._schedules = ScheduleRepository(db)
        self._logs = AccessLogRepository(db)

        self.is_online: bool = False
        self.last_sync: str | None = None
        self._on_status_change = on_status_change
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def start(self):
        """Inicia a thread de sincronização em background."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Loop de sincronização
    # ------------------------------------------------------------------
    def _loop(self):
        while not self._stop_event.is_set():
            self.sync_now()
            self._stop_event.wait(config.SYNC_INTERVAL)

    def sync_now(self) -> bool:
        """Realiza uma sincronização imediata. Retorna True se bem-sucedida."""
        try:
            self._pull_drivers()
            self._pull_tags()
            self._pull_schedules()
            self._push_logs()

            self.last_sync = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            self._set_online(True)
            logger.info("Sincronização concluída: %s", self.last_sync)
            return True

        except requests.exceptions.ConnectionError:
            logger.warning("Servidor indisponível – operando com backup local")
            self._set_online(False)
        except requests.exceptions.Timeout:
            logger.warning("Timeout na sincronização com o servidor")
            self._set_online(False)
        except Exception as exc:
            logger.error("Erro inesperado na sincronização: %s", exc)
            self._set_online(False)

        return False

    # ------------------------------------------------------------------
    # Pull do servidor → banco local
    # ------------------------------------------------------------------
    def _pull_drivers(self):
        data = self._get("/sync/drivers")
        for item in data:
            self._drivers.upsert(
                Driver(
                    server_id=item["id"],
                    name=item["name"],
                    cpf=item.get("cpf"),
                    phone=item.get("phone"),
                    is_active=item.get("is_active", True),
                    updated_at=item.get("updated_at"),
                )
            )

    def _pull_tags(self):
        data = self._get("/sync/tags")
        for item in data:
            # Resolve driver_id local a partir do server_id
            driver_local_id = None
            if item.get("driver_id"):
                row = self._db.fetchone(
                    "SELECT id FROM drivers WHERE server_id = ?", (item["driver_id"],)
                )
                if row:
                    driver_local_id = row["id"]

            self._tags.upsert(
                Tag(
                    server_id=item["id"],
                    tag_code=item["tag_code"],
                    driver_id=driver_local_id,
                    is_active=item.get("is_active", True),
                    updated_at=item.get("updated_at"),
                )
            )

    def _pull_schedules(self):
        data = self._get("/sync/schedules")
        for item in data:
            driver_local_id = None
            if item.get("driver_id"):
                row = self._db.fetchone(
                    "SELECT id FROM drivers WHERE server_id = ?", (item["driver_id"],)
                )
                if row:
                    driver_local_id = row["id"]

            self._schedules.upsert(
                Schedule(
                    server_id=item["id"],
                    driver_id=driver_local_id,
                    scheduled_date=item["scheduled_date"],
                    time_start=item["time_start"],
                    time_end=item["time_end"],
                    is_active=item.get("is_active", True),
                    updated_at=item.get("updated_at"),
                )
            )

    # ------------------------------------------------------------------
    # Push: logs de acesso pendentes → servidor
    # ------------------------------------------------------------------
    def _push_logs(self):
        unsynced = self._logs.find_unsynced()
        for log in unsynced:
            try:
                requests.post(
                    f"{config.SERVER_BASE_URL}/sync/access-logs",
                    json={
                        "tag_code": log.tag_code,
                        "driver_id": log.driver_id,
                        "authorized": log.authorized,
                        "reason": log.reason,
                        "timestamp": log.timestamp,
                    },
                    timeout=config.SERVER_TIMEOUT,
                )
                self._logs.mark_synced(log.id)
            except Exception:
                break  # aborta no primeiro erro; tenta novamente no próximo ciclo

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get(self, path: str) -> list[dict]:
        response = requests.get(
            f"{config.SERVER_BASE_URL}{path}",
            timeout=config.SERVER_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def _set_online(self, online: bool):
        changed = self.is_online != online
        self.is_online = online
        if changed and self._on_status_change:
            self._on_status_change(online)
