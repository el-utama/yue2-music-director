import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from yue2_music_director import listening_director as ld


class ListeningDirectorTests(unittest.TestCase):
    def test_partial_and_duplicate_observations_are_not_invented(self):
        status, rows = ld.parse_observations(
            "VOCAL: soft voice\nVOCAL: loud voice\nINSTRUMENTS: piano\nTAIL: unknown\n")
        self.assertEqual(status, "partial_unvalidated")
        by_field = {r["field"]: r for r in rows}
        self.assertIsNone(by_field["VOCAL"]["observation"])
        self.assertIsNone(by_field["TAIL"]["observation"])
        self.assertEqual(by_field["INSTRUMENTS"]["observation"], "piano")
        self.assertIsNone(by_field["CHANGES"]["observation"])

    def test_demo_is_valid_direct_native_and_plan_is_offline(self):
        repo = Path(__file__).resolve().parents[1]
        brief, intent = ld.inputs(repo, True)
        self.assertEqual(ld.artist_run.route_for(intent), "direct_native")
        self.assertNotIn(brief["title"], ld.PROMPT)
        self.assertNotIn(brief["style"], ld.PROMPT)
        with patch.object(ld.artist_run, "run") as run, patch.object(ld, "Client") as client:
            self.assertEqual(ld.launch(repo, "unused", demo=True), 0)
            run.assert_not_called()
            client.assert_not_called()

    def test_contract_is_immutable_and_contains_no_intent(self):
        row = {"audio_sha256": "fixture", "acoustic": {"duration_seconds": 190}}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "listening"
            a = ld.freeze(out, row)
            self.assertEqual(a, ld.freeze(out, row))
            self.assertNotIn("brief", a)
            self.assertNotIn("intent", a)
            with self.assertRaises(ValueError):
                ld.freeze(out, {**row, "audio_sha256": "changed"})

    def test_packet_marks_only_final_excerpt_and_never_accepts(self):
        row = {"audio_sha256": "fixture", "audio": "a.flac",
               "acoustic": {"duration_seconds": 200}, "lyric_screen": {}}
        evidence = [{"start_seconds": 0, "duration_seconds": 100},
                    {"start_seconds": 100, "duration_seconds": 100}]
        p = ld.review_packet({"title": "song"}, {}, row, {}, evidence)
        self.assertFalse(p["observations"][0]["contains_recording_end"])
        self.assertTrue(p["observations"][1]["contains_recording_end"])
        self.assertFalse(p["revision_authorized"])
        self.assertFalse(p["automatic_acceptance"])

    def test_lock_is_exclusive_and_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".active"
            with ld.lock(p):
                with self.assertRaises(FileExistsError):
                    with ld.lock(p):
                        self.fail("Unexpected acquired lock")
                self.assertTrue(p.exists())
            self.assertFalse(p.exists())
