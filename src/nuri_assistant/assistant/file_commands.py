from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from ..core.models import DEFAULT_RULE


@dataclass(frozen=True)
class FileAssistantPlan:
    """A non-destructive interpretation of a user's file-organizing request."""

    command: str
    date: str
    media: str
    page: str
    rule: str
    recursive: bool
    needs_media: bool


_DATE_PATTERN = re.compile(r"(20\d{2})[-./]?(0[1-9]|1[0-2])[-./]?([0-2]\d|3[01])")
_MEDIA_PATTERN = re.compile(r"(?i)(?<![a-z0-9])([a-z]{2}\d{2})(?![a-z0-9])")
_PAGE_PATTERN = re.compile(r"(?:p(?:age)?|페이지)\s*(\d{1,4})|(?:(\d{1,4})\s*부터)", re.IGNORECASE)


def interpret_file_command(command: str) -> FileAssistantPlan:
    """Extract safe rename settings from a Korean or English natural-language command.

    The result deliberately contains no execute flag. The caller must show a preview
    and ask for confirmation before changing files.
    """

    text = command.strip()
    date_match = _DATE_PATTERN.search(text)
    media_match = _MEDIA_PATTERN.search(text)
    page_match = _PAGE_PATTERN.search(text)

    date = "".join(date_match.groups()) if date_match else datetime.now().strftime("%Y%m%d")
    media = media_match.group(1).lower() if media_match else ""
    page = next((group for group in page_match.groups() if group), "001") if page_match else "001"
    lowered = text.lower()
    recursive = any(token in lowered for token in ("하위", "재귀", "subfolder", "recursive"))

    rule = DEFAULT_RULE
    if any(token in lowered for token in ("매체-날짜", "media-date", "media date")):
        rule = "{MEDIA}-{DATE}-{PAGE}"
    elif any(token in lowered for token in ("날짜-매체", "date-media", "date media")):
        rule = "{DATE}-{MEDIA}-p{PAGE}"

    return FileAssistantPlan(
        command=text,
        date=date,
        media=media,
        page=str(int(page)).zfill(3),
        rule=rule,
        recursive=recursive,
        needs_media=not bool(media),
    )
