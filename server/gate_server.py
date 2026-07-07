from __future__ import annotations
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

logger = logging.getLogger(__name__)


class _GateHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/open":
            self._send_json(404, {"error": "not_found"})
            return

        token = self.server.token
        if token and self.headers.get("Authorization") != token:
            logger.warning("Abertura remota rejeitada: token inválido")
            self._send_json(401, {"error": "unauthorized"})
            return

        # Body opcional {"portaria": <id>} — apenas informativo para o log.
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            self._send_json(400, {"error": "bad_request"})
            return
        if length:
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                if isinstance(data, dict) and "portaria" in data:
                    logger.info("Abertura remota para portaria %s", data.get("portaria"))
            except ValueError:
                pass  # body não-JSON é ignorado

        try:
            self.server.on_open()
        except Exception as exc:
            logger.error("Erro ao processar abertura remota: %s", exc)
            self._send_json(500, {"error": "internal"})
            return

        self._send_json(200, {"opened": True})

    def log_message(self, *args):
        pass  # silencia o log padrão do http.server


class GateServer:
    """Servidor HTTP leve que recebe o comando de abertura remota do gatehouse.

    Responsabilidade única: falar HTTP e chamar o callback on_open. Não conhece
    relé nem GUI.
    """

    def __init__(self, on_open: Callable[[], None], port: int, token: str = ""):
        self._on_open = on_open
        self._port = port
        self._token = token
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self._port

    def start(self) -> None:
        self._httpd = ThreadingHTTPServer(("0.0.0.0", self._port), _GateHandler)
        self._port = self._httpd.server_address[1]  # resolve porta efêmera quando port=0
        # o handler acessa on_open/token via a instância do servidor
        self._httpd.on_open = self._on_open
        self._httpd.token = self._token
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        logger.info("GateServer escutando em 0.0.0.0:%d (/open, /health)", self._port)

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
