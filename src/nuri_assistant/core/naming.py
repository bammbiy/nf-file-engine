from __future__ import annotations

import re
from datetime import datetime

from .models import RenameError, RenameInput


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
