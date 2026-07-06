from unittest.mock import patch, MagicMock

from controllers.auth_controller import AuthController, AccessDecision


def _fake_response(status_code, json_data=None, raise_json=False):
    resp = MagicMock()
    resp.status_code = status_code
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_data or {}
    return resp


def test_allowed_when_open_true():
    resp = _fake_response(200, {"decision": "allowed", "open": True})
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123", "IN")
    assert result.authorized is True
    assert result.online is True
    assert result.tag_code == "TAG123"
    assert result.direction == "IN"


def test_denied_preserves_reason():
    resp = _fake_response(200, {"decision": "denied", "open": False, "reason": "Tag inativa"})
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is True
    assert result.reason == "Tag inativa"


def test_network_error_is_fail_closed_and_offline():
    import requests
    with patch("controllers.auth_controller.requests.post",
               side_effect=requests.exceptions.ConnectionError("down")):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is False
    assert result.reason == "Servidor inacessível"


def test_non_200_is_fail_closed_but_online():
    resp = _fake_response(500)
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is True


def test_bad_json_is_fail_closed():
    resp = _fake_response(200, raise_json=True)
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is True


def test_non_dict_json_is_fail_closed():
    resp = _fake_response(200, [1, 2, 3])
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is True
