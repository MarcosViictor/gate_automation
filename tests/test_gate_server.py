import json
import socket
import urllib.error
import urllib.request

import pytest

from server.gate_server import GateServer


def _post(port, path, body=None, headers=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST", headers=headers or {})
    try:
        resp = urllib.request.urlopen(req, timeout=3)
        return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def _get(port, path):
    url = f"http://127.0.0.1:{port}{path}"
    try:
        resp = urllib.request.urlopen(url, timeout=3)
        return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


@pytest.fixture
def make_server():
    servers = []

    def factory(token="", on_open=None):
        calls = []
        cb = on_open or (lambda: calls.append(1))
        srv = GateServer(cb, port=0, token=token)
        srv.start()
        srv.calls = calls
        servers.append(srv)
        return srv

    yield factory
    for s in servers:
        s.stop()


def test_open_without_token_calls_on_open(make_server):
    srv = make_server()
    status, body = _post(srv.port, "/open")
    assert status == 200
    assert body == {"opened": True}
    assert srv.calls == [1]


def test_open_with_correct_token(make_server):
    srv = make_server(token="segredo")
    status, _ = _post(srv.port, "/open", headers={"Authorization": "segredo"})
    assert status == 200
    assert srv.calls == [1]


def test_open_with_wrong_token_is_401_and_no_call(make_server):
    srv = make_server(token="segredo")
    status, body = _post(srv.port, "/open", headers={"Authorization": "errado"})
    assert status == 401
    assert body == {"error": "unauthorized"}
    assert srv.calls == []


def test_open_accepts_portaria_body(make_server):
    srv = make_server()
    status, _ = _post(srv.port, "/open", body={"portaria": 1})
    assert status == 200
    assert srv.calls == [1]


def test_health_returns_ok(make_server):
    srv = make_server()
    status, body = _get(srv.port, "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_get_open_is_404(make_server):
    srv = make_server()
    status, _ = _get(srv.port, "/open")
    assert status == 404


def test_post_unknown_route_is_404(make_server):
    srv = make_server()
    status, _ = _post(srv.port, "/nope")
    assert status == 404


def test_on_open_exception_returns_500(make_server):
    def boom():
        raise RuntimeError("falhou")

    srv = make_server(on_open=boom)
    status, _ = _post(srv.port, "/open")
    assert status == 500


def test_open_with_missing_authorization_header_is_401(make_server):
    srv = make_server(token="segredo")
    status, _ = _post(srv.port, "/open")  # sem header Authorization
    assert status == 401
    assert srv.calls == []


def test_malformed_content_length_returns_400(make_server):
    srv = make_server()
    raw = (
        "POST /open HTTP/1.1\r\n"
        "Host: 127.0.0.1\r\n"
        "Content-Length: abc\r\n"
        "Connection: close\r\n\r\n"
    ).encode()
    s = socket.create_connection(("127.0.0.1", srv.port), timeout=3)
    s.sendall(raw)
    resp = b""
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        resp += chunk
    s.close()
    status_line = resp.split(b"\r\n", 1)[0]
    assert b"400" in status_line
    assert srv.calls == []
