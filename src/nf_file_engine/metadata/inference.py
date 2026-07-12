from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..core.naming import normalize_page

from .patterns import DATE_PATTERN, MEDIA_CODE_PATTERN, PAGE_PATTERN


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
