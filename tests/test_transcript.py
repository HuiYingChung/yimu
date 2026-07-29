import os
import tempfile
import unittest
from pathlib import Path

import config
from transcript import TranscriptRecorder, load_latest_session


class TranscriptSessionTests(unittest.TestCase):
    def setUp(self):
        self._original = {
            "TRANSCRIPT_DIR": config.TRANSCRIPT_DIR,
            "TRANSCRIPT_CONTENT": config.TRANSCRIPT_CONTENT,
        }
        self._temp_dir = tempfile.TemporaryDirectory()
        config.TRANSCRIPT_DIR = self._temp_dir.name
        config.TRANSCRIPT_CONTENT = "both"

    def tearDown(self):
        for name, value in self._original.items():
            setattr(config, name, value)
        self._temp_dir.cleanup()

    def test_snapshot_prefers_source_and_keeps_translation(self):
        recorder = TranscriptRecorder()
        recorder.add_source("A source sentence.")
        recorder.add_translation("一段譯文。")
        recorder.close()

        session = recorder.snapshot()

        self.assertEqual(session.source_text, "A source sentence.")
        self.assertEqual(session.translation_text, "一段譯文。")
        self.assertEqual(session.summary_text, "A source sentence.")
        self.assertEqual(session.character_count, len("A source sentence."))
        self.assertTrue(Path(session.transcript_path).exists())

    def test_flush_pending_does_not_end_or_split_the_session(self):
        recorder = TranscriptRecorder()
        recorder.add_source("First sentence.")
        original_path = recorder.path

        recorder.flush_pending()
        recorder.add_source("Second sentence.")
        recorder.close()

        self.assertEqual(recorder.path, original_path)
        content = Path(recorder.path).read_text(encoding="utf-8")
        self.assertIn("First sentence.", content)
        self.assertIn("Second sentence.", content)

    def test_translation_only_does_not_retain_hidden_source_text(self):
        config.TRANSCRIPT_CONTENT = "translation"
        recorder = TranscriptRecorder()
        recorder.add_source("Private source.")
        recorder.add_translation("保留的譯文。")
        recorder.close()

        session = recorder.snapshot()

        self.assertEqual(session.source_text, "")
        self.assertEqual(session.summary_text, "保留的譯文。")

    def test_latest_saved_transcript_can_be_retried_after_restart(self):
        older = Path(self._temp_dir.name) / "yimu_20260729_100000.md"
        latest = Path(self._temp_dir.name) / "yimu_20260729_110000.md"
        summary = Path(
            self._temp_dir.name) / "yimu_20260729_120000_summary.md"
        older.write_text("older", encoding="utf-8")
        latest.write_text("# 譯幕逐字稿\n\nlatest", encoding="utf-8")
        summary.write_text("must be ignored", encoding="utf-8")
        os.utime(older, (100, 100))
        os.utime(latest, (200, 200))
        os.utime(summary, (300, 300))

        session = load_latest_session(self._temp_dir.name)

        self.assertEqual(session.transcript_path, str(latest))
        self.assertIn("latest", session.summary_text)


if __name__ == "__main__":
    unittest.main()
