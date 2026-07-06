from __future__ import annotations
from dataclasses import dataclass

from clients.gatehouse_client import GatehouseClient


@dataclass
class AccessDecision:
    authorized: bool
    tag_code: str
    direction: str = "IN"
    reason: str | None = None
    online: bool = False


class AuthController:
    """Decide se uma tag é autorizada, mapeando a resposta do GatehouseClient.

    Fail-closed: qualquer falha de rede/servidor resulta em acesso negado.
    """

    def __init__(self, client: GatehouseClient | None = None):
        self._client = client or GatehouseClient()

    def check(self, tag_code: str, direction: str = "IN") -> AccessDecision:
        r = self._client.post_access(tag_code)
        if not r.reachable:
            return AccessDecision(False, tag_code, direction, "Servidor inacessível", online=False)
        if r.status_code != 200:
            return AccessDecision(
                False, tag_code, direction, f"Servidor respondeu {r.status_code}", online=True
            )
        if r.data is None:
            return AccessDecision(
                False, tag_code, direction, "Resposta inválida do servidor", online=True
            )
        authorized = bool(r.data.get("open"))
        reason = r.data.get("reason") or ("Acesso liberado" if authorized else "Acesso negado")
        return AccessDecision(authorized, tag_code, direction, reason, online=True)
