# Abertura remota (endpoint /open) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o Raspberry escutar um endpoint HTTP leve (`POST /open`, `GET /health`) que aciona o relé, permitindo que o gatehouse comande a abertura manual por push.

**Architecture:** Novo `server/gate_server.py` com `GateServer` (stdlib `ThreadingHTTPServer` em thread daemon) que recebe o POST e chama um callback `on_open`. `main.py` sobe o servidor junto com os leitores e liga o callback ao `gate.open()` existente (relé intocado) + feedback na GUI. Config de porta/token no `.env`.

**Tech Stack:** Python 3.12, stdlib `http.server` (sem dependência nova), `pytest`. Rodar via venv (`venv/bin/python`, `venv/bin/pytest`).

## Global Constraints

- Rodar tudo pelo venv: `venv/bin/pytest`, `venv/bin/python`.
- Sem dependências novas (só stdlib).
- Contrato fixo: `POST /open` → `200 {"opened": true}` (comando aceito); token exigido só se `GATE_OPEN_TOKEN` != "" (header `Authorization`), senão `401 {"error":"unauthorized"}`; rota/método desconhecido → `404`. `GET /health` → `200 {"status":"ok"}` (sem token). Body opcional `{"portaria": <int>}` — só logado.
- Servidor escuta em `0.0.0.0:{GATE_LISTEN_PORT}` (default `8080`).
- NÃO tocar em `commands/gate_controller.py` (relé/GPIO) nem no fluxo de tag; reusar `gate.open()` como está (mantém o nome `open()`).
- `on_open()` deve retornar rápido (o `gate.open()` já dispara o pulso em thread).
- Textos/logs em português. Um commit por tarefa; terminar a mensagem com a linha Co-Authored-By.

---

### Task 1: `GateServer` (endpoint /open + /health)

**Files:**
- Create: `server/__init__.py`
- Create: `server/gate_server.py`
- Test: `tests/test_gate_server.py`

**Interfaces:**
- Produces: `GateServer(on_open: Callable[[], None], port: int, token: str = "")` com `.start()`, `.stop()`, e a property `.port` (porta efetivamente ligada — resolve porta efêmera quando `port=0`).

- [ ] **Step 1: Escrever os testes que falham**

Criar `server/__init__.py` vazio primeiro (senão o import falha na coleta):

```bash
mkdir -p server && touch server/__init__.py
```

Criar `tests/test_gate_server.py`:

```python
import json
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `venv/bin/pytest tests/test_gate_server.py -v`
Expected: FAIL na coleta (`ModuleNotFoundError: No module named 'server.gate_server'`).

- [ ] **Step 3: Implementar `server/gate_server.py`**

```python
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
        length = int(self.headers.get("Content-Length", 0) or 0)
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `venv/bin/pytest tests/test_gate_server.py -v`
Expected: PASS (8 testes).

- [ ] **Step 5: Commit**

```bash
git add server/__init__.py server/gate_server.py tests/test_gate_server.py
git commit -m "feat: GateServer expõe /open e /health para abertura remota

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Config + fiação no `main.py`

**Files:**
- Modify: `config.py`
- Modify: `main.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `GateServer(on_open, port, token)` (Task 1); `AccessDecision` de `controllers.auth_controller`; `gate.open()` de `GateController`.
- Produces: `config.GATE_LISTEN_PORT: int`, `config.GATE_OPEN_TOKEN: str`.

- [ ] **Step 1: Escrever os testes de config que falham**

Adicionar ao fim de `tests/test_config.py`:

```python
def test_gate_listen_port_default():
    import config
    assert config.GATE_LISTEN_PORT == 8080


def test_gate_open_token_default_empty():
    import config
    assert config.GATE_OPEN_TOKEN == ""
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `venv/bin/pytest tests/test_config.py -v`
Expected: FAIL (`AttributeError: module 'config' has no attribute 'GATE_LISTEN_PORT'`).

- [ ] **Step 3: Adicionar as configs no `config.py`**

Adicionar, logo após o bloco "Servidor local (sb-gatehouse)" (perto de `ACCESS_PATH`/`get_server_base_url`):

```python
# ==============================================================================
# Servidor de abertura remota (recebe push do gatehouse)
# ==============================================================================
GATE_LISTEN_PORT = int(os.getenv("GATE_LISTEN_PORT", "8080"))
GATE_OPEN_TOKEN = os.getenv("GATE_OPEN_TOKEN", "")  # vazio = sem autenticação
```

- [ ] **Step 4: Rodar e ver passar**

Run: `venv/bin/pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Fiar o `GateServer` no `main.py` — imports**

Substituir o bloco de imports:

```python
from controllers.auth_controller import AuthController
from commands.rfid_reader import RFIDReader
from commands.gate_controller import GateController
```

por:

```python
from controllers.auth_controller import AuthController, AccessDecision
from commands.rfid_reader import RFIDReader
from commands.gate_controller import GateController
from server.gate_server import GateServer
```

- [ ] **Step 6: Adicionar o handler de abertura remota**

Em `main.py`, logo APÓS o fim da função `handle_tag` (a que termina com o bloco `app.after(0, lambda: ( ... ))`) e ANTES de `def start_readers(...)`, inserir:

```python
    def handle_remote_open():
        logger.info("🔓 Abertura remota recebida do gatehouse")
        gate.open()
        if app:
            remote = AccessDecision(True, "(gatehouse)", "REMOTO", "Abertura remota", online=True)
            app.after(0, lambda: (
                app.add_read_row(remote),
                app.update_gate_status(True),
            ))
```

- [ ] **Step 7: Criar e subir o servidor; pará-lo no shutdown**

Substituir:

```python
    start_readers(port_in, port_out)

    try:
```

por:

```python
    start_readers(port_in, port_out)

    gate_server = GateServer(handle_remote_open, config.GATE_LISTEN_PORT, config.GATE_OPEN_TOKEN)
    gate_server.start()

    try:
```

E no bloco `finally`, substituir:

```python
        if reader_in:
            reader_in.stop()
        if reader_out:
            reader_out.stop()
        gate.cleanup()
```

por:

```python
        if reader_in:
            reader_in.stop()
        if reader_out:
            reader_out.stop()
        gate_server.stop()
        gate.cleanup()
```

- [ ] **Step 8: Verificar — suíte completa + boot + curl real no endpoint**

Run: `venv/bin/pytest -q`
Expected: PASS (todos; a suíte cresce com os testes do GateServer e de config).

Boot headless mock numa porta de teste, e bater no endpoint de verdade:
```bash
GATE_LISTEN_PORT=18080 MOCK_HARDWARE=true HEADLESS=true venv/bin/python main.py > /tmp/gate_open.log 2>&1 &
APP_PID=$!
sleep 2
echo "--- POST /open ---"; curl -s -X POST http://127.0.0.1:18080/open -H "Content-Type: application/json" -d '{"portaria":1}'; echo
echo "--- GET /health ---"; curl -s http://127.0.0.1:18080/health; echo
kill $APP_PID
echo "--- log (deve conter a abertura remota e o mock do portão) ---"
grep -E "Abertura remota|Portão ABERTO|GateServer escutando" /tmp/gate_open.log
```
Expected: `POST /open` → `{"opened": true}`; `GET /health` → `{"status": "ok"}`; o log mostra "GateServer escutando", "Abertura remota recebida" e "[MOCK] Portão ABERTO".

- [ ] **Step 9: Commit**

```bash
git add config.py main.py tests/test_config.py
git commit -m "feat: main sobe GateServer e liga /open ao acionamento do portão

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notas de verificação final

- Suíte completa verde: `venv/bin/pytest -v`.
- App sobe headless e responde `POST /open` (200 `{"opened":true}`) e `GET /health` (200 `{"status":"ok"}`).
- Uma abertura remota aciona o `gate.open()` (relé) e, na GUI, aparece "ABERTURA REMOTA".
- `commands/gate_controller.py` e o fluxo de tag: intocados.
