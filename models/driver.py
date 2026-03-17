from __future__ import annotations
from dataclasses import dataclass
from models.database import Database


@dataclass
class Driver:
    name: str
    cpf: str | None = None
    phone: str | None = None
    is_active: bool = True
    id: int | None = None
    server_id: int | None = None
    updated_at: str | None = None


class DriverRepository:
    def __init__(self, db: Database):
        self._db = db

    def find_by_id(self, driver_id: int) -> Driver | None:
        row = self._db.fetchone(
            "SELECT * FROM drivers WHERE id = ?",
            (driver_id,),
        )
        if row is None:
            return None
        return self._from_row(row)

    def find_all_active(self) -> list[Driver]:
        rows = self._db.fetchall("SELECT * FROM drivers WHERE is_active = 1 ORDER BY name")
        return [self._from_row(r) for r in rows]

    def upsert(self, driver: Driver) -> None:
        self._db.execute(
            """
            INSERT INTO drivers (server_id, name, cpf, phone, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(server_id) DO UPDATE SET
                name       = excluded.name,
                cpf        = excluded.cpf,
                phone      = excluded.phone,
                is_active  = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            (driver.server_id, driver.name, driver.cpf, driver.phone,
             int(driver.is_active), driver.updated_at),
        )

    def count(self) -> int:
        row = self._db.fetchone("SELECT COUNT(*) as total FROM drivers WHERE is_active = 1")
        return row["total"] if row else 0

    def _from_row(self, row) -> Driver:
        return Driver(
            id=row["id"],
            server_id=row["server_id"],
            name=row["name"],
            cpf=row["cpf"],
            phone=row["phone"],
            is_active=bool(row["is_active"]),
            updated_at=row["updated_at"],
        )
