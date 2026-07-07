# Abertura remota do portão — endpoint `/open` no Pi (Design)

Data: 2026-07-06
Branch: `prototip_01`
Contraparte: sb-gatehouse SBS-4305 (botão "Abrir portão" → push ao Pi)

## Contexto

Hoje o Pi (`gate_automation`) é um **cliente HTTP puro**: só faz requisições de saída ao
servidor e não escuta nenhuma porta. A abertura manual (SBS-4305) é o caminho inverso — um
operador clica "Abrir portão" no dashboard do gatehouse e o servidor faz um **push** para o
Pi abrir. Para receber isso, o Pi passa a **escutar** um endpoint HTTP leve, que aciona o
**mesmo** acionamento de relé já existente (`GateController.open()`).

Direção e endereçamento (decididos junto ao SBS-4305): **push por IP fixo**; o gatehouse
guarda `RASPBERRY_HOST=<ip>:8080` e faz `POST /open`.

## Contrato (espelha o SBS-4305)

### `POST /open` — comanda a abertura
```
 
```
| Status | Body | Significado |
|---|---|---|
| `200` | `{"opened": true}` | Comando aceito, pulso disparado (≠ confirmação física) |
| `401` | `{"error": "unauthorized"}` | Segredo exigido e ausente/incorreto |
| `404` | — | Rota ou método desconhecido |

O gatehouse trata qualquer 2xx como sucesso; timeout/não-2xx → `GateOpenException` no lado dele.

### `GET /health` — sonda de disponibilidade
```
GET http://{RASPBERRY_HOST}/health       # sem autenticação
→ 200 {"status": "ok"}
```
Permite ao gatehouse checar se o Pi está no ar antes de habilitar o botão.

## Componentes

### Novo: `server/gate_server.py`

Pacote novo `server/`. Usa apenas a **stdlib** (`http.server.ThreadingHTTPServer` +
`BaseHTTPRequestHandler`), sem dependência nova. Roda numa thread daemon.

```python
class GateServer:
    def __init__(self, on_open: Callable[[], None], port: int, token: str = ""):
        ...
    def start(self) -> None:  # sobe o ThreadingHTTPServer numa thread daemon
        ...
    def stop(self) -> None:   # shutdown() + server_close()
        ...
```

- Escuta em `0.0.0.0:{port}`.
- O handler lê `on_open` e `token` a partir da instância do servidor (atributos setados no
  `start`), e roteia:
  - `POST /open`:
    - se `token` não vazio e o header `Authorization` != `token` → **401** `{"error":"unauthorized"}` (não chama `on_open`);
    - senão: lê o body JSON (se houver), loga a `portaria` quando presente, chama `on_open()` → **200** `{"opened": true}`;
  - `GET /health` → **200** `{"status": "ok"}` (sem checagem de token);
  - qualquer outra rota/método → **404**.
- Responde rápido: `on_open()` (que chama `gate.open()`) dispara o pulso numa thread e
  retorna na hora, então o `200` volta bem dentro do timeout de 5s do gatehouse.

Responsabilidade única: falar HTTP e chamar o callback. Não conhece relé nem GUI.

### Alterado: `config.py`

Dois novos valores (lidos do `.env`):
```python
GATE_LISTEN_PORT = int(os.getenv("GATE_LISTEN_PORT", "8080"))
GATE_OPEN_TOKEN = os.getenv("GATE_OPEN_TOKEN", "")  # vazio = sem autenticação
```

### Alterado: `main.py`

Cria o `GateServer`, sobe junto com os leitores e para no `finally`. O handler aciona o
relé e (se a GUI estiver aberta) mostra a abertura na tela:
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

gate_server = GateServer(handle_remote_open, config.GATE_LISTEN_PORT, config.GATE_OPEN_TOKEN)
gate_server.start()
...
# no finally:
gate_server.stop()
```

`AccessDecision` já existe (reusado só para pintar a linha na UI). Em modo headless (`app is
None`), a abertura remota apenas loga.

### Intocado: `commands/gate_controller.py`

O `GateController.open()` (que já dispara o ciclo de abertura + fechamento ativo, com guarda
`_is_active` contra comandos concorrentes) é reusado como está. **Sem rename** para `pulse()`:
`open()` inicia um ciclo completo (abre → aguarda → fecha), não um pulso — `pulse()` seria um
nome mais enganoso. Nenhuma mudança no relé/GPIO.

> Nota: se uma abertura remota chegar enquanto um ciclo já está ativo, o `GateController`
> ignora (loga um warning) e o Pi ainda responde `200` (comando aceito). Aceitável para este
> escopo — confirmação física fica para a Fase 2 (sensor), fora deste ticket.

## Fluxo de dados

```
Operador clica "Abrir portão" no gatehouse
  → POST http://{RASPBERRY_HOST}/open  (Authorization se configurado, body {portaria})
    → GateServer valida token (se houver)
      ├─ token inválido → 401
      └─ ok → handle_remote_open()
                → gate.open()          (relé: ciclo abre→fecha)
                → UI("ABERTURA REMOTA", portão aberto)   [se GUI]
                → 200 {"opened": true}
```

## Tratamento de erros

- Token exigido e header ausente/incorreto → `401`, sem acionar o relé.
- Rota/método desconhecido → `404`.
- Body ausente ou não-JSON → tratado como sem `portaria` (não é erro; a `portaria` é
  meramente informativa para o log).
- Exceção inesperada ao processar → `500` (o gatehouse trata como falha).

## Segurança

- Autenticação **opcional** por token no header `Authorization`, lida de `GATE_OPEN_TOKEN`.
  Default vazio = sem auth (decisão atual do protótipo). Quando os dois lados configurarem o
  mesmo segredo, o Pi passa a exigir — sem mudança de código.
- O servidor liga em `0.0.0.0:8080`; com token vazio, qualquer host na LAN que conheça
  `ip:8080` consegue abrir o portão. Risco aceito no protótipo; mitigável ligando o token.

## Testes

`tests/test_gate_server.py` — sobe o `GateServer` numa porta efêmera (`port=0`) e faz
requisições HTTP reais:
- `POST /open` sem token → `on_open` é chamado, `200` com `{"opened": true}`.
- `POST /open` com token configurado + `Authorization` correto → `200`, `on_open` chamado.
- `POST /open` com token configurado + header errado/ausente → `401`, `on_open` NÃO chamado.
- `POST /open` com body `{"portaria": 1}` → aceito, `200`.
- `GET /health` → `200` com `{"status": "ok"}`.
- `GET /open` ou `POST /rota-errada` → `404`.

(`on_open` é injetado como um callback fake que registra as chamadas — sem relé real.)

## Fora de escopo

- O botão, o `ManualGateService`, o `AccessRecord` e a config `RASPBERRY_*` — tudo do lado do
  gatehouse (SBS-4305).
- Confirmação física de abertura (sensor de portão) — Fase 2.
- Qualquer mudança no relé/GPIO ou no fluxo de tag.

## Peso

Zero dependência nova (stdlib). 1 classe (`GateServer`) + 2 configs + fiação no `main`.
`GateController`, leitores, camada cliente e GUI: intocados (a GUI só ganha uma linha de
feedback reusando `AccessDecision`).
