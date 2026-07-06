# Camada de Comunicação — GatehouseClient (Design)

Data: 2026-07-06
Branch: `prototip_01`

## Contexto

Hoje a comunicação do Pi com o servidor local (sb-gatehouse) está espalhada e duplicada:
a montagem da URL e o `requests.post` aparecem em `controllers/auth_controller.py` (validação
de tag) **e** em `main.py` (`handle_test_connection`, o botão "Testar conexão"). Não há uma
camada de transporte isolada, e testar o `AuthController` exige `monkeypatch` em `requests`.

Este design cria uma camada de comunicação **leve** — um único cliente HTTP — que centraliza
essas chamadas. Escopo escolhido: **só o cliente único** (sem retry, sem cache, sem auditoria
local). Sem dependências novas.

## Princípio

**Separar transporte de domínio.** O cliente (`GatehouseClient`) sabe apenas falar HTTP com o
sb-gatehouse e devolve uma resposta neutra. O `AuthController` continua dono da regra de
domínio ("isso é autorizado?"), consumindo o cliente. É um refactor puro: contrato de rede,
comportamento e mensagens permanecem idênticos aos atuais.

## Componentes

### Novo: `clients/gatehouse_client.py`

Pacote novo `clients/` (espelha o padrão `Catalog/Clients` do próprio sb-gatehouse).

```python
@dataclass
class GatehouseResponse:
    reachable: bool          # conseguiu conectar ao servidor?
    status_code: int | None  # None se não conectou
    data: dict | None        # JSON parseado, só quando 200 E o corpo é um objeto
    error: str | None        # mensagem do erro de transporte (quando reachable=False)


class GatehouseClient:
    def __init__(self, base_url=None, timeout=None, session=None):
        # base_url e timeout são CALLABLES lidos a cada chamada, para que
        # mudanças de IP/porta salvas pela GUI valham sem reiniciar.
        self._base_url = base_url or config.get_server_base_url
        self._timeout = timeout or (lambda: config.SERVER_TIMEOUT)
        self._session = session or requests

    def post_access(self, tag_code: str) -> GatehouseResponse:
        url = f"{self._base_url()}{config.ACCESS_PATH}"
        try:
            resp = self._session.post(url, json={"tag_code": tag_code}, timeout=self._timeout())
        except Exception as exc:
            logger.warning("Servidor inacessível ao chamar %s: %s", url, exc)
            return GatehouseResponse(reachable=False, status_code=None, data=None, error=str(exc))

        data = None
        if resp.status_code == 200:
            try:
                parsed = resp.json()
                if isinstance(parsed, dict):
                    data = parsed
            except ValueError:
                data = None
        return GatehouseResponse(reachable=True, status_code=resp.status_code, data=data, error=None)
```

Responsabilidade única: montar a URL, fazer o POST, tratar exceção/parse. Não conhece
`AccessDecision` nem a semântica de "autorizado".

### Alterado: `controllers/auth_controller.py`

Recebe o cliente por injeção e passa a **mapear** a resposta neutra para o domínio. Mesmas
mensagens e mesma distinção `online`/`authorized` de hoje.

```python
class AuthController:
    def __init__(self, client: GatehouseClient | None = None):
        self._client = client or GatehouseClient()

    def check(self, tag_code: str, direction: str = "IN") -> AccessDecision:
        r = self._client.post_access(tag_code)
        if not r.reachable:
            return AccessDecision(False, tag_code, direction, "Servidor inacessível", online=False)
        if r.status_code != 200:
            return AccessDecision(False, tag_code, direction, f"Servidor respondeu {r.status_code}", online=True)
        if r.data is None:
            return AccessDecision(False, tag_code, direction, "Resposta inválida do servidor", online=True)
        authorized = bool(r.data.get("open"))
        reason = r.data.get("reason") or ("Acesso liberado" if authorized else "Acesso negado")
        return AccessDecision(authorized, tag_code, direction, reason, online=True)
```

`AccessDecision` (dataclass) permanece inalterado. `import requests` sai deste arquivo.

### Alterado: `main.py`

Cria **uma** instância do cliente e injeta no `AuthController`; o botão "Testar conexão" passa
a usar o mesmo cliente (some o POST manual duplicado).

```python
gatehouse = GatehouseClient()
auth = AuthController(gatehouse)
...
def handle_test_connection():
    r = gatehouse.post_access("__test__")
    if r.reachable:
        return True, f"Conectado a {config.get_server_base_url()} (HTTP {r.status_code})"
    return False, f"Falha ao conectar: {r.error}"
```

## Fluxo de dados

```
handle_tag(tag, dir)
  → AuthController.check(tag)
      → GatehouseClient.post_access(tag)   [transporte: POST /api/raspberry/access]
      ← GatehouseResponse(reachable, status_code, data, error)
  ← AccessDecision(authorized, reason, online)   [domínio]
```

## Tratamento de erros (inalterado no comportamento)

| Situação | GatehouseResponse | AccessDecision |
|---|---|---|
| timeout / conexão recusada | reachable=False | negado, online=False, "Servidor inacessível" |
| status ≠ 200 | reachable=True, data=None | negado, online=True, "Servidor respondeu {n}" |
| 200, JSON inválido/não-objeto | reachable=True, data=None | negado, online=True, "Resposta inválida do servidor" |
| 200, `{"open": true}` | reachable=True, data={...} | autorizado, online=True |

## Testes

- **Novo `tests/test_gatehouse_client.py`:** exercita `post_access` contra um servidor-stub HTTP
  real (mesmo padrão de `test_integration_access.py`): allowed (200 dict), non-200, e offline
  (porta sem listener → reachable=False).
- **`tests/test_auth_controller.py` reescrito:** injeta um `FakeGatehouseClient` que devolve
  `GatehouseResponse` prontos, cobrindo os 4 caminhos da tabela acima. Elimina o `monkeypatch`
  em `requests`.
- **`tests/test_integration_access.py`:** mantido — agora valida o caminho completo
  `AuthController → GatehouseClient → servidor real`.

## Fora de escopo (decidido)

- Retry, cache de decisões, e trilha de auditoria local — não entram nesta camada.
- O "Testar conexão" continua enviando a tag `"__test__"` ao mesmo endpoint (gera um registro
  "negado" no log do sb-gatehouse). Comportamento atual mantido; alternativa fica para depois.
- `config.py`, a GUI (`views/main_window.py`) e toda a parte física: intocados.

## Peso

Zero dependências novas (reusa `requests`). 1 classe + 1 dataclass (~40 linhas). O resto é
mover código existente para trás da nova fronteira.
