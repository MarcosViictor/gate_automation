# SPEC: Deteccao de Estado do Portao com 2 Sensores Hall

## Status
Draft

## Objetivo
Implementar a deteccao do estado fisico do portao usando dois sensores Hall NPN NJK-5002C instalados em pontos distintos do curso do mecanismo.

O sistema deve distinguir tres estados:

* `ABERTO`
* `FECHADO`
* `EM_ANDAMENTO`

A deteccao deve complementar o acionamento atual do rele, que hoje envia apenas o pulso de abertura/fechamento, sem confirmar a posicao fisica real do portao.

## Contexto do Projeto
O projeto roda em um Raspberry Pi e ja possui:

* `commands/gate_controller.py`: aciona o rele do portao.
* `main.py`: orquestra leitores RFID, autorizacao, sincronizacao, UI e temporizador de fechamento.
* `config.py`: centraliza configuracoes de GPIO, RFID, mock e intervalos.
* `views/main_window.py`: exibe o estado visual atual do portao, hoje baseado em eventos de software.

Esta spec define uma camada nova de monitoramento fisico do portao. A UI e os logs devem passar a refletir o estado lido dos sensores sempre que esse monitor estiver ativo.

## Hardware Alvo
* Raspberry Pi 3 Model B.
* Dois sensores Hall NPN NJK-5002C.
* Biblioteca Python de GPIO: `RPi.GPIO`.

## Mapeamento Eletrico
Os sensores NJK-5002C possuem saida NPN coletor aberto. Com pull-up no GPIO:

* Ima presente / sensor ativo: GPIO em nivel `LOW`.
* Ima ausente / sensor inativo: GPIO em nivel `HIGH`.

Pinos sugeridos:

| Sensor | GPIO BCM | Pino fisico | Funcao |
|---|---:|---:|---|
| Sensor A | 17 | 11 | Entrada digital com pull-up |
| Sensor B | 27 | 13 | Entrada digital com pull-up |

Ligacao sugerida:

```text
Sensor A (NJK-5002C)              Raspberry Pi 3B
-----------------------           -----------------
Marrom (V+)   -----> Fonte externa (+)
Azul (GND)    -----> GND comum
Preto (OUT)   -----> GPIO 17 (BCM), pull-up interno

Sensor B (NJK-5002C)
-----------------------
Marrom (V+)   -----> Fonte externa (+)
Azul (GND)    -----> GND comum
Preto (OUT)   -----> GPIO 27 (BCM), pull-up interno
```

## Cuidados Eletricos
Antes da implementacao final em hardware real:

* Confirmar a tensao de alimentacao dos sensores adquiridos na etiqueta ou datasheet.
* Se os sensores forem alimentados com tensao diferente de nivel seguro para GPIO do Raspberry Pi, usar optoacoplador, por exemplo PC817, ou level shifter.
* O GND da fonte dos sensores deve ser comum ao GND do Raspberry Pi quando a ligacao eletrica exigir referencia comum.
* Usar pull-up interno via `GPIO.PUD_UP` inicialmente.
* Em ambiente com ruido eletrico, avaliar resistor externo de pull-up de 10 kOhm e ajustes de debounce.

## Regra de Negocio
Tabela verdade:

| Sensor A | Sensor B | GPIO A | GPIO B | Estado |
|---|---|---|---|---|
| Ativo | Inativo | LOW | HIGH | `ABERTO` |
| Inativo | Ativo | HIGH | LOW | `ABERTO` |
| Ativo | Ativo | LOW | LOW | `FECHADO` |
| Inativo | Inativo | HIGH | HIGH | `EM_ANDAMENTO` |

Observacao: a regra considera que qualquer um dos dois sensores ativo isoladamente representa o estado aberto. Ambos ativos representam fechado. Ambos inativos representam movimento ou posicao intermediaria.

## Configuracao Esperada
Adicionar configuracoes no `config.py`:

```python
GATE_SENSOR_A_PIN = 17
GATE_SENSOR_B_PIN = 27
GATE_STATE_POLL_INTERVAL = 0.05
GATE_STATE_DEBOUNCE_SECONDS = 0.02
GATE_MOVING_TIMEOUT_SECONDS = 30.0
GATE_PULSE_RESPONSE_SECONDS = 10.0
GATE_RETRY_COOLDOWN_SECONDS = 2.0
GATE_MAX_RETRY_ATTEMPTS = 3
GATE_PASSAGE_CONFIRMATION_SECONDS = 30.0
```

O monitor deve respeitar `MOCK_HARDWARE`:

* Em hardware real, ler GPIO.
* Em modo mock, permitir simular estados sem importar `RPi.GPIO`.

## Componente Proposto
Criar um componente dedicado, por exemplo:

```text
commands/gate_state_monitor.py
```

Responsabilidades:

* Configurar os pinos dos sensores como entrada com pull-up.
* Ler os dois GPIOs.
* Aplicar debounce.
* Determinar o estado conforme a tabela verdade.
* Manter o ultimo estado conhecido.
* Emitir callback ou log somente quando houver mudanca de estado.
* Permitir consulta pontual do estado atual.
* Encerrar de forma limpa com `GPIO.cleanup()` quando aplicavel.

API sugerida:

```python
class GateStateMonitor:
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def get_state(self) -> str:
        ...

    def set_mock_state(self, state: str) -> None:
        ...
```

Estados sugeridos como constantes:

```python
GATE_OPEN = "ABERTO"
GATE_CLOSED = "FECHADO"
GATE_MOVING = "EM_ANDAMENTO"
GATE_STUCK = "TRAVADO"
```

## Estrategia de Leitura
Usar polling simples em thread separada.

Parametros iniciais:

* Intervalo de polling: 50 ms.
* Debounce: 20 ms.
* Timeout em movimento: 30 s.

Fluxo:

1. Ler GPIO A e GPIO B.
2. Aguardar debounce.
3. Ler novamente.
4. Aceitar a leitura apenas se as duas leituras forem iguais.
5. Mapear a combinacao para `ABERTO`, `FECHADO` ou `EM_ANDAMENTO`.
6. Se o estado mudou, atualizar o estado interno e chamar o callback de mudanca.
7. Se o estado permanecer `EM_ANDAMENTO` por mais que o timeout configurado, registrar alerta.

## Controle de Atuador e Watchdog
O Raspberry Pi comanda o motor do portao por um pulso unico, como em centrais comuns de portao eletronico. Esse pulso nao define diretamente a direcao; ele alterna o comportamento da central conforme o estado interno dela, por exemplo: abre, para, fecha, para, abre.

Por isso, o sistema deve sempre enviar um pulso, aguardar a resposta mecanica e entao descobrir o resultado real pela leitura dos sensores Hall.

### Arquitetura de Controle
* Saida de comando: `PULSO_PORTAO`, hoje representada pelo GPIO de rele do `GateController`.
* Cada pulso e generico; o efeito real pode ser abrir, fechar ou parar.
* A decisao final sempre depende da leitura posterior dos sensores.
* O sistema deve manter uma flag `comando_ativo_pelo_sistema` para distinguir comandos proprios de movimentos externos.

### Fluxo de Comando
1. Receber necessidade de comando, por exemplo liberar acesso ou tratar portao travado no meio.
2. Enviar um pulso em `PULSO_PORTAO`.
3. Marcar `comando_ativo_pelo_sistema = True`.
4. Aguardar `GATE_PULSE_RESPONSE_SECONDS`.
5. Ler os sensores com debounce.
6. Mapear o resultado usando a tabela verdade.
7. Decidir a proxima acao conforme a leitura.
8. Encerrar o comando ou aplicar watchdog/retentativa.

### Decisao Pos-Pulso
| Resultado da leitura | Acao |
|---|---|
| `FECHADO` | Enviar novo pulso para reabrir o portao quando a intencao original era liberar acesso. |
| `ABERTO` | Manter o portao aberto e aguardar confirmacao de passagem ou temporizador de fechamento. |
| `EM_ANDAMENTO` | Aplicar watchdog: verificar timeout, cooldown e contador de tentativas. |

Se o resultado continuar `EM_ANDAMENTO` depois do tempo de resposta:

1. Verificar se `GATE_MAX_RETRY_ATTEMPTS` ja foi atingido.
2. Se nao foi atingido, aguardar `GATE_RETRY_COOLDOWN_SECONDS`.
3. Enviar novo pulso.
4. Incrementar o contador de tentativas.
5. Repetir leitura apos `GATE_PULSE_RESPONSE_SECONDS`.
6. Se o limite foi atingido, parar de enviar pulsos, marcar `TRAVADO` e disparar alerta.

### Estado TRAVADO
O estado `TRAVADO` representa falha operacional: o portao excedeu o tempo e o numero maximo de tentativas sem chegar a um estado estavel.

Ao entrar em `TRAVADO`:

* O sistema nao deve tentar novos pulsos sozinho.
* Deve registrar alerta visivel em log.
* Pode acionar LED, buzzer ou notificacao remota em uma evolucao futura.
* Deve exigir intervencao manual ou novo comando explicito para resetar a condicao.

### Regras de Seguranca
* Nunca enviar pulsos em sequencia rapida sem aguardar `GATE_PULSE_RESPONSE_SECONDS`.
* Limitar retentativas com `GATE_MAX_RETRY_ATTEMPTS`.
* Nao insistir em pulsos depois de entrar em `TRAVADO`.
* Antes de cada pulso, reler sensores com debounce.
* Se o resultado do pulso for inesperado, considerar interferencia externa antes de insistir em novas tentativas.
* Se houver risco de esmagamento, adicionar sensor de seguranca apropriado antes de habilitar qualquer retentativa automatica.

## Deteccao de Movimento Externo
O portao pode ser operado por controle remoto, botoeira ou pela propria central, fora do controle do Raspberry Pi.

Para evitar correcoes indevidas:

1. Manter a flag `comando_ativo_pelo_sistema`.
2. Setar `True` apenas quando o sistema envia pulso.
3. Setar `False` quando o comando termina ou quando o watchdog desiste.
4. Se uma mudanca de estado ocorrer enquanto `comando_ativo_pelo_sistema` for `False`, registrar `movimento externo detectado`.
5. Nao acionar watchdog nem retentativa para movimento externo.

## Reconciliacao de Acesso e Passagem
Uma tag lida e autorizada nao garante que o veiculo passou pelo portao. Para auditoria, o evento de acesso deve ter um desfecho.

Este fluxo exige um sensor dedicado de presenca/passagem de veiculo, independente dos sensores Hall de posicao do portao, como laco indutivo ou barreira infravermelha.

Fluxo esperado:

1. Tag lida e autorizada cria evento com status `AGUARDANDO_PASSAGEM`.
2. Se o portao nao estiver `ABERTO`, o sistema envia comando de abertura pelo fluxo de pulso unico.
3. Quando o portao estiver `ABERTO`, iniciar janela de confirmacao de passagem.
4. Se o sensor de passagem disparar dentro de `GATE_PASSAGE_CONFIRMATION_SECONDS`, marcar `PASSAGEM_CONFIRMADA`.
5. Se a janela expirar sem sensor de passagem, marcar `PASSAGEM_NAO_CONFIRMADA` para revisao.

Este fluxo e independente da deteccao de posicao do portao. A pendencia aqui e sobre a confirmacao de passagem do veiculo, nao sobre o estado mecanico.

## Integracao com a Aplicacao
O `main.py` deve iniciar o monitor junto com os demais servicos de background.

Quando o estado fisico mudar:

* Atualizar a UI via `app.after(...)`, se a UI estiver ativa.
* Registrar log de mudanca de estado no logger da aplicacao.
* Evitar spam de logs repetidos para o mesmo estado.

A funcao atual `MainWindow.update_gate_status(is_open: bool)` aceita apenas aberto/fechado. Ela deve evoluir para aceitar os estados fisicos e operacionais do portao, por exemplo:

```python
update_gate_status(state: str)
```

Mapeamento visual sugerido:

| Estado | Texto na UI | Estilo sugerido |
|---|---|---|
| `ABERTO` | `PORTAO ABERTO` | sucesso |
| `FECHADO` | `PORTAO FECHADO` | neutro |
| `EM_ANDAMENTO` | `PORTAO EM ANDAMENTO` | alerta |
| `TRAVADO` | `PORTAO TRAVADO` | erro |

Enquanto o monitor fisico estiver ativo, o estado visual nao deve depender apenas do temporizador de software.

## Relacao com o Temporizador de Fechamento
O temporizador atual envia um novo pulso apos 90 segundos para fechar o portao. Com sensores fisicos:

* O temporizador ainda pode existir como regra operacional.
* A confirmacao visual de fechamento deve vir dos sensores.
* Se o pulso de fechamento for enviado, o sistema deve aguardar `GATE_PULSE_RESPONSE_SECONDS` e reler sensores antes de decidir nova acao.
* Se o estado permanecer `EM_ANDAMENTO`, o watchdog de pulso unico deve controlar cooldown, retentativas e eventual estado `TRAVADO`.
* Se o estado chegar em `FECHADO`, o sistema pode limpar qualquer estado visual pendente de abertura.

## Logs
Eventos minimos esperados:

```text
Estado fisico do portao alterado: ABERTO
Estado fisico do portao alterado: EM_ANDAMENTO
Estado fisico do portao alterado: FECHADO
Estado fisico do portao alterado: TRAVADO
Portao permaneceu EM_ANDAMENTO por mais de 30.0 segundos
Pulso enviado pelo sistema; aguardando resposta do portao
Retentativa de pulso 1/3 apos cooldown
Portao entrou em estado TRAVADO; intervencao manual necessaria
Movimento externo detectado
Passagem confirmada
Passagem nao confirmada dentro da janela configurada
```

O historico em banco de dados ou arquivo CSV fica fora do escopo inicial, mas pode ser adicionado depois.

## Tratamento de Erros
* Se `RPi.GPIO` nao estiver disponivel e `MOCK_HARDWARE` for `false`, registrar erro claro.
* Se a configuracao de GPIO falhar, nao derrubar a aplicacao inteira; o RFID e a sincronizacao devem continuar rodando.
* `stop()` deve encerrar a thread de polling.
* `cleanup()` deve liberar os pinos quando aplicavel.
* O monitor nao deve chamar `GPIO.cleanup()` de forma que atrapalhe o `GateController` enquanto a aplicacao ainda estiver rodando.

## Testes Esperados
Testes unitarios:

* `LOW, HIGH` retorna `ABERTO`.
* `HIGH, LOW` retorna `ABERTO`.
* `LOW, LOW` retorna `FECHADO`.
* `HIGH, HIGH` retorna `EM_ANDAMENTO`.
* Estado repetido nao dispara callback duplicado.
* Mudanca de estado dispara callback uma vez.
* Timeout de `EM_ANDAMENTO` gera alerta uma vez por periodo de movimento.
* Watchdog envia no maximo `GATE_MAX_RETRY_ATTEMPTS` pulsos de retentativa.
* Estado `TRAVADO` bloqueia novas retentativas automaticas.
* Movimento externo nao aciona watchdog quando `comando_ativo_pelo_sistema` e `False`.
* Evento de acesso pode ser marcado como `PASSAGEM_CONFIRMADA`.
* Evento de acesso pode ser marcado como `PASSAGEM_NAO_CONFIRMADA`.

Testes manuais em hardware:

* Aproximar o ima de cada sensor individualmente.
* Aproximar o ima dos dois sensores ao mesmo tempo.
* Afastar o ima dos dois sensores.
* Simular ciclo completo: aberto -> em andamento -> fechado -> em andamento -> aberto.
* Deixar rodando por periodo prolongado para observar estabilidade e falsos positivos.

## Criterios de Aceite
* O projeto possui uma classe ou modulo dedicado para monitorar os dois sensores Hall.
* A tabela verdade desta spec esta coberta por testes automatizados.
* O monitor funciona em modo mock sem depender de Raspberry Pi.
* Em hardware real, os pinos sao configurados com pull-up interno.
* A aplicacao loga mudancas de estado apenas quando ha alteracao real.
* A UI consegue exibir `ABERTO`, `FECHADO`, `EM_ANDAMENTO` e `TRAVADO`.
* O sistema possui regra documentada para pulso unico, retentativa e portao travado.
* O watchdog nao gera loop infinito de acionamentos.
* Movimentos externos sao registrados sem acionar correcao automatica.
* O encerramento da aplicacao para leitores, sync, temporizadores, monitor e GPIO de forma limpa.

## Fora do Escopo Inicial
* Encoder ou medicao continua de posicao.
* MQTT.
* API REST local para consulta de estado.
* Persistencia historica em SQLite dos eventos de estado, exceto se for escolhida para eventos de passagem.
* Ajuste automatico de debounce.
* Diagnostico eletrico avancado de sensor quebrado, curto ou cabo rompido.

## Itens em Aberto
* Confirmar tensao real de alimentacao dos sensores instalados.
* Confirmar se sera usado optoacoplador ou level shifter.
* Confirmar pinos GPIO finais no Raspberry Pi instalado para sensores e rele.
* Confirmar se a central do portao realmente opera por pulso unico/toggle.
* Confirmar se sera necessario rele intermediario de contato seco entre Raspberry Pi e central do portao.
* Medir tempo real de abertura/fechamento para definir `GATE_PULSE_RESPONSE_SECONDS`.
* Definir valores finais de cooldown e maximo de tentativas.
* Definir como `TRAVADO` sera sinalizado alem do log.
* Definir modelo e interface do sensor de passagem de veiculo.
* Decidir se eventos de estado fisico devem ser gravados no banco local.
* Decidir se o servico systemd deve expor logs especificos para manutencao do portao.
