# database/seed.py
from __future__ import annotations
from database import Database


DRIVERS = [
    # (name, cpf, phone)
    ("nininho",    "111.111.111-11", "(85) 99111-1111"),
    ("carol regis",   "222.222.222-22", "(85) 99222-2222"),
    ("Ritinha", "333.333.333-33", "(85) 99333-3333"),
]

TAGS = [
    # (tag_code,)  — driver_id preenchido em runtime
    ("TAG-001-ABC",),
    ("TAG-002-DEF",),
    ("TAG-003-GHI",),
]

VEHICLES = [
    # (plate, model)  — tag_id preenchido em runtime
    ("ABC-1234", "Fiat Strada"),
    ("DEF-5678", "Volkswagen Gol"),
    ("GHI-9012", "Chevrolet S10"),
]


def run(db: Database) -> None:
    driver_ids = _seed_drivers(db)
    tag_ids    = _seed_tags(db, driver_ids)
    _seed_vehicles(db, tag_ids)
    print("✅ Seed concluído: 3 drivers, 3 tags e 3 veículos inseridos.")


# ------------------------------------------------------------------
# Helpers privados
# ------------------------------------------------------------------

def _seed_drivers(db: Database) -> list[int]:
    ids = []
    for name, cpf, phone in DRIVERS:
        existing = db.fetchone("SELECT id FROM drivers WHERE cpf = ?", (cpf,))
        if existing:
            print(f"  [skip] Driver já existe: {name}")
            ids.append(existing["id"])
            continue

        cur = db.execute(
            "INSERT INTO drivers (name, cpf, phone, is_active) VALUES (?, ?, ?, 1)",
            (name, cpf, phone),
        )
        ids.append(cur.lastrowid)
        print(f"  [insert] Driver: {name} (id={cur.lastrowid})")

    return ids


def _seed_tags(db: Database, driver_ids: list[int]) -> list[int]:
    ids = []
    for (tag_code,), driver_id in zip(TAGS, driver_ids):
        existing = db.fetchone("SELECT id FROM tags WHERE tag_code = ?", (tag_code,))
        if existing:
            print(f"  [skip] Tag já existe: {tag_code}")
            ids.append(existing["id"])
            continue

        cur = db.execute(
            "INSERT INTO tags (tag_code, driver_id, is_active) VALUES (?, ?, 1)",
            (tag_code, driver_id),
        )
        ids.append(cur.lastrowid)
        print(f"  [insert] Tag: {tag_code} → driver_id={driver_id} (id={cur.lastrowid})")

    return ids


def _seed_vehicles(db: Database, tag_ids: list[int]) -> None:
    for (plate, model), tag_id in zip(VEHICLES, tag_ids):
        existing = db.fetchone("SELECT id FROM vehicles WHERE plate = ?", (plate,))
        if existing:
            print(f"  [skip] Veículo já existe: {plate}")
            continue

        cur = db.execute(
            "INSERT INTO vehicles (plate, model, tag_id, is_active) VALUES (?, ?, ?, 1)",
            (plate, model, tag_id),
        )
        print(f"  [insert] Veículo: {plate} ({model}) → tag_id={tag_id} (id={cur.lastrowid})")


# ------------------------------------------------------------------
# Execução direta
# ------------------------------------------------------------------

if __name__ == "__main__":
    db = Database()
    db.create_tables()
    run(db)