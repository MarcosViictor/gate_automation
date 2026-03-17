from __future__ import annotations
from dataclasses import dataclass
from datetime import date, time
from models.database import Database


@dataclass
class Schedule:
    driver_id: int
    scheduled_date: str   # formato ISO: "YYYY-MM-DD"
    time_start: str        # formato "HH:MM"
    time_end: str          # formato "HH:MM"
    is_active: bool = True
    id: int | None = None
    server_id: int | None = None
    updated_at: str | None = None


class ScheduleRepository:
    def __init__(self, db: Database):
        self._db = db

    def find_active_for_driver_today(self, driver_id: int) -> Schedule | None:
        """Retorna o agendamento ativo de um motorista para o dia atual."""
        today = date.today().isoformat()
        row = self._db.fetchone(
            """
            SELECT * FROM schedules
            WHERE driver_id = ?
              AND scheduled_date = ?
              AND is_active = 1
            LIMIT 1
            """,
            (driver_id, today),
        )
        return self._from_row(row) if row else None

    def find_all_for_date(self, target_date: str) -> list[Schedule]:
        rows = self._db.fetchall(
            "SELECT * FROM schedules WHERE scheduled_date = ? AND is_active = 1",
            (target_date,),
        )
        return [self._from_row(r) for r in rows]

    def upsert(self, schedule: Schedule) -> None:
        self._db.execute(
            """
            INSERT INTO schedules
                (server_id, driver_id, scheduled_date, time_start, time_end, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(server_id) DO UPDATE SET
                driver_id      = excluded.driver_id,
                scheduled_date = excluded.scheduled_date,
                time_start     = excluded.time_start,
                time_end       = excluded.time_end,
                is_active      = excluded.is_active,
                updated_at     = excluded.updated_at
            """,
            (schedule.server_id, schedule.driver_id, schedule.scheduled_date,
             schedule.time_start, schedule.time_end, int(schedule.is_active),
             schedule.updated_at),
        )

    def find_all(self, limit: int = 200) -> list[Schedule]:
        """Retorna todos os agendamentos ordenados por data e hora de início."""
        rows = self._db.fetchall(
            """
            SELECT s.*, d.name as driver_name
            FROM schedules s
            LEFT JOIN drivers d ON s.driver_id = d.id
            ORDER BY s.scheduled_date DESC, s.time_start ASC
            LIMIT ?
            """,
            (limit,),
        )
        result = []
        for r in rows:
            s = self._from_row(r)
            s._driver_name = r["driver_name"] if r["driver_name"] else "—"
            result.append(s)
        return result

    def count_today(self) -> int:
        today = date.today().isoformat()
        row = self._db.fetchone(
            "SELECT COUNT(*) as total FROM schedules WHERE scheduled_date = ? AND is_active = 1",
            (today,),
        )
        return row["total"] if row else 0

    def _from_row(self, row) -> Schedule:
        return Schedule(
            id=row["id"],
            server_id=row["server_id"],
            driver_id=row["driver_id"],
            scheduled_date=row["scheduled_date"],
            time_start=row["time_start"],
            time_end=row["time_end"],
            is_active=bool(row["is_active"]),
            updated_at=row["updated_at"],
        )
