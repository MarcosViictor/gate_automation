# Gate Automation

Aplicacao de automacao de portao com leitura de tags RFID, validacao local/offline e sincronizacao com servidor.

## Leitor RFID (Serial e HID)

O projeto agora suporta tres modos de leitura:

- `RFID_MODE=serial`: leitor por porta serial (`/dev/ttyUSB0`, etc.)
- `RFID_MODE=hid`: leitor USB HID (leitura por bytes, como no script base)
- `RFID_MODE=auto`: tenta HID primeiro e depois serial

### Variaveis de ambiente

Exemplo para Linux com leitor HID:

```bash
export MOCK_HARDWARE=false
export RFID_MODE=hid
export RFID_HID_VENDOR_ID=0x1234
export RFID_HID_PRODUCT_ID=0x5678
export RFID_HID_INTERFACE_NUMBER=
export RFID_HID_OFFSET=18
export RFID_HID_STRIP_HEX_DIGITS=4
python main.py
```

Observacoes:

- `RFID_HID_OFFSET` pode variar por leitor/OS. Se o codigo sair incorreto, teste `17`, `18` ou `19`.
- `RFID_HID_STRIP_HEX_DIGITS` remove sufixo no final da tag (checksum/padding). O padrao e `4`.
- Se nao quiser filtrar dispositivo HID por VID/PID, deixe `RFID_HID_VENDOR_ID` e `RFID_HID_PRODUCT_ID` vazios.
- Se houver multiplas interfaces HID no mesmo dispositivo, use `RFID_HID_INTERFACE_NUMBER` para fixar a interface correta.
- O leitor agora tenta automaticamente offsets `17`, `18` e `19` (alem do offset configurado).

Configuracoes avancadas (opcionais):

- `RFID_HID_USAGE_PAGE` e `RFID_HID_USAGE`: filtros extras para selecionar a interface HID correta.
- `RFID_HID_INTERFACE_IDLE_SECONDS`: tempo sem dados para trocar automaticamente para a proxima interface HID candidata.
- `RFID_HID_LOG_ENUMERATION`: quando `true`, mostra no log as interfaces HID candidatas encontradas.

Para descobrir VID/PID no Linux:

```bash
lsusb
```

### Dependencias

Instale as dependencias:

```bash
pip install -r requirements.txt
```

## Dados de teste (mock)

Quando `SEED_TEST_DATA=true` (padrao quando `MOCK_HARDWARE=true`), o app prepara dados locais para validar autorizacao:

- Tag liberada: `01000000000000000000000158`
- Tag inativa (negada): `01000000000000000000000159`
- Tag inativa (negada): `01000000000000000000000160`

Motoristas ficticios criados automaticamente:

- `Alex Liberado` (tag liberada)
- `Bruno Teste` (tags inativas)

Para desativar o seed:

```bash
export SEED_TEST_DATA=false
```