import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from clients.gatehouse_client import GatehouseClient


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        tag = body.get("tag_code")
        if tag == "BOOM":
            self.send_response(500)
            self.end_headers()
            return
        if tag == "NOTJSON":
            data = b"not-json-at-all"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        data = json.dumps({"decision": "allowed", "open": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def stub(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", str(port))
    yield port
    server.shutdown()
    server.server_close()


def test_post_access_200_dict(stub):
    r = GatehouseClient().post_access("OK")
    assert r.reachable is True
    assert r.status_code == 200
    assert r.data == {"decision": "allowed", "open": True}


def test_post_access_non_200(stub):
    r = GatehouseClient().post_access("BOOM")
    assert r.reachable is True
    assert r.status_code == 500
    assert r.data is None


def test_post_access_non_json_body(stub):
    r = GatehouseClient().post_access("NOTJSON")
    assert r.reachable is True
    assert r.status_code == 200
    assert r.data is None


def test_post_access_offline(monkeypatch):
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", "9")  # porta sem listener -> conexão recusada
    r = GatehouseClient().post_access("OK")
    assert r.reachable is False
    assert r.status_code is None
    assert r.error is not None
