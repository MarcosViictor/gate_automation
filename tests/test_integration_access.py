import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from controllers.auth_controller import AuthController


class _StubHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        # Regra do stub: tag "OK" libera; qualquer outra nega.
        allowed = body.get("tag_code") == "OK"
        payload = {
            "decision": "allowed" if allowed else "denied",
            "open": allowed,
        }
        if not allowed:
            payload["reason"] = "Tag inativa"
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # silencia o log do servidor


@pytest.fixture
def stub_server(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _StubHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", str(port))
    yield port
    server.shutdown()


def test_allowed_against_real_server(stub_server):
    result = AuthController().check("OK", "IN")
    assert result.authorized is True
    assert result.online is True


def test_denied_against_real_server(stub_server):
    result = AuthController().check("NOPE", "IN")
    assert result.authorized is False
    assert result.online is True
    assert result.reason == "Tag inativa"


def test_offline_when_server_down(monkeypatch):
    # Porta sem ninguém escutando -> fail-closed offline.
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", "9")  # porta reservada, recusa conexão
    result = AuthController().check("OK", "IN")
    assert result.authorized is False
    assert result.online is False
