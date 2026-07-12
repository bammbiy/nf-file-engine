from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ..storage.history import HistoryStore
from .models import RenameError, RenamePreview


def apply_rename(preview: RenamePreview, history: HistoryStore) -> Path:
    if preview.status != "ready":
        raise RenameError(f"변경할 수 없는 상태입니다: {preview.status}")
    preview.source.rename(preview.target)
    history.record(preview.source, preview.target)
    return preview.target


def apply_batch_rename(previews: list[RenamePreview], history: HistoryStore) -> list[Path]:
    ready = [preview for preview in previews if preview.status == "ready"]
    if not ready:
        raise RenameError("변경 가능한 파일이 없습니다.")

    batch_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    changed: list[RenamePreview] = []
    try:
        for preview in ready:
            preview.source.rename(preview.target)
            history.record(preview.source, preview.target, batch_id=batch_id)
            changed.append(preview)
    except Exception as exc:
        for preview in reversed(changed):
            if preview.target.exists() and not preview.source.exists():
                shutil.move(str(preview.target), str(preview.source))
        raise RenameError(f"배치 변경 중 오류가 발생해 이전 변경을 되돌렸습니다: {exc}") from exc

    return [preview.target for preview in ready]


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


def undo_last_batch(history: HistoryStore) -> list[Path]:
    rows = history.latest_active_batch()
    if not rows:
        raise RenameError("되돌릴 배치 이력이 없습니다.")

    batch_id = rows[0].batch_id
    for row in rows:
        source = Path(row.source_path)
        target = Path(row.target_path)
        if not target.exists():
            raise RenameError(f"되돌릴 대상 파일을 찾을 수 없습니다: {target.name}")
        if source.exists():
            raise RenameError(f"원래 파일명이 이미 존재해서 되돌릴 수 없습니다: {source.name}")

    restored: list[Path] = []
    for row in rows:
        source = Path(row.source_path)
        target = Path(row.target_path)
        shutil.move(str(target), str(source))
        restored.append(source)

    history.mark_batch_undone(batch_id)
    return restored
