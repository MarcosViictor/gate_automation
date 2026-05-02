from __future__ import annotations
from dataclasses import dataclass

from models.database import Database
from models.tag import TagRepository
from models.access_log import AccessLog, AccessLogRepository


@dataclass
class AuthResult:
    authorized: bool
    tag_code: str
    direction: str = "IN"
    driver_name: str | None = None
    driver_id: int | None = None
    reason: str | None = None
    mode: str = "online"


class AuthController:
    """
    Processa a leitura de uma tag RFID e decide se o acesso é autorizado.
        Regras:
            1. A tag deve existir no banco local.
            2. A tag deve estar ativa.
    """

    def __init__(self, db: Database, mode: str = "online"):
        self._tags = TagRepository(db)
        self._logs = AccessLogRepository(db)
        self.mode = mode  # "online" | "offline"

    def process(self, tag_code: str, direction: str) -> AuthResult:
        tag = self._tags.find_by_code(tag_code)

        if tag is None:
            return self._deny(tag_code, direction, "Tag não cadastrada")

        if not tag.is_active:
            return self._deny(tag_code, direction, "Tag inativa", tag.driver_id)

        return self._allow(tag_code, direction, tag.driver_id)

    # ------------------------------------------------------------------
    def _allow(
        self,
        tag_code: str,
        direction: str,
        driver_id: int | None = None,
        driver_name: str | None = None,
    ) -> AuthResult:
        result = AuthResult(
            authorized=True,
            tag_code=tag_code,
            direction=direction,
            driver_id=driver_id,
            driver_name=driver_name,
            reason="Acesso autorizado",
            mode=self.mode,
        )
        self._save_log(result)
        return result

    def _deny(
        self, tag_code: str, direction: str, reason: str, driver_id: int | None = None
    ) -> AuthResult:
        result = AuthResult(
            authorized=False,
            tag_code=tag_code,
            direction=direction,
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
                authorized=result.authorized,
                direction=result.direction,
                driver_id=result.driver_id,
                reason=result.reason,
                mode=result.mode,
                synced=result.mode == "online",  # se online, servidor já registrou
            )
        )
