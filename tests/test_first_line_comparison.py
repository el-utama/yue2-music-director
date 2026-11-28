from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_cover_art import make_song
from yue2_music_director import first_line_comparison as compare, native_draft as nd


class FirstLineComparisonTests(unittest.TestCase):
    def test_replace_only_opening_lyric_preserving_line_endings(self):
        lyrics = "[Intro]\r\n\r\n[Verse 1]\r\n  Opening words\r\nKeep my line\r\n[Outro]\r\n"
        self.assertEqual(compare.revised_lyrics(lyrics, ("New phrase", "Another phrase")),
                         "[Intro]\r\n\r\n[Verse 1]\r\nNew phrase\r\nAnother phrase\r\nKeep my line\r\n[Outro]\r\n")
        for invalid in (("New phrase", "[Chorus]"), ("Two\nlines", "Other")):
            with self.assertRaises(ValueError):
                compare.revised_lyrics(lyrics, invalid)

    def test_exact_retained_score_preview_and_confirmed_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            parent = make_song(repo, "one")
            production = parent / "production"
            draft = production / "draft"
            configuration = {"fixture": True}
            for path in (production / "journal_plan.json", draft / "journal_song.json"):
                journal = nd.read(path)
                journal["configuration" if path.name == "journal_plan.json" else "reference_configuration"] = configuration
                nd.atomic_write(path, journal)
            nd.atomic_write(draft / "artist-policy.json",
                            {"intent": nd.read(parent / "intent.json"), "planner_configuration": configuration})
            before = {p: p.read_bytes() for p in parent.rglob("*") if p.is_file()}
            args = (repo, "one", ("New phrase", "Pause here"), "http://127.0.0.1:8791/mcp")
            root = parent / "first-line-comparison"
            fake = {"song_id": "candidate", "audio": "candidate.flac", "acoustic": {"duration_seconds": 2}}
            with patch.object(nd, "execute", return_value=fake) as execute:
                self.assertEqual(compare.launch(*args), 0)
                self.assertFalse(root.exists())
                execute.assert_not_called()
                self.assertEqual(compare.launch(*args, confirm=True), 0)
                brief = execute.call_args.args[0]
                self.assertEqual(brief["lyrics"], "[Verse]\nNew phrase\nPause here")
                self.assertEqual(execute.call_args.kwargs["abc"], nd.read(draft / "request.json")["abc"])
                self.assertEqual(execute.call_args.kwargs["expected_configuration"], configuration)
                with self.assertRaisesRegex(ValueError, "Retained comparison differs"):
                    compare.launch(repo, "one", ("Different words", "Pause here"), args[-1], confirm=True)
                self.assertEqual(execute.call_count, 1)
            self.assertEqual(before, {p: p.read_bytes() for p in before})
