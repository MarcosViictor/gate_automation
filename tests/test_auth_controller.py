from clients.gatehouse_client import GatehouseResponse
from controllers.auth_controller import AuthController


class FakeGatehouseClient:
    """Duck-type do GatehouseClient: só precisa de post_access."""

    def __init__(self, response):
        self._response = response
        self.calls = []

    def post_access(self, tag_code):
        self.calls.append(tag_code)
        return self._response


def _auth(response):
    return AuthController(FakeGatehouseClient(response))


def test_allowed_when_open_true():
    auth = _auth(GatehouseResponse(reachable=True, status_code=200, data={"open": True}))
    result = auth.check("TAG123", "IN")
    assert result.authorized is True
    assert result.online is True
    assert result.tag_code == "TAG123"
    assert result.direction == "IN"


def test_denied_preserves_reason():
    auth = _auth(GatehouseResponse(
        reachable=True, status_code=200, data={"open": False, "reason": "Tag inativa"}))
    result = auth.check("TAG123")
    assert result.authorized is False
    assert result.online is True
    assert result.reason == "Tag inativa"


def test_offline_is_fail_closed():
    auth = _auth(GatehouseResponse(reachable=False, error="down"))
    result = auth.check("TAG123")
    assert result.authorized is False
    assert result.online is False
    assert result.reason == "Servidor inacessível"


def test_non_200_is_fail_closed_but_online():
    auth = _auth(GatehouseResponse(reachable=True, status_code=500, data=None))
    result = auth.check("TAG123")
    assert result.authorized is False
    assert result.online is True


def test_invalid_body_is_fail_closed():
    auth = _auth(GatehouseResponse(reachable=True, status_code=200, data=None))
    result = auth.check("TAG123")
    assert result.authorized is False
    assert result.online is True
