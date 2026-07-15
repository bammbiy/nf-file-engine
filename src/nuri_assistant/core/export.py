from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import RenamePreview


def export_preview_csv(previews: Iterable[RenamePreview], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["source_path", "target_path", "target_name", "status", "message"])
        for preview in previews:
            writer.writerow(
                [
                    str(preview.source),
                    str(preview.target),
                    preview.target.name,
                    preview.status,
                    preview.message,
                ]
            )
    return output_path
