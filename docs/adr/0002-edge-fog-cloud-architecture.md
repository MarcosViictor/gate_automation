# Arquitetura de comunicação — sistema de portarias (edge / fog / cloud)

## 1. Visão geral

```
Nuvem (multi-tenant, multi-site)
   |  sync bidirecional (config desce, eventos sobem)
Fog local (um por portaria, site_id fixo)
   |  autenticação por serial + token
Raspberry Pi (edge, um ou mais por portaria, por role)
```

Cada camada só conhece o necessário sobre a de baixo — nunca o inverso além do mínimo:
- O **Pi** sabe: endereço do fog + seu próprio serial + token recebido.
- O **fog** sabe: todos os devices pareados dele, seu próprio `site_id`, e credencial própria pra falar com a nuvem.
- A **nuvem** sabe: todos os tenants, sites e fogs, e a visão agregada de tudo.

---

## 2. Identidade hierárquica

| Nível | Identificador | Como é definido |
|---|---|---|
| Tenant | `tenant_id` | Cadastro do cliente na nuvem |
| Site (portaria) | `site_id` | Cadastro do site na nuvem, vinculado a um fog |
| Fog | `fog_id` + API key | Provisionado na instalação, credencial própria |
| Device (Pi) | `serial` (hardware) + `token` | Serial é de fábrica; token é gerado no primeiro registro |

**Regra de ouro:** nenhuma camada aceita um identificador "auto-declarado" no corpo da requisição. Toda identidade usada pra filtrar dados vem da **credencial autenticada** de quem está chamando (header `Authorization`), nunca de um campo tipo `{"site_id": "..."}` enviado por quem pergunta.

---

## 3. Modelo de dados

### No fog local (banco por portaria)

```sql
CREATE TABLE devices (
    id UUID PRIMARY KEY,
    serial TEXT UNIQUE NOT NULL,      -- serial de fábrica do Pi
    role TEXT NOT NULL,               -- 'entrada_veiculo', 'saida_veiculo', 'leitor_pedestre'
    token_hash TEXT NOT NULL,         -- nunca salvar token puro
    status TEXT NOT NULL DEFAULT 'active',  -- active | revoked
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE autorizados (
    id UUID PRIMARY KEY,
    identificador TEXT NOT NULL,      -- placa, cartão RFID, etc.
    tipo TEXT NOT NULL,               -- 'veiculo', 'pedestre'
    synced_at TIMESTAMP               -- controle de sync incremental
);

CREATE TABLE eventos (
    id UUID PRIMARY KEY,
    device_id UUID REFERENCES devices(id),
    tipo TEXT NOT NULL,
    identificador TEXT,
    timestamp TIMESTAMP DEFAULT now(),
    synced_to_cloud BOOLEAN DEFAULT false
);
```

### Na nuvem (multi-tenant)

```sql
CREATE TABLE sites (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    nome TEXT
);

CREATE TABLE fog_servers (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES sites(id),
    api_key_hash TEXT NOT NULL,
    status TEXT DEFAULT 'active'
);

CREATE TABLE veiculos (
    id UUID PRIMARY KEY,
    placa TEXT,
    tenant_id UUID NOT NULL
);

-- associação: qual veículo passa em qual portaria
CREATE TABLE veiculo_site (
    veiculo_id UUID REFERENCES veiculos(id),
    site_id UUID REFERENCES sites(id),
    PRIMARY KEY (veiculo_id, site_id)
);
```

---

## 4. Fluxo de pareamento (Pi → Fog)

1. Alguém cadastra o **serial** do Pi no fog antes (ou durante) a instalação, associando a um `role`.
2. Na tela de configuração do Pi, alguém digita o **IP do fog local** (isso é só endereço de rede, não identidade).
3. Pi liga, lê seu próprio serial (`/proc/cpuinfo` ou equivalente), chama:

```
POST /devices/register
Body: { "serial": "10000000abc123" }
```

4. Fog confere se o serial está cadastrado → gera token → salva hash → devolve token pro Pi.
5. Pi salva o token localmente. Todas as chamadas seguintes usam:

```
Authorization: Bearer <token>
```

**Troca de hardware:** se o Pi queimar, recadastra-se o novo serial no mesmo "slot" (mesmo `role`), revoga-se o token antigo, e o novo Pi se registra normalmente.

---

## 5. Endpoints — Pi ↔ Fog

| Endpoint | Direção | Função |
|---|---|---|
| `POST /devices/register` | Pi → Fog | Registro inicial via serial, retorna token |
| `POST /devices/{id}/heartbeat` | Pi → Fog | Confirma que está ativo |
| `POST /devices/{id}/events` | Pi → Fog | Envia evento (ex: placa lida) |
| `GET /devices/{id}/sync?since=<ts>` | Pi → Fog | Puxa lista de autorizados atualizada, filtrada por `role` |

O fog nunca aceita `site_id` vindo do Pi — a portaria já é implícita (um fog = uma portaria). O que o fog filtra por device é o **role**, não o site.

---

## 6. Endpoints — Fog ↔ Nuvem

| Endpoint | Direção | Função |
|---|---|---|
| `POST /sync/events` | Fog → Nuvem | Envia lote de eventos pendentes |
| `GET /sync/config?since=<ts>` | Fog → Nuvem | Puxa autorizados/regras atualizadas, filtrado por `site_id` |

A nuvem deriva `site_id` a partir da API key do fog (nunca de um campo enviado). Sync incremental por `since=<timestamp>` evita reprocessar tudo a cada chamada.

---

## 7. Isolamento de dados por portaria — exemplo prático

Cenário: carro `ABC-1234` só entra na Portaria Norte; `XYZ-5678` entra nas duas.

```sql
-- Quando o fog da Portaria Norte sincroniza (site_id = 's1', vindo da API key):
SELECT v.placa FROM veiculos v
JOIN veiculo_site vs ON v.id = vs.veiculo_id
WHERE vs.site_id = 's1';
-- Resultado: ABC-1234, XYZ-5678 (nunca QWE-9999)
```

O fog Norte salva isso no seu banco local. Quando um carro passa na cancela, o Pi manda a placa lida pro fog, que consulta **sua própria lista local já filtrada** — não precisa checar site de novo nesse momento.

---

## 8. Camadas de segurança

| Camada | Mecanismo |
|---|---|
| Pi → Fog | Token gerado no registro, hash salvo no fog, nunca token puro em texto |
| Fog → Nuvem | API key própria por fog, hash salvo na nuvem |
| Revogação | Trocar hardware = revogar token/key antigo, gerar novo |
| Auditoria | Logar IP de origem de cada chamada (não como identidade, só como rastro) |

---

## 9. Resiliência offline-first

- **Pi**: se tiver lógica local, mantém cache da lista de autorizados e fila de eventos pendentes.
- **Fog**: banco local próprio, nunca depende da nuvem pra decisão de acesso em tempo real. Sincroniza "quando der".
- **Nuvem cai** → fog continua operando com o cache que já tinha. Eventos ficam na fila até a nuvem voltar.
- **Fog cai** (numa arquitetura sem mini PC dedicado) → Pi precisa de autonomia própria (banco local leve) — ver seção de trade-offs no histórico da conversa se for essa a rota escolhida.

---

## 10. Decisões em aberto / próximos passos sugeridos

- [ ] Definir se cada portaria terá mini PC dedicado (fog local) ou fog central com VPN — depende de distância física e orçamento.
- [ ] Escolher stack do fog (sugestão: FastAPI + SQLite, leve o suficiente pra rodar até num Pi mais robusto).
- [ ] Desenhar a tela de configuração do Pi (IP do fog) e o painel de cadastro de serial no fog.
- [ ] Definir política de rotação/expiração de token.
- [ ] Implementar sync incremental (`since=timestamp`) desde o MVP, pra não precisar refatorar depois.
