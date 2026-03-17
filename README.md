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
export RFID_HID_OFFSET=18
export RFID_HID_STRIP_HEX_DIGITS=4
python main.py
```

Observacoes:

- `RFID_HID_OFFSET` pode variar por leitor/OS. Se o codigo sair incorreto, teste `17`, `18` ou `19`.
- `RFID_HID_STRIP_HEX_DIGITS` remove sufixo no final da tag (checksum/padding). O padrao e `4`.
- Se nao quiser filtrar dispositivo HID por VID/PID, deixe `RFID_HID_VENDOR_ID` e `RFID_HID_PRODUCT_ID` vazios.

Para descobrir VID/PID no Linux:

```bash
lsusb
```

### Dependencias

Instale as dependencias:

```bash
pip install -r requirements.txt
```