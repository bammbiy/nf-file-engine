from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import RenameError, RenameInput, RenamePreview
from .naming import build_file_name


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
