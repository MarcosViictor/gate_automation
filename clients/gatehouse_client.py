from __future__ import annotations
import logging
from dataclasses import dataclass

import requests

import config

logger = logging.getLogger(__name__)


@dataclass
class GatehouseResponse:
    reachable: bool
    status_code: int | None = None
    data: dict | None = None
    error: str | None = None


class GatehouseClient:
    """Cliente HTTP do servidor local (sb-gatehouse).

    Responsabilidade única: montar a URL, fazer o POST e devolver uma resposta
    neutra. Não conhece a semântica de autorização (isso é do AuthController).

    base_url e timeout são callables lidos a cada chamada, para que mudanças de
    IP/porta salvas pela GUI valham sem reiniciar.
    """

    def __init__(self, base_url=None, timeout=None, session=None):
        self._base_url = base_url or config.get_server_base_url
        self._timeout = timeout or (lambda: config.SERVER_TIMEOUT)
        self._session = session or requests

    def post_access(self, tag_code: str) -> GatehouseResponse:
        url = f"{self._base_url()}{config.ACCESS_PATH}"
        try:
            resp = self._session.post(
                url, json={"tag_code": tag_code}, timeout=self._timeout()
            )
        except Exception as exc:
            logger.warning("Servidor inacessível ao chamar %s: %s", url, exc)
            return GatehouseResponse(reachable=False, error=str(exc))

        data = None
        if resp.status_code == 200:
            try:
                parsed = resp.json()
                if isinstance(parsed, dict):
                    data = parsed
            except ValueError:
                data = None
        return GatehouseResponse(reachable=True, status_code=resp.status_code, data=data)
