# Design Doc: Veículos e Tags Listing Screens

## Overview
This document outlines the design for introducing read-only vehicle and tag lists in the Tkinter GUI. 
The application acts as an edge node in a gate automation system, relying on local offline data synchronized from a cloud server. 

## Architectural Decision Record (ADR) Link
The architectural decision to keep edge clients read-only and synchronize data from a cloud API is detailed in [docs/adr/0001-edge-device-offline-first.md](file:///home/victor/dev/gate_automation/docs/adr/0001-edge-device-offline-first.md).

## Proposed Changes

### 1. Database Schema
Add a `vehicles` table in [models/database.py](file:///home/victor/dev/gate_automation/models/database.py):
```sql
CREATE TABLE IF NOT EXISTS vehicles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id   INTEGER UNIQUE,
    plate       TEXT NOT NULL UNIQUE,
    tag_id      INTEGER,
    portaria_id INTEGER,
    model       TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    updated_at  TEXT,
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

### 2. Vehicle Model & Repository
Create [models/vehicle.py](file:///home/victor/dev/gate_automation/models/vehicle.py):
* `Vehicle` dataclass containing all fields.
* `VehicleRepository` containing `find_all_active()`, `find_by_tag_code()`, and `upsert()`.

### 3. UI Updates
In [views/main_window.py](file:///home/victor/dev/gate_automation/views/main_window.py):
* Add two new tabs to the notebook: **"Veículos"** and **"Tags"**.
* **Veículos Tab**: Displays a table (Treeview) of vehicles with columns: Placa, Modelo, Portaria ID, Tag e Status.
* **Tags Tab**: Displays a table (Treeview) of tags with columns: Tag Código e Status.
* Data is fetched from the database when the tabs are initialized or when a refresh is called (e.g. after sync).

### 4. Seed Data Update
Update `_seed_test_data` in [main.py](file:///home/victor/dev/gate_automation/main.py) to seed a few vehicles linked to the test tags.
