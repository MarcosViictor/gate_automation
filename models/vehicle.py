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
    tag_code: str | None = None  

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
