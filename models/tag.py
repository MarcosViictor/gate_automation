from __future__ import annotations
from dataclasses import dataclass, field
from models.database import Database


@dataclass
class Tag:
    tag_code: str
    driver_id: int | None = None
    is_active: bool = True
    id: int | None = None
    server_id: int | None = None
    updated_at: str | None = None


class TagRepository:
    def __init__(self, db: Database):
        self._db = db

    def find_by_code(self, tag_code: str) -> Tag | None:
        row = self._db.fetchone(
            "SELECT * FROM tags WHERE tag_code = ? AND is_active = 1",
            (tag_code,),
        )
        if row is None:
            return None
        return Tag(
            id=row["id"],
            server_id=row["server_id"],
            tag_code=row["tag_code"],
            driver_id=row["driver_id"],
            is_active=bool(row["is_active"]),
            updated_at=row["updated_at"],
        )

    def upsert(self, tag: Tag) -> None:
        """Insere ou atualiza uma tag (usado na sincronização com o servidor)."""
        self._db.execute(
            """
            INSERT INTO tags (server_id, tag_code, driver_id, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(server_id) DO UPDATE SET
                tag_code   = excluded.tag_code,
                driver_id  = excluded.driver_id,
                is_active  = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            (tag.server_id, tag.tag_code, tag.driver_id, int(tag.is_active), tag.updated_at),
        )

    def find_by_driver_id(self, driver_id: int) -> list[Tag]:
        rows = self._db.fetchall(
            "SELECT * FROM tags WHERE driver_id = ? ORDER BY tag_code",
            (driver_id,),
        )
        return [
            Tag(
                id=r["id"],
                server_id=r["server_id"],
                tag_code=r["tag_code"],
                driver_id=r["driver_id"],
                is_active=bool(r["is_active"]),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def find_all(self) -> list[Tag]:
        rows = self._db.fetchall(
            "SELECT * FROM tags ORDER BY tag_code"
        )
        return [
            Tag(
                id=r["id"],
                server_id=r["server_id"],
                tag_code=r["tag_code"],
                driver_id=r["driver_id"],
                is_active=bool(r["is_active"]),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def count(self) -> int:
        row = self._db.fetchone("SELECT COUNT(*) as total FROM tags WHERE is_active = 1")
        return row["total"] if row else 0
