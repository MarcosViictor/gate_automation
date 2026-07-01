# Thin Client Architecture (Prototip_01) Design

## Overview
The project is pivoting from an Edge-Heavy architecture (local SQLite database with background sync) to an Edge-Thin architecture. The Raspberry Pi will act purely as a sensor and actuator node, relaying all authorization queries in real-time to a local Fog server.

## Key Changes

### 1. Removal of Local Database
- **Action**: Delete `models/database.py`, all SQLAlchemy model files (`tag.py`, `vehicle.py`, `driver.py`, `access_log.py`), and repositories.
- **Benefit**: Vastly simplifies the codebase, eliminates the need for background synchronization (`SyncController`), and increases the lifespan of the Raspberry Pi's SD card by eliminating constant database writes.

### 2. Configuration Management via `.env`
- **Action**: Since the local SQLite `settings` table is being removed, we will transition to using a `.env` file to store persistent configuration.
- **Settings to Track**: 
  - `SERVER_BASE_URL` (The local server IP/Port)
  - `RFID_PORT_IN`
  - `RFID_PORT_OUT`
- **UI Integration**: The existing Tkinter UI will be updated with a dedicated "Configurações" tab. This tab will allow the user to input the Server IP and select the RFID ports. Upon saving, the UI will write these values to the `.env` file using the `python-dotenv` library.

### 3. Real-time Authentication
- **Action**: Refactor `AuthController.process(tag_code, direction)` to make a synchronous HTTP request to the local server.
- **Flow**:
  1. RFID Reader detects a tag.
  2. `AuthController` sends a `POST {SERVER_BASE_URL}/api/gate/check` with payload `{"tag_code": tag_code, "direction": direction}`.
  3. The local server responds with `200 OK` (Authorized) or `4xx/5xx` (Denied).
  4. The Gate Controller opens the gate if authorized, utilizing the existing ultrasonic active-close logic.

## Trade-offs and Risks
- **Network Dependency**: The gate will not operate if the local network between the Raspberry Pi and the Fog Server is down. 
- **Latency**: HTTP requests introduce minor latency (typically <50ms on a LAN), which is negligible for this application.
