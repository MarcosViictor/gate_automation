# Camada de Comunicação (GatehouseClient) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduzir um `GatehouseClient` leve que centraliza toda a comunicação HTTP com o sb-gatehouse, separando transporte (cliente) de domínio (AuthController).

**Architecture:** Novo pacote `clients/` com `GatehouseClient.post_access(tag_code) -> GatehouseResponse` (resposta neutra). `AuthController` passa a receber o cliente por injeção e só mapeia a resposta para `AccessDecision`. `main.py` cria uma instância única e a injeta, usando-a também no botão "Testar conexão". Refactor puro: contrato de rede, comportamento e mensagens idênticos.

**Tech Stack:** Python 3.12, `requests` (já presente), `pytest`. Rodar via venv (`venv/bin/python`, `venv/bin/pytest`).

## Global Constraints

- Rodar tudo pelo venv: `venv/bin/pytest`, `venv/bin/python`.
- Sem dependências novas (reusar `requests`).
- Comportamento e mensagens de rede IDÊNTICOS aos atuais (refactor puro). Mensagens exatas: "Servidor inacessível", "Servidor respondeu {status}", "Resposta inválida do servidor", "Acesso liberado"/"Acesso negado" (default quando o servidor não manda `reason`).
- `GatehouseClient` NÃO conhece `AccessDecision`; `AuthController` NÃO chama `requests` diretamente.
- `base_url` e `timeout` do cliente são callables, lidos a cada chamada (mudança de IP/porta pela GUI vale sem reiniciar).
- NÃO tocar: `config.py`, `views/main_window.py`, `commands/*` (parte física).
- Textos/logs em português. Um commit por tarefa; terminar a mensagem com a linha Co-Authored-By.

---

### Task 1: `GatehouseClient` + `GatehouseResponse`

**Files:**
- Create: `clients/__init__.py`
- Create: `clients/gatehouse_client.py`
- Test: `tests/test_gatehouse_client.py`

**Interfaces:**
- Consumes: `config.get_server_base_url()`, `config.ACCESS_PATH`, `config.SERVER_TIMEOUT`.
- Produces:
  - `GatehouseResponse(reachable: bool, status_code: int | None = None, data: dict | None = None, error: str | None = None)` (dataclass).
  - `GatehouseClient(base_url=None, timeout=None, session=None)` com `post_access(tag_code: str) -> GatehouseResponse`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `clients/__init__.py` vazio primeiro (senão o import falha na coleta):

```bash
mkdir -p clients && touch clients/__init__.py
```

Criar `tests/test_gatehouse_client.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `venv/bin/pytest tests/test_gatehouse_client.py -v`
Expected: FAIL na coleta (`ModuleNotFoundError: No module named 'clients.gatehouse_client'`).

- [ ] **Step 3: Implementar `clients/gatehouse_client.py`**

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `venv/bin/pytest tests/test_gatehouse_client.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add clients/__init__.py clients/gatehouse_client.py tests/test_gatehouse_client.py
git commit -m "feat: GatehouseClient centraliza comunicação HTTP com o servidor

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `AuthController` consome o cliente (transporte fora do domínio)

**Files:**
- Rewrite: `controllers/auth_controller.py`
- Rewrite: `tests/test_auth_controller.py`

**Interfaces:**
- Consumes: `clients.gatehouse_client.GatehouseClient`, `GatehouseResponse` (da Task 1).
- Produces:
  - `AuthController(client: GatehouseClient | None = None)` com `check(tag_code, direction="IN") -> AccessDecision`.
  - `AccessDecision` (dataclass) inalterado: `authorized, tag_code, direction="IN", reason=None, online=False`.

- [ ] **Step 1: Reescrever os testes (falham antes da implementação)**

Substituir todo o conteúdo de `tests/test_auth_controller.py` por (agora injeta um fake, sem `monkeypatch` em `requests`):

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `venv/bin/pytest tests/test_auth_controller.py -v`
Expected: FAIL (`AuthController` atual não aceita cliente / ainda importa requests; e `GatehouseResponse` não é consumido pelo controller ainda).

- [ ] **Step 3: Reescrever `controllers/auth_controller.py`**

Substituir todo o conteúdo por:

```python
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
```

- [ ] **Step 4: Rodar os testes afetados e ver passar**

Run: `venv/bin/pytest tests/test_auth_controller.py tests/test_integration_access.py -v`
Expected: PASS. (O `test_integration_access.py` NÃO muda: ele constrói `AuthController()` sem argumentos, que usa um `GatehouseClient` padrão real contra o servidor-stub — continua funcionando de ponta a ponta.)

- [ ] **Step 5: Commit**

```bash
git add controllers/auth_controller.py tests/test_auth_controller.py
git commit -m "refactor: AuthController mapeia resposta do GatehouseClient (transporte fora do domínio)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `main.py` injeta o cliente e o reusa no "Testar conexão"

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `GatehouseClient` (Task 1), `AuthController(client)` (Task 2), `config.get_server_base_url`.

- [ ] **Step 1: Adicionar o import do cliente**

Em `main.py`, junto dos outros imports de projeto (perto de `from controllers.auth_controller import AuthController`), adicionar:

```python
from clients.gatehouse_client import GatehouseClient
```

- [ ] **Step 2: Criar uma instância e injetar no AuthController**

Substituir a linha:

```python
    auth = AuthController()
```

por:

```python
    gatehouse = GatehouseClient()
    auth = AuthController(gatehouse)
```

- [ ] **Step 3: Reescrever `handle_test_connection` para usar o cliente**

Substituir o bloco atual:

```python
    def handle_test_connection():
        import requests
        url = f"{config.get_server_base_url()}{config.ACCESS_PATH}"
        try:
            resp = requests.post(url, json={"tag_code": "__test__"},
                                 timeout=config.SERVER_TIMEOUT)
            return True, f"Conectado a {url} (HTTP {resp.status_code})"
        except Exception as exc:
            return False, f"Falha ao conectar em {url}: {exc}"
```

por:

```python
    def handle_test_connection():
        r = gatehouse.post_access("__test__")
        if r.reachable:
            return True, f"Conectado a {config.get_server_base_url()} (HTTP {r.status_code})"
        return False, f"Falha ao conectar: {r.error}"
```

- [ ] **Step 4: Verificar — suíte completa + boot smoke**

Run: `venv/bin/pytest -q`
Expected: PASS (todos; a suíte cresce com os testes do cliente).

Boot headless mock (não deve ter traceback):
```bash
MOCK_HARDWARE=true HEADLESS=true venv/bin/python main.py > /tmp/gate_boot3.log 2>&1 &
sleep 2 && kill %1
grep -q "Rodando em modo HEADLESS" /tmp/gate_boot3.log && echo "BOOT OK" || (cat /tmp/gate_boot3.log; echo "BOOT FALHOU")
```
Expected: `BOOT OK`.

Confirmar que `main.py` não faz mais POST manual:
`grep -n "requests" main.py` → Expected: sem resultados (o `import requests` interno saiu).

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "refactor: main injeta GatehouseClient e reusa no Testar conexão

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notas de verificação final

- Suíte completa verde: `venv/bin/pytest -v`.
- Nenhuma chamada `requests` fora de `clients/gatehouse_client.py`:
  `grep -rn "requests" --include=*.py . | grep -v venv/ | grep -v tests/` → só `clients/gatehouse_client.py`.
- App sobe headless sem erros; comportamento de autorização idêntico (mensagens preservadas).
- `config.py`, GUI e `commands/*` intocados.
