from __future__ import annotations
import logging
from dataclasses import dataclass

import requests

import config

logger = logging.getLogger(__name__)


@dataclass
class AccessDecision:
    authorized: bool
    tag_code: str
    direction: str = "IN"
    reason: str | None = None
    online: bool = False


class AuthController:
    """Valida uma tag consultando o servidor local (sb-gatehouse) em tempo real.

    Fail-closed: qualquer falha de rede/servidor resulta em acesso negado.
    Para adicionar autenticação no futuro, basta incluir um header aqui
    (ex.: Authorization) lido de config/.env.
    """

    def check(self, tag_code: str, direction: str = "IN") -> AccessDecision:
        url = f"{config.get_server_base_url()}{config.ACCESS_PATH}"
        try:
            resp = requests.post(
                url, json={"tag_code": tag_code}, timeout=config.SERVER_TIMEOUT
            )
        except Exception as exc:
            logger.warning("Servidor inacessível ao checar tag %s: %s", tag_code, exc)
            return AccessDecision(False, tag_code, direction, "Servidor inacessível", online=False)

        if resp.status_code != 200:
            logger.warning("Servidor respondeu %s para a tag %s", resp.status_code, tag_code)
            return AccessDecision(
                False, tag_code, direction, f"Servidor respondeu {resp.status_code}", online=True
            )

        try:
            data = resp.json()
        except ValueError:
            logger.warning("Resposta JSON inválida do servidor para a tag %s", tag_code)
            return AccessDecision(
                False, tag_code, direction, "Resposta inválida do servidor", online=True
            )

        authorized = bool(data.get("open"))
        reason = data.get("reason") or ("Acesso liberado" if authorized else "Acesso negado")
        return AccessDecision(authorized, tag_code, direction, reason, online=True)
