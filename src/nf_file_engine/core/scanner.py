from __future__ import annotations

from pathlib import Path


DEFAULT_EXTENSIONS = (".pdf", ".doc", ".docx", ".hwp", ".hwpx", ".jpg", ".jpeg", ".png", ".tif", ".tiff")


def scan_files(folder: Path, recursive: bool = False, extensions: tuple[str, ...] = DEFAULT_EXTENSIONS) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"폴더가 아닙니다: {folder}")

    normalized = {extension.lower() for extension in extensions}
    pattern = "**/*" if recursive else "*"
    files = [
        path
        for path in folder.glob(pattern)
        if path.is_file() and path.suffix.lower() in normalized
    ]
    return sorted(files, key=lambda path: path.name.lower())
