# Vehicle and Tag Listing Screen Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Create read-only listing screens (tabs) for Vehicles and Tags in the Tkinter GUI, pulling data from the local SQLite offline-first database.

**Architecture:** We will create a `vehicles` table referencing the `tags` table, a `VehicleRepository` to query vehicles, and add two read-only tabs ("Veículos" and "Tags") using `ttk.Treeview` within the existing notebook of `MainWindow`.

**Tech Stack:** Python 3, Tkinter / ttk, SQLite.

---

### Task 1: Create Database Table for Vehicles

**Files:**
- Modify: `models/database.py`
- Create: `tests/test_database.py`

**Step 1: Write the failing test**
Create `tests/test_database.py` to check that the database creates the `vehicles` table with correct columns:
```python
import unittest
import os
import sqlite3
from models.database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_gate_local.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Import config and override DB_PATH dynamically for tests
        import config
        config.DB_PATH = self.db_path
        self.db = Database()
        self.db.create_tables()

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_vehicles_table_exists(self):
        conn = self.db.connect()
        cursor = conn.execute("PRAGMA table_info(vehicles)")
        columns = {row["name"]: row["type"] for row in cursor.fetchall()}
        
        self.assertIn("id", columns)
        self.assertIn("server_id", columns)
        self.assertIn("plate", columns)
        self.assertIn("tag_id", columns)
        self.assertIn("portaria_id", columns)
        self.assertIn("model", columns)
        self.assertIn("is_active", columns)
        self.assertIn("updated_at", columns)

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests/test_database.py`
Expected: FAIL (no table named vehicles)

**Step 3: Write minimal implementation**
Modify [models/database.py](file:///home/victor/dev/gate_automation/models/database.py) to add the table creation sql to `create_tables()`:
```python
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

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests/test_database.py`
Expected: PASS

**Step 5: Commit**
```bash
git add models/database.py tests/test_database.py
git commit -m "feat: add vehicles table and database creation tests"
```

---

### Task 2: Implement Vehicle Model & Repository

**Files:**
- Create: `models/vehicle.py`
- Create: `tests/test_vehicle.py`

**Step 1: Write the failing test**
Create `tests/test_vehicle.py`:
```python
import unittest
import os
from models.database import Database
from models.tag import Tag, TagRepository
from models.vehicle import Vehicle, VehicleRepository

class TestVehicleRepository(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_vehicle.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import config
        config.DB_PATH = self.db_path
        self.db = Database()
        self.db.create_tables()
        self.tag_repo = TagRepository(self.db)
        self.vehicle_repo = VehicleRepository(self.db)

        # Seed a tag
        self.tag_repo.upsert(Tag(server_id=1, tag_code="ABC12345", is_active=True))
        self.tag = self.tag_repo.find_by_code("ABC12345")

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_upsert_and_find_all(self):
        v = Vehicle(plate="XYZ-9876", model="Golf", portaria_id=1, tag_id=self.tag.id)
        self.vehicle_repo.upsert(v)
        
        vehicles = self.vehicle_repo.find_all()
        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0].plate, "XYZ-9876")
        self.assertEqual(vehicles[0].tag_code, "ABC12345")

    def test_find_by_tag_code(self):
        v = Vehicle(plate="XYZ-9876", model="Golf", portaria_id=1, tag_id=self.tag.id)
        self.vehicle_repo.upsert(v)
        
        found = self.vehicle_repo.find_by_tag_code("ABC12345")
        self.assertIsNotNone(found)
        self.assertEqual(found.plate, "XYZ-9876")

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests/test_vehicle.py`
Expected: FAIL (cannot import name 'Vehicle' / 'VehicleRepository')

**Step 3: Write minimal implementation**
Create [models/vehicle.py](file:///home/victor/dev/gate_automation/models/vehicle.py):
```python
from __future__ import annotations
from dataclasses import dataclass
from models.database import Database

@dataclass
class Vehicle:
    plate: str
    model: str | None = None
    portaria_id: int | None = None
    tag_id: int | None = None
    is_active: bool = True
    id: int | None = None
    server_id: int | None = None
    updated_at: str | None = None
    tag_code: str | None = None  # Joined field for ease of display

class VehicleRepository:
    def __init__(self, db: Database):
        self._db = db

    def upsert(self, vehicle: Vehicle) -> None:
        self._db.execute(
            """
            INSERT INTO vehicles (server_id, plate, tag_id, portaria_id, model, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plate) DO UPDATE SET
                server_id   = excluded.server_id,
                tag_id      = excluded.tag_id,
                portaria_id = excluded.portaria_id,
                model       = excluded.model,
                is_active   = excluded.is_active,
                updated_at  = excluded.updated_at
            """,
            (vehicle.server_id, vehicle.plate, vehicle.tag_id, vehicle.portaria_id,
             vehicle.model, int(vehicle.is_active), vehicle.updated_at),
        )

    def find_all(self) -> list[Vehicle]:
        rows = self._db.fetchall(
            """
            SELECT v.*, t.tag_code
            FROM vehicles v
            LEFT JOIN tags t ON v.tag_id = t.id
            ORDER BY v.plate
            """
        )
        return [self._from_row(r) for r in rows]

    def find_by_tag_code(self, tag_code: str) -> Vehicle | None:
        row = self._db.fetchone(
            """
            SELECT v.*, t.tag_code
            FROM vehicles v
            JOIN tags t ON v.tag_id = t.id
            WHERE t.tag_code = ? AND v.is_active = 1
            """,
            (tag_code,),
        )
        if row is None:
            return None
        return self._from_row(row)

    def _from_row(self, row) -> Vehicle:
        return Vehicle(
            id=row["id"],
            server_id=row["server_id"],
            plate=row["plate"],
            tag_id=row["tag_id"],
            portaria_id=row["portaria_id"],
            model=row["model"],
            is_active=bool(row["is_active"]),
            updated_at=row["updated_at"],
            tag_code=row["tag_code"] if "tag_code" in row.keys() else None,
        )
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests/test_vehicle.py`
Expected: PASS

**Step 5: Commit**
```bash
git add models/vehicle.py tests/test_vehicle.py
git commit -m "feat: implement Vehicle and VehicleRepository with queries"
```

---

### Task 3: Seed Vehicles Data

**Files:**
- Modify: `main.py`

**Step 1: Write manual verification check**
Confirm we will seed data in `main.py` so we can view mock vehicles linked to tags in the GUI.

**Step 2: Write minimal implementation**
Modify [main.py](file:///home/victor/dev/gate_automation/main.py) to import `Vehicle` and `VehicleRepository`, and add seeding logic to `_seed_test_data(db)`:
```python
def _seed_test_data(db: Database) -> None:
    from models.vehicle import Vehicle, VehicleRepository
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags = TagRepository(db)
    vehicles = VehicleRepository(db)

    tags.upsert(Tag(server_id=99201, tag_code="01000000000000000000000158", driver_id=None, is_active=True, updated_at=now))
    tags.upsert(Tag(server_id=99202, tag_code="01000000000000000000000159", driver_id=None, is_active=False, updated_at=now))
    tags.upsert(Tag(server_id=99203, tag_code="01000000000000000000000160", driver_id=None, is_active=False, updated_at=now))
    tags.upsert(Tag(server_id=99204, tag_code="01E28069150000401D63E8C9", driver_id=None, is_active=True, updated_at=now))

    # Fetch seeded tag IDs to associate with vehicles
    t1 = tags.find_by_code("01000000000000000000000158")
    t2 = tags.find_by_code("01E28069150000401D63E8C9")

    if t1:
        vehicles.upsert(Vehicle(server_id=101, plate="ABC-1234", model="Toyota Hilux", portaria_id=1, tag_id=t1.id, is_active=True, updated_at=now))
    if t2:
        vehicles.upsert(Vehicle(server_id=102, plate="XYZ-9876", model="Honda Civic", portaria_id=2, tag_id=t2.id, is_active=True, updated_at=now))
```

**Step 3: Commit**
```bash
git add main.py
git commit -m "feat: seed vehicles data in main.py"
```

---

### Task 4: Add Vehicles & Tags GUI Tabs

**Files:**
- Modify: `views/main_window.py`

**Step 1: Write minimal implementation**
Modify [views/main_window.py](file:///home/victor/dev/gate_automation/views/main_window.py) to import `VehicleRepository` and `TagRepository`, and add the tabs in `__init__`:
* Add `self._build_vehicles_tab()` and `self._build_tags_tab()` calls in `__init__`.
* Implement the tab creation methods using `ttk.Treeview`.
* Implement functions `refresh_vehicles()` and `refresh_tags()`.
* Add custom refresh callbacks after `on_sync` or periodic refreshes if needed, or simply load them at initialization.

Example tab creation methods:
```python
    def _build_vehicles_tab(self):
        from models.vehicle import VehicleRepository
        self.vehicle_repo = VehicleRepository(self.db)
        
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Veículos")

        frame = ttk.Frame(tab, style="Card.TFrame")
        frame.pack(expand=True, fill='both', padx=10, pady=10)

        columns = ("plate", "model", "portaria", "tag", "status")
        self.tree_vehicles = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree_vehicles.heading("plate", text="Placa")
        self.tree_vehicles.heading("model", text="Modelo")
        self.tree_vehicles.heading("portaria", text="Portaria ID")
        self.tree_vehicles.heading("tag", text="Tag Código")
        self.tree_vehicles.heading("status", text="Status")

        self.tree_vehicles.column("plate", width=100)
        self.tree_vehicles.column("model", width=150)
        self.tree_vehicles.column("portaria", width=100, anchor='center')
        self.tree_vehicles.column("tag", width=200)
        self.tree_vehicles.column("status", width=100, anchor='center')

        self.tree_vehicles.pack(expand=True, fill='both', padx=2, pady=2)
        
        btn_refresh = ttk.Button(tab, text="⟳ Atualizar Lista", command=self.refresh_vehicles)
        btn_refresh.pack(pady=5)

        self.refresh_vehicles()

    def refresh_vehicles(self):
        for item in self.tree_vehicles.get_children():
            self.tree_vehicles.delete(item)
        
        vehicles = self.vehicle_repo.find_all()
        for v in vehicles:
            status = "Ativo" if v.is_active else "Inativo"
            self.tree_vehicles.insert("", "end", values=(
                v.plate,
                v.model or "-",
                v.portaria_id or "-",
                v.tag_code or "Não vinculada",
                status
            ))

    def _build_tags_tab(self):
        from models.tag import TagRepository
        self.tag_repo = TagRepository(self.db)

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Tags")

        frame = ttk.Frame(tab, style="Card.TFrame")
        frame.pack(expand=True, fill='both', padx=10, pady=10)

        columns = ("code", "status")
        self.tree_tags = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree_tags.heading("code", text="Tag Código")
        self.tree_tags.heading("status", text="Status")

        self.tree_tags.column("code", width=300)
        self.tree_tags.column("status", width=150, anchor='center')

        self.tree_tags.pack(expand=True, fill='both', padx=2, pady=2)
        
        btn_refresh = ttk.Button(tab, text="⟳ Atualizar Lista", command=self.refresh_tags)
        btn_refresh.pack(pady=5)

        self.refresh_tags()

    def refresh_tags(self):
        for item in self.tree_tags.get_children():
            self.tree_tags.delete(item)
        
        tags = self.tag_repo.find_all()
        for t in tags:
            status = "Ativa" if t.is_active else "Inativa"
            self.tree_tags.insert("", "end", values=(
                t.tag_code,
                status
            ))
```

And update `handle_sync` callback inside `main()` in `main.py` so that it refreshes all Treeviews when a sync finishes.

**Step 2: Commit**
```bash
git add views/main_window.py
git commit -m "feat: add vehicles and tags tabs to Tkinter GUI"
```
