# Gate Timer Auto-Close Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Implement a 90-second (1:30) automatic gate closing timer, triggered after a successful RFID tag read, ensuring the reader only opens the gate and the timer closes it, with timer restart support if a new tag is read.

**Architecture:** We will manage the timer state in `main.py` using `threading.Timer` and a `threading.Lock` for thread-safety. The original logic will be commented out, and cleanup of the timer on shutdown will be added to the `finally` block.

**Tech Stack:** Python standard library (`threading.Timer`, `threading.Lock`).

---

### Task 1: Add State Variables and `close_gate` Helper to `main.py`

**Files:**
- Modify: [main.py](file:///home/victor/dev/gate_automation/main.py)

**Step 1: Write the minimal implementation**
Introduce the state variables inside `main()` right before the reader initialization, and define the `close_gate` helper.

```python
    # Timer state variables for auto-close
    gate_timer = None
    gate_timer_lock = threading.Lock()

    def close_gate():
        nonlocal gate_timer
        logger.info("⏰ Temporizador expirou. Enviando impulso para FECHAR o portão.")
        gate.open()  # Sends the close pulse
        with gate_timer_lock:
            gate_timer = None
        if app:
            app.after(0, lambda: app.update_gate_status(False))
```

**Step 2: Commit**
```bash
git add main.py
git commit -m "feat: initialize timer state variables and close_gate helper"
```

---

### Task 2: Comment out existing tag handling and implement new timer logic in `handle_tag`

**Files:**
- Modify: [main.py](file:///home/victor/dev/gate_automation/main.py)

**Step 1: Write minimal implementation**
Modify `handle_tag` in `main.py` to comment out the old logic and write the timer reset/trigger logic:

```python
    def handle_tag(tag_code: str, direction: str):
        nonlocal gate_timer
        logger.info("Leitura: Tag=%s, Direction=%s", tag_code, direction)
        result = auth.process(tag_code, direction)

        # Comentado o código original conforme solicitado
        # if result.authorized:
        #     logger.info("🔓 ACESSO AUTORIZADO para a tag %s", tag_code)
        #     gate.open()
        # else:
        #     logger.warning("🔒 ACESSO NEGADO para a tag %s. Motivo: %s", tag_code, result.reason)
        #     
        # # Agendar atualização da UI na thread principal se a tela estiver ativa
        # if app:
        #     app.after(0, lambda: [
        #         app.refresh_all_tabs(),
        #         app.update_gate_status(result.authorized)
        #     ])
        #     
        #     # Fecha o portão visualmente depois do tempo
        #     if result.authorized:
        #         app.after(config.GATE_OPEN_DURATION * 1000, lambda: app.update_gate_status(False))

        # Nova funcionalidade de temporizador de 1:30 para fechar o portão
        if result.authorized:
            logger.info("🔓 ACESSO AUTORIZADO para a tag %s", tag_code)
            
            with gate_timer_lock:
                if gate_timer is not None:
                    logger.info("Reiniciando o temporizador de 1:30 para fechar o portão.")
                    gate_timer.cancel()
                    gate_timer = None
                else:
                    logger.info("Enviando impulso para ABRIR o portão.")
                    gate.open()
                
                # Agenda o fechamento do portão para 90 segundos (1:30)
                gate_timer = threading.Timer(90.0, close_gate)
                gate_timer.start()
        else:
            logger.warning("🔒 ACESSO NEGADO para a tag %s. Motivo: %s", tag_code, result.reason)

        if app:
            app.after(0, lambda: [
                app.refresh_all_tabs(),
                app.update_gate_status(result.authorized)
            ])
```

**Step 2: Commit**
```bash
git add main.py
git commit -m "feat: refactor handle_tag to use 90s auto-close timer"
```

---

### Task 3: Clean up timer on application shutdown

**Files:**
- Modify: [main.py](file:///home/victor/dev/gate_automation/main.py)

**Step 1: Write minimal implementation**
Modify the `finally` block in `main.py` to cancel the active timer if one is running:

```python
    finally:
        logger.info("Encerrando serviços...")
        if reader_in: reader_in.stop()
        if reader_out: reader_out.stop()
        sync.stop()
        
        # Cancela temporizador ativo no desligamento
        with gate_timer_lock:
            if gate_timer:
                gate_timer.cancel()
                
        gate.cleanup()
        db.close()
        logger.info("Desligamento completo.")
```

**Step 2: Commit**
```bash
git add main.py
git commit -m "feat: cancel active gate timer on exit"
```

---

### Task 4: Manual Verification of the 90-second Timer

**Step 1: Run the application in mock mode**
Run: `python3 main.py` or `MOCK_HARDWARE=true python3 main.py`
Verify that the application starts successfully and visual monitor is shown.

**Step 2: Verify Opening Pulse**
Action: In the Simulator tab, enter tag `01E28069150000401D63E8C9` and press Enter.
Expected behavior:
- Log shows `🔓 ACESSO AUTORIZADO para a tag 01E28069150000401D63E8C9`
- Log shows `Enviando impulso para ABRIR o portão.`
- Log shows `[MOCK] Portão ABERTO por 5 segundo(s)`
- UI gate status changes to "PORTÃO ABERTO" and stays there.

**Step 3: Verify Timer Reset**
Action: Within 90 seconds (e.g. at 20 seconds), enter the same tag `01E28069150000401D63E8C9` and press Enter.
Expected behavior:
- Log shows `Reiniciando o temporizador de 1:30 para fechar o portão.`
- Verify that **NO** new `[MOCK] Portão ABERTO por 5 segundo(s)` log is emitted at this time.

**Step 4: Verify Auto-Closing Pulse**
Action: Wait for 90 seconds after the second read.
Expected behavior:
- Log shows `⏰ Temporizador expirou. Enviando impulso para FECHAR o portão.`
- Log shows `[MOCK] Portão ABERTO por 5 segundo(s)` (representing the closing pulse trigger)
- UI gate status changes to "PORTÃO FECHADO".
