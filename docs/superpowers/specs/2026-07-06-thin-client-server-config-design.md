# Thin Client + Configuração do Servidor (prototip_01) — Design

Data: 2026-07-06
Branch: `prototip_01`

## Contexto

O projeto está pivotando de uma arquitetura **edge-heavy** (banco SQLite local +
sincronização em background) para **thin client**. O Raspberry Pi passa a ser um nó
puro de sensor/atuador: lê a tag RFID, pergunta em tempo real ao servidor local
(**sb-gatehouse**) se libera, e obedece a resposta acionando o relé. Nenhum estado é
mantido localmente.

A **ativação** (acionamento do relé, tempo/pulso, lógica de fechamento) **não muda** —
apenas a **fonte de validação** deixa de ser o banco local e passa a ser uma requisição
HTTP ao sistema local.

## Contrato do servidor (sb-gatehouse)

Verificado no código do sb-gatehouse (`routes/api.php`, `AccessController@store`):

- **Rota:** `POST {SERVER_BASE_URL}/api/raspberry/access`
- **Autenticação:** nenhuma (rota pública, fora do `auth:sanctum`)
- **Request:** `{"tag_code": "<código>"}` — o `portaria_id` é config **do servidor**, o Pi não envia
- **Response 200 (JSON):**
  ```json
  { "decision": "allowed" | "denied", "open": true | false, "reason": "<opcional>" }
  ```
- O Pi decide abrir com base no booleano `open`.

## Decisões

1. **Remoção total do banco local** e de tudo acoplado a ele.
2. **Fail-closed:** servidor inacessível / timeout / não-200 / JSON inválido → acesso **negado**.
3. **UI mínima de status** (o Pi roda headless em produção; a GUI é para quando há tela).
4. **Config persistida no `.env`** (fonte da verdade). A GUI é uma camada visual sobre o `.env`.
5. **Escape via código (sutil):** no provisionamento do Raspberry (headless), a config é feita
   editando o `.env` por SSH — como no gatehouse. Documentado via `.env.example`, sem poluir a UI.

## O que é removido

- `models/` inteiro: `database.py`, `tag.py`, `vehicle.py`, `driver.py`, `access_log.py`,
  `seed.py`, `schedule.py`, `__init__.py`.
- `controllers/sync_controller.py`.
- `data/gate_local.db`: apagado do disco, `git rm --cached`, e ignorado.
- Seed de dados e toda leitura/escrita `db.get_setting`/`set_setting` em `main.py` e na UI.
- `tests/test_database.py`, `tests/test_vehicle.py`, `tests/test_access_log.py`
  (testam models deletados).

## O que é mantido intacto

- `commands/gate_controller.py`, `commands/rfid_reader.py`, `commands/ultrasonic_sensor.py`.
- Todo o fluxo de acionamento do relé em `handle_tag` (chama `gate.open()` ao autorizar).

## Componentes alterados

### `config.py`

Servidor derivado de host + porta (env), montando a base URL. Rota fixa no código.

```python
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = os.getenv("SERVER_PORT", "8001")
SERVER_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
SERVER_TIMEOUT = int(os.getenv("SERVER_TIMEOUT", "5"))

RFID_PORT_IN = os.getenv("RFID_PORT_IN", "/dev/ttyUSB0")
RFID_PORT_OUT = os.getenv("RFID_PORT_OUT", "/dev/ttyUSB1")
```

Remove: `DB_PATH`, `SEED_TEST_DATA` e demais constantes ligadas ao banco.
Mantém: `update_env(key, value)` (grava no `.env` + atualiza `os.environ`) e as vars HID/mock.

A rota de acesso é fixa: `ACCESS_PATH = "/api/raspberry/access"`.

### `controllers/auth_controller.py` (reescrito)

Sem repositórios, sem log local. Lê host/porta a cada chamada (via `os.getenv`), para que
mudanças salvas pela GUI valham imediatamente sem reiniciar.

```python
@dataclass
class AccessDecision:
    authorized: bool
    tag_code: str
    direction: str = "IN"
    reason: str | None = None
    online: bool = False

class AuthController:
    def check(self, tag_code: str, direction: str = "IN") -> AccessDecision:
        base_url = f"http://{os.getenv('SERVER_HOST', config.SERVER_HOST)}:{os.getenv('SERVER_PORT', config.SERVER_PORT)}"
        url = f"{base_url}{config.ACCESS_PATH}"
        try:
            resp = requests.post(url, json={"tag_code": tag_code}, timeout=config.SERVER_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                return AccessDecision(bool(data.get("open")), tag_code, direction,
                                      data.get("reason"), online=True)
            return AccessDecision(False, tag_code, direction,
                                  f"Servidor respondeu {resp.status_code}", online=True)
        except Exception as e:
            logger.warning("Servidor inacessível ao checar tag %s: %s", tag_code, e)
            return AccessDecision(False, tag_code, direction, "Servidor inacessível", online=False)
```

### `main.py`

- Remove imports/uso de `models` e `SyncController`.
- Portas vêm de `config` (env), não do banco.
- `handle_tag(tag_code, direction)`:
  ```python
  result = auth.check(tag_code, direction)
  if result.authorized:
      gate.open()          # acionamento inalterado
  if app:
      app.after(0, lambda: [
          app.add_read_row(result),
          app.update_gate_status(result.authorized),
          app.update_net_status(result.online),
      ])
  ```
- Callback de salvar config: grava `.env` e reinicia leitores com as novas portas.

### `views/main_window.py` (reescrito, mínimo)

Sem `models`, sem `db`. Assinatura:
`MainWindow(on_save_config, on_mock_tag, on_test_connection, initial_config)`.

- **Aba Monitor:** status do portão, status de rede, lista em memória das últimas ~15 leituras
  (hora / tag / direção / decisão / motivo), simulador de tag ("Ler Tag").
- **Aba Configurações:**
  - IP do servidor → `SERVER_HOST`
  - Porta → `SERVER_PORT`
  - Leitor Entrada (IN) → `RFID_PORT_IN`
  - Leitor Saída (OUT) → `RFID_PORT_OUT`
  - Botão **Salvar** → grava no `.env` via `config.update_env` e reinicia leitores.
  - Botão **Testar conexão** → chama `on_test_connection` (POST de teste) e mostra ✅/❌.
- Métodos: `update_gate_status(bool)`, `update_net_status(bool)`, `add_read_row(AccessDecision)`.
- Remove abas Veículos/Tags e o botão "Sincronizar Agora".

### `.env.example` (novo — escape sutil)

```dotenv
# Endereço do servidor local (sb-gatehouse)
SERVER_HOST=localhost
SERVER_PORT=8001

# Portas dos leitores RFID
RFID_PORT_IN=/dev/ttyUSB0
RFID_PORT_OUT=/dev/ttyUSB1

# Hardware
MOCK_HARDWARE=false
RFID_MODE=hid
```

### `.gitignore`

Substituir o template AL/Business Central (irrelevante) por um `.gitignore` Python:
`venv/`, `__pycache__/`, `*.pyc`, `.env`, `data/*.db`.

## Fluxo de dados

```
Leitor RFID (IN/OUT) → handle_tag(tag, dir) → auth.check(tag, dir)
   → POST {SERVER_BASE_URL}/api/raspberry/access  {"tag_code": tag}
   → 200 {"open": true}   → gate.open()  + UI(portão aberto, rede online, linha de leitura)
   → 200 {"open": false}  → nega          + UI(negado, rede online)
   → erro/timeout/não-200 → nega (fail-closed) + UI(negado, rede offline)
```

## Tratamento de erros

- `requests` exception / timeout / `ConnectionError` → fail-closed, `online=False`, log warning.
- Status ≠ 200 → fail-closed, `online=True` (servidor respondeu, mas recusou/erro).
- JSON malformado → fail-closed, log warning.

## Testes

- **Unitários** (`tests/test_auth_controller.py`, `requests` mockado):
  - `open=true` → `authorized=True`, `online=True`.
  - `open=false` + `reason` → `authorized=False`, reason preservado.
  - `ConnectionError`/`Timeout` → `authorized=False`, `online=False` (fail-closed).
  - status 500 → `authorized=False`, `online=True`.
- **Verificação end-to-end:** stub HTTP local respondendo o contrato `{decision, open, reason}`;
  dirigir os 3 caminhos (allowed / denied / offline). Opcionalmente apontar `SERVER_HOST/PORT`
  para o sb-gatehouse real em `localhost:8001`.

## Trade-offs e riscos

- **Dependência de rede:** se a LAN entre Pi e servidor cair, o portão não abre (fail-closed).
  Aceito para este protótipo.
- **Latência:** ~<50ms em LAN, desprezível.
- **Sem auditoria local:** o registro de acessos passa a ser responsabilidade do sb-gatehouse.
```