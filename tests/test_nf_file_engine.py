from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.nf_file_engine import (
    DEFAULT_RULE,
    HistoryStore,
    RenameInput,
    WorkProfile,
    apply_batch_rename,
    apply_rename,
    build_file_name,
    export_preview_csv,
    infer_metadata,
    load_profiles,
    preview_batch,
    preview_rename,
    scan_files,
    save_profile,
    undo_last,
    undo_last_batch,
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

    def test_scan_files_filters_supported_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pdf").write_text("pdf", encoding="utf-8")
            (root / "b.txt").write_text("text", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "c.jpg").write_text("image", encoding="utf-8")

            shallow = scan_files(root)
            recursive = scan_files(root, recursive=True)

            self.assertEqual([path.name for path in shallow], ["a.pdf"])
            self.assertEqual([path.name for path in recursive], ["a.pdf", "c.jpg"])

    def test_export_preview_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "raw.pdf"
            output = root / "preview.csv"
            source.write_text("pdf", encoding="utf-8")
            previews = preview_batch([RenameInput(source, "20260628", "ja00", "001")])

            export_preview_csv(previews, output)

            text = output.read_text(encoding="utf-8-sig")
            self.assertIn("source_path,target_path,target_name,status,message", text)
            self.assertIn("20260628_ja00_001.pdf", text)

    def test_apply_and_undo_batch_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.pdf"
            second = root / "second.pdf"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            history = HistoryStore(root / "history.sqlite3")
            previews = preview_batch(
                [
                    RenameInput(first, "20260628", "ja00", "001"),
                    RenameInput(second, "20260628", "ja00", "002"),
                ]
            )

            changed = apply_batch_rename(previews, history)
            restored = undo_last_batch(history)

            self.assertEqual(len(changed), 2)
            self.assertFalse((root / "20260628_ja00_001.pdf").exists())
            self.assertFalse((root / "20260628_ja00_002.pdf").exists())
            self.assertEqual({path.name for path in restored}, {"first.pdf", "second.pdf"})
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_save_and_load_work_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            profile = WorkProfile(
                name="daily",
                date="20260712",
                media="ja00",
                page="003",
                rule="{MEDIA}-{DATE}-{PAGE}",
                recursive=True,
            )

            save_profile(path, profile)
            profiles = load_profiles(path)

            self.assertIn("daily", profiles)
            self.assertEqual(profiles["daily"].media, "ja00")
            self.assertEqual(profiles["daily"].rule, "{MEDIA}-{DATE}-{PAGE}")
            self.assertTrue(profiles["daily"].recursive)


if __name__ == "__main__":
    unittest.main()
