from __future__ import annotations

import re


MEDIA_CODE_PATTERN = re.compile(r"(?i)(?<![a-z0-9])([a-z]{2}\d{2})(?![a-z0-9])")
DATE_PATTERN = re.compile(r"(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?([0-2]\d|3[01])")
PAGE_PATTERN = re.compile(r"(?i)(?:page|p|면|_)(\d{1,3})(?=\D|$)")
