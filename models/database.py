from __future__ import annotations
import sqlite3
import os
from config import DB_PATH


class Database:
    """
    Gerencia a conexão e criação do banco de dados SQLite local.
    Este banco serve como backup para operação offline do Raspberry Pi.
    """

    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def create_tables(self):
        conn = self.connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS drivers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id   INTEGER UNIQUE,
                name        TEXT NOT NULL,
                cpf         TEXT,
                phone       TEXT,
                is_active   INTEGER NOT NULL DEFAULT 1,
                updated_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id   INTEGER UNIQUE,
                tag_code    TEXT NOT NULL UNIQUE,
                driver_id   INTEGER,
                is_active   INTEGER NOT NULL DEFAULT 1,
                updated_at  TEXT,
                FOREIGN KEY (driver_id) REFERENCES drivers(id)
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id           INTEGER UNIQUE,
                driver_id           INTEGER,
                scheduled_date      TEXT NOT NULL,
                time_start          TEXT NOT NULL,
                time_end            TEXT NOT NULL,
                is_active           INTEGER NOT NULL DEFAULT 1,
                updated_at          TEXT,
                FOREIGN KEY (driver_id) REFERENCES drivers(id)
            );

            CREATE TABLE IF NOT EXISTS access_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_code    TEXT NOT NULL,
                driver_id   INTEGER,
                authorized  INTEGER NOT NULL,
                direction   TEXT NOT NULL DEFAULT 'IN',
                reason      TEXT,
                mode        TEXT NOT NULL DEFAULT 'online',
                synced      INTEGER NOT NULL DEFAULT 0,
                timestamp   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
            
            CREATE TABLE IF NOT EXISTS settings (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL
            );
        """)
        conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        if row:
            return row["value"]
        return default

    def set_setting(self, key: str, value: str):
        self.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )

    # ------------------------------------------------------------------
    # Helpers genéricos
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: tuple = ()):
        conn = self.connect()
        cur = conn.execute(sql, params)
        conn.commit()
        return cur

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.connect().execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.connect().execute(sql, params).fetchone()
