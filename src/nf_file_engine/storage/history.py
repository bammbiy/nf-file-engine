from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class HistoryRecord:
    id: int
    batch_id: str
    source_path: str
    target_path: str
    created_at: str
    undone_at: str | None


class HistoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rename_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT,
                    source_path TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    undone_at TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(rename_history)").fetchall()
            }
            if "batch_id" not in columns:
                conn.execute("ALTER TABLE rename_history ADD COLUMN batch_id TEXT")
            conn.execute(
                """
                UPDATE rename_history
                SET batch_id = 'legacy-' || id
                WHERE batch_id IS NULL OR batch_id = ''
                """
            )

    def record(self, source: Path, target: Path, batch_id: str | None = None) -> None:
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rename_history (batch_id, source_path, target_path, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (batch_id or created_at, str(source), str(target), created_at),
            )

    def recent(self, limit: int = 20) -> list[dict[str, str | int | None]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, batch_id, source_path, target_path, created_at, undone_at
                FROM rename_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_batches(self, limit: int = 20) -> list[dict[str, str | int | None]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    batch_id,
                    MIN(created_at) AS created_at,
                    COUNT(*) AS item_count,
                    SUM(CASE WHEN undone_at IS NULL THEN 0 ELSE 1 END) AS undone_count
                FROM rename_history
                GROUP BY batch_id
                ORDER BY MAX(id) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_active_batch(self) -> list[HistoryRecord]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            batch = conn.execute(
                """
                SELECT batch_id
                FROM rename_history
                WHERE undone_at IS NULL
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if batch is None:
                return []
            rows = conn.execute(
                """
                SELECT id, batch_id, source_path, target_path, created_at, undone_at
                FROM rename_history
                WHERE batch_id = ? AND undone_at IS NULL
                ORDER BY id DESC
                """,
                (batch["batch_id"],),
            ).fetchall()
        return [HistoryRecord(**dict(row)) for row in rows]

    def mark_undone(self, history_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE rename_history SET undone_at = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), history_id),
            )

    def mark_batch_undone(self, batch_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE rename_history SET undone_at = ? WHERE batch_id = ? AND undone_at IS NULL",
                (datetime.now().isoformat(timespec="seconds"), batch_id),
            )
