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
        import requests
        import config
        import logging
        logger = logging.getLogger(__name__)

        # Faz requisição direta para a API do usuário
        url = f"{config.SERVER_BASE_URL}/api/gate/check"
        headers = {
            "Authorization": "sbs",
            "Content-Type": "application/json"
        }
        payload = {"code": tag_code}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            # Como não sabemos o formato exato da resposta de sucesso (se é 200 OK e se o corpo diz true/false),
            # vamos assumir que um status code de sucesso (ex: 200) significa autorizado.
            if response.status_code == 200:
                return self._allow(tag_code, direction, reason="Acesso autorizado via API")
            else:
                reason = f"Negado pela API (Status {response.status_code})"
                try:
                    data = response.json()
                    if "message" in data:
                        reason = data["message"]
                except:
                    pass
                return self._deny(tag_code, direction, reason)
        except Exception as e:
            logger.error("Erro de conexão com a API: %s", e)
            return self._deny(tag_code, direction, f"Erro de conexão: {e}")

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
