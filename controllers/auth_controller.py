from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from models.database import Database
from models.tag import TagRepository
from models.driver import DriverRepository
from models.schedule import ScheduleRepository
from models.access_log import AccessLog, AccessLogRepository


@dataclass
class AuthResult:
    authorized: bool
    tag_code: str
    driver_name: str | None = None
    driver_id: int | None = None
    reason: str | None = None
    mode: str = "online"


class AuthController:
    """
    Processa a leitura de uma tag RFID e decide se o acesso é autorizado.
    Regras:
      1. A tag deve existir no banco local e estar ativa.
      2. O motorista vinculado deve estar ativo.
      3. Deve haver um agendamento ativo para o motorista no dia atual
         dentro do intervalo de horário configurado.
    """

    def __init__(self, db: Database, mode: str = "online"):
        self._tags = TagRepository(db)
        self._drivers = DriverRepository(db)
        self._schedules = ScheduleRepository(db)
        self._logs = AccessLogRepository(db)
        self.mode = mode  # "online" | "offline"

    def process(self, tag_code: str) -> AuthResult:
        tag = self._tags.find_by_code(tag_code)

        if tag is None:
            return self._deny(tag_code, "Tag não cadastrada")

        if tag.driver_id is None:
            return self._deny(tag_code, "Tag sem motorista vinculado")

        driver = self._drivers.find_by_id(tag.driver_id)
        if driver is None or not driver.is_active:
            return self._deny(tag_code, "Motorista inativo ou não encontrado", tag.driver_id)

        schedule = self._schedules.find_active_for_driver_today(driver.id)
        if schedule is None:
            return self._deny(
                tag_code,
                f"Sem agendamento para hoje ({driver.name})",
                driver.id,
            )

        now_time = datetime.now().strftime("%H:%M")
        if not (schedule.time_start <= now_time <= schedule.time_end):
            return self._deny(
                tag_code,
                f"Fora do horário permitido ({schedule.time_start}–{schedule.time_end})",
                driver.id,
            )

        return self._allow(tag_code, driver.id, driver.name)

    # ------------------------------------------------------------------
    def _allow(self, tag_code: str, driver_id: int, driver_name: str) -> AuthResult:
        result = AuthResult(
            authorized=True,
            tag_code=tag_code,
            driver_id=driver_id,
            driver_name=driver_name,
            reason="Acesso autorizado",
            mode=self.mode,
        )
        self._save_log(result)
        return result

    def _deny(
        self, tag_code: str, reason: str, driver_id: int | None = None
    ) -> AuthResult:
        result = AuthResult(
            authorized=False,
            tag_code=tag_code,
            driver_id=driver_id,
            reason=reason,
            mode=self.mode,
        )
        self._save_log(result)
        return result

    def _save_log(self, result: AuthResult) -> None:
        self._logs.save(
            AccessLog(
                tag_code=result.tag_code,
                driver_id=result.driver_id,
                authorized=result.authorized,
                reason=result.reason,
                mode=result.mode,
                synced=result.mode == "online",  # se online, servidor já registrou
            )
        )
