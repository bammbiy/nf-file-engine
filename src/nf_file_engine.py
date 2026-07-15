from __future__ import annotations

import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DEFAULT_RULE = "{DATE}_{MEDIA}_{PAGE}"
MEDIA_CODE_PATTERN = re.compile(r"(?i)(?<![a-z0-9])([a-z]{2}\d{2})(?![a-z0-9])")
DATE_PATTERN = re.compile(r"(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?([0-2]\d|3[01])")
PAGE_PATTERN = re.compile(r"(?i)(?:page|p|면|_)(\d{1,3})(?=\D|$)")


@dataclass(frozen=True)
class RenameInput:
    path: Path
    date: str
    media: str
    page: str
    rule: str = DEFAULT_RULE


@dataclass(frozen=True)
class RenamePreview:
    source: Path
    target: Path
    status: str
    message: str = ""


class RenameError(ValueError):
    pass


def normalize_date(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 8:
        raise RenameError("날짜는 YYYYMMDD 형식이어야 합니다.")
    datetime.strptime(digits, "%Y%m%d")
    return digits


def normalize_media(value: str) -> str:
    media = value.strip().lower()
    if not re.fullmatch(r"[a-z]{2}\d{2}", media):
        raise RenameError("매체코드는 ja00 같은 영문 2자 + 숫자 2자 형식이어야 합니다.")
    return media


def normalize_page(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise RenameError("페이지 번호를 입력해야 합니다.")
    return digits.zfill(3)


def safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")


def build_file_name(item: RenameInput) -> str:
    date = normalize_date(item.date)
    media = normalize_media(item.media)
    page = normalize_page(item.page)
    stem = item.rule.format(DATE=date, MEDIA=media, PAGE=page)
    stem = safe_name(stem)
    if not stem:
        raise RenameError("파일명 규칙 결과가 비어 있습니다.")
    return f"{stem}{item.path.suffix.lower()}"


def infer_metadata(path: Path, fallback_date: str | None = None) -> dict[str, str]:
    stem = path.stem
    today = datetime.now().strftime("%Y%m%d")
    date_match = DATE_PATTERN.search(stem)
    media_match = MEDIA_CODE_PATTERN.search(stem)
    page_match = PAGE_PATTERN.search(stem)

    return {
        "date": "".join(date_match.groups()) if date_match else fallback_date or today,
        "media": media_match.group(1).lower() if media_match else "",
        "page": normalize_page(page_match.group(1)) if page_match else "001",
    }


def preview_rename(item: RenameInput) -> RenamePreview:
    source = item.path
    if not source.exists():
        return RenamePreview(source, source, "error", "원본 파일을 찾을 수 없습니다.")
    if not source.is_file():
        return RenamePreview(source, source, "error", "파일만 변경할 수 있습니다.")

    try:
        target = source.with_name(build_file_name(item))
    except (RenameError, ValueError) as exc:
        return RenamePreview(source, source, "error", str(exc))

    if target == source:
        return RenamePreview(source, target, "skip", "이미 같은 파일명입니다.")
    if target.exists():
        return RenamePreview(source, target, "conflict", "대상 파일명이 이미 존재합니다.")
    return RenamePreview(source, target, "ready")


def preview_batch(items: Iterable[RenameInput]) -> list[RenamePreview]:
    previews = [preview_rename(item) for item in items]
    seen: set[Path] = set()
    result: list[RenamePreview] = []
    for preview in previews:
        if preview.status == "ready" and preview.target in seen:
            result.append(
                RenamePreview(preview.source, preview.target, "conflict", "같은 대상 파일명이 중복됩니다.")
            )
            continue
        seen.add(preview.target)
        result.append(preview)
    return result


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
                    source_path TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    undone_at TEXT
                )
                """
            )

    def record(self, source: Path, target: Path) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rename_history (source_path, target_path, created_at)
                VALUES (?, ?, ?)
                """,
                (str(source), str(target), datetime.now().isoformat(timespec="seconds")),
            )

    def recent(self, limit: int = 20) -> list[dict[str, str | int | None]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, source_path, target_path, created_at, undone_at
                FROM rename_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_undone(self, history_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE rename_history SET undone_at = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), history_id),
            )


def apply_rename(preview: RenamePreview, history: HistoryStore) -> Path:
    if preview.status != "ready":
        raise RenameError(f"변경할 수 없는 상태입니다: {preview.status}")
    preview.source.rename(preview.target)
    history.record(preview.source, preview.target)
    return preview.target


def undo_last(history: HistoryStore) -> Path:
    rows = [row for row in history.recent(limit=50) if row["undone_at"] is None]
    if not rows:
        raise RenameError("되돌릴 변경 이력이 없습니다.")

    row = rows[0]
    source = Path(str(row["source_path"]))
    target = Path(str(row["target_path"]))
    if not target.exists():
        raise RenameError("되돌릴 대상 파일을 찾을 수 없습니다.")
    if source.exists():
        raise RenameError("원래 파일명이 이미 존재해서 되돌릴 수 없습니다.")

    shutil.move(str(target), str(source))
    history.mark_undone(int(row["id"]))
    return source
