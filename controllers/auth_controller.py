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
    synced: bool = False


class AuthController:
    """
    Processa a leitura de uma tag RFID e decide se o acesso é autorizado.
        Regras:
            1. A tag deve existir no banco local.
            2. A tag deve estar ativa.
    """

    def __init__(self, db: Database, mode: str = "online"):
        self._db = db
        self._tags = TagRepository(db)
        self._logs = AccessLogRepository(db)
        self.mode = mode  # "online" | "offline"

    def process(self, tag_code: str, direction: str) -> AuthResult:
        import requests
        import config
        import logging
        from models.driver import DriverRepository
        logger = logging.getLogger(__name__)

        # 1. Validação local no banco de dados
        tag = self._tags.find_by_code(tag_code)

        if tag is None:
            # Tag não cadastrada localmente
            return self._deny(
                tag_code=tag_code,
                direction=direction,
                reason="Tag não cadastrada",
                driver_id=None,
                mode="offline",
                synced=False
            )
        elif not tag.is_active:
            # Tag cadastrada, mas inativa
            return self._deny(
                tag_code=tag_code,
                direction=direction,
                reason="Tag inativa",
                driver_id=tag.driver_id,
                mode="offline",
                synced=False
            )

        # 2. Tag é ativa e cadastrada -> Autorizado!
        # Agora tentamos notificar/sincronizar com a API se estiver no modo online
        synced = False
        mode = "offline"

        if self.mode == "online":
            url = f"{config.SERVER_BASE_URL}/api/gate/check"
            headers = {
                "Authorization": "sbs",
                "Content-Type": "application/json"
            }
            payload = {"code": tag_code}
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=config.SERVER_TIMEOUT)
                if response.status_code == 200:
                    synced = True
                    mode = "online"
                    logger.info("Evento de acesso da tag %s enviado com sucesso para a API.", tag_code)
                else:
                    logger.warning("API retornou status %s ao registrar acesso da tag %s.", response.status_code, tag_code)
            except Exception as e:
                logger.error("Erro de conexão ao enviar tag %s para a API: %s. Operando offline.", tag_code, e)

        # Busca o nome do motorista, caso exista driver_id associado à tag
        driver_name = None
        if tag.driver_id:
            try:
                driver_repo = DriverRepository(self._db)
                driver = driver_repo.find_by_id(tag.driver_id)
                if driver:
                    driver_name = driver.name
            except Exception as e:
                logger.error("Erro ao buscar motorista localmente: %s", e)

        return self._allow(
            tag_code=tag_code,
            direction=direction,
            driver_id=tag.driver_id,
            driver_name=driver_name,
            mode=mode,
            synced=synced
        )

    # ------------------------------------------------------------------
    def _allow(
        self,
        tag_code: str,
        direction: str,
        driver_id: int | None = None,
        driver_name: str | None = None,
        mode: str = "online",
        synced: bool = False,
    ) -> AuthResult:
        result = AuthResult(
            authorized=True,
            tag_code=tag_code,
            direction=direction,
            driver_id=driver_id,
            driver_name=driver_name,
            reason="Acesso autorizado",
            mode=mode,
            synced=synced,
        )
        self._save_log(result)
        return result

    def _deny(
        self,
        tag_code: str,
        direction: str,
        reason: str,
        driver_id: int | None = None,
        driver_name: str | None = None,
        mode: str = "offline",
        synced: bool = False,
    ) -> AuthResult:
        result = AuthResult(
            authorized=False,
            tag_code=tag_code,
            direction=direction,
            driver_id=driver_id,
            driver_name=driver_name,
            reason=reason,
            mode=mode,
            synced=synced,
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
                synced=result.synced,
            )
        )
