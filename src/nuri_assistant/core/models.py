from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_RULE = "{DATE}_{MEDIA}_{PAGE}"


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
