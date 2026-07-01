# Design: Integração do Sensor Ultrassônico JSN-SR04T (Fechamento Ativo)

## Overview
Integração do sensor ultrassônico JSN-SR04T (à prova d'água) no projeto `gate_automation` para garantir o fechamento ativo e seguro do portão pelo Raspberry Pi, prevenindo que o portão se feche prematuramente enquanto um veículo estiver passando ou permaneça aberto desnecessariamente após a passagem.

## 1. Configurações (`config.py`)
Novas variáveis de ambiente/configuração no `config.py` para abstrair os detalhes do hardware:
- `ULTRASONIC_TRIGGER_PIN`: GPIO utilizado para disparar o pulso (Trigger).
- `ULTRASONIC_ECHO_PIN`: GPIO utilizado para receber o retorno (Echo).
- `ULTRASONIC_PRESENCE_THRESHOLD`: Distância em metros (ex: `< 1.5m`) abaixo da qual o sistema considera um veículo como "presente".
- `GATE_SAFE_CLOSE_DELAY`: Tempo (em segundos) que o sistema aguardará para enviar o comando de fechamento após a detecção de saída completa do veículo.
- `GATE_FALLBACK_TIMEOUT`: Tempo de segurança máximo (em segundos, ex: 120s) em que o portão pode ficar aberto sem detectar um veículo antes de forçar o fechamento automático (caso o sensor não detecte nada).

## 2. Componente de Hardware (`commands/ultrasonic_sensor.py`)
Uma classe `UltrasonicSensor` independente para gerenciar a interação de baixo nível com o pino Trigger/Echo.
- **Média Móvel**: Em vez de reagir a cada pulso (o que pode ser falso positivo por conta de chuva ou vento), a classe lerá várias vezes a distância. Um obstáculo só será confirmado se persistir através do cálculo da média móvel.

## 3. Máquina de Estados no Fluxo do Portão (`commands/gate_controller.py`)
A integração da classe do sensor no controle do relé será baseada em 3 fases após a abertura do portão:
1. **Aguardando Carro (Fase 1)**: Portão abre. Sensor livre.
2. **Carro Passando (Fase 2)**: Distância cai (veículo detectado embaixo).
3. **Passagem Concluída (Fase 3)**: Distância volta a subir (veículo saiu). O portão agora aguarda o `GATE_SAFE_CLOSE_DELAY` e aciona o relé para fechar imediatamente.

## 4. Tratamento de Erros e Fallback de Segurança
- **Desistência:** Se o sistema estiver na Fase 1 e o tempo `GATE_FALLBACK_TIMEOUT` for atingido sem nenhum veículo passar, o portão efetuará uma leitura final do sensor para garantir que está livre, e então se fechará.
- **Falha Crítica do Hardware:** Se a rotina de detecção sofrer *timeout* constante lendo o sensor (indicando rompimento de cabo ou problema no GPIO), o sistema reporta o erro nos logs e transita para um fallback conservador puro de tempo para o fechamento.
