from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.nf_file_engine import (
    DEFAULT_RULE,
    HistoryStore,
    RenameInput,
    apply_rename,
    build_file_name,
    infer_metadata,
    preview_batch,
    preview_rename,
    undo_last,
)


class RenameEngineTest(unittest.TestCase):
    def test_build_file_name_with_default_rule(self) -> None:
        item = RenameInput(Path("sample.PDF"), "2026-06-28", "JA00", "7", DEFAULT_RULE)

        self.assertEqual(build_file_name(item), "20260628_ja00_007.pdf")

    def test_infer_metadata_from_existing_name(self) -> None:
        metadata = infer_metadata(Path("20260628_ja00_p12.pdf"))

        self.assertEqual(metadata["date"], "20260628")
        self.assertEqual(metadata["media"], "ja00")
        self.assertEqual(metadata["page"], "012")

    def test_preview_detects_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            target = root / "20260628_ja00_001.pdf"
            source.write_text("source", encoding="utf-8")
            target.write_text("target", encoding="utf-8")

            preview = preview_rename(RenameInput(source, "20260628", "ja00", "001"))

            self.assertEqual(preview.status, "conflict")

    def test_preview_batch_detects_duplicate_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.pdf"
            second = root / "second.pdf"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")

            previews = preview_batch(
                [
                    RenameInput(first, "20260628", "ja00", "001"),
                    RenameInput(second, "20260628", "ja00", "001"),
                ]
            )

            self.assertEqual(previews[0].status, "ready")
            self.assertEqual(previews[1].status, "conflict")

    def test_apply_and_undo_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "raw.pdf"
            source.write_text("pdf", encoding="utf-8")
            history = HistoryStore(root / "history.sqlite3")
            preview = preview_rename(RenameInput(source, "20260628", "ja00", "001"))

            target = apply_rename(preview, history)
            restored = undo_last(history)

            self.assertFalse(target.exists())
            self.assertEqual(restored, source)
            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
