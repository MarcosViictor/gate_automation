from __future__ import annotations
from dataclasses import dataclass
from models.database import Database


@dataclass
class AccessLog:
    tag_code: str
    authorized: bool
    direction: str = "IN"       # "IN" | "OUT"
    mode: str = "online"        # "online" | "offline"
    driver_id: int | None = None
    reason: str | None = None
    timestamp: str | None = None
    synced: bool = False
    id: int | None = None


class AccessLogRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, log: AccessLog) -> None:
        self._db.execute(
            """
            INSERT INTO access_logs (tag_code, driver_id, authorized, direction, reason, mode, synced)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (log.tag_code, log.driver_id, int(log.authorized), log.direction,
             log.reason, log.mode, int(log.synced)),
        )

    def find_recent(self, limit: int = 50) -> list[AccessLog]:
        rows = self._db.fetchall(
            """
            SELECT al.*, d.name as driver_name
            FROM access_logs al
            LEFT JOIN drivers d ON al.driver_id = d.id
            ORDER BY al.timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._from_row(r) for r in rows]

    def find_unsynced(self) -> list[AccessLog]:
        rows = self._db.fetchall(
            "SELECT * FROM access_logs WHERE synced = 0 ORDER BY timestamp ASC"
        )
        return [self._from_row(r) for r in rows]

    def mark_synced(self, log_id: int) -> None:
        self._db.execute("UPDATE access_logs SET synced = 1 WHERE id = ?", (log_id,))

    def count_today(self) -> int:
        row = self._db.fetchone(
            """
            SELECT COUNT(*) as total FROM access_logs
            WHERE date(timestamp) = date('now','localtime')
            """
        )
        return row["total"] if row else 0

    def _from_row(self, row) -> AccessLog:
        log = AccessLog(
            id=row["id"],
            tag_code=row["tag_code"],
            driver_id=row["driver_id"],
            authorized=bool(row["authorized"]),
            direction=row["direction"] if "direction" in row.keys() else "IN",
            reason=row["reason"],
            mode=row["mode"],
            synced=bool(row["synced"]),
            timestamp=row["timestamp"],
        )
        # driver_name pode estar presente na query com JOIN
        if "driver_name" in row.keys() and row["driver_name"]:
            log.reason = log.reason  # mantém reason; driver_name fica no campo extra
            log._driver_name = row["driver_name"]
        return log
