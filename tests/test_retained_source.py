"""Regression of the read-only historical source path, including continuations."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_cover_art import make_song
from yue2_music_director import retained_source as rs, native_draft as nd
from yue2_music_director import ending_audit as ea, release_export as ex, cover_art as ca


class RetainedSourceTests(unittest.TestCase):
    def test_completed_continuation_without_current_parser_or_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            parent=make_song(repo,"one",True)
            before={p:nd._sha(p) for p in parent.rglob("*") if p.is_file()}
            with patch.object(rs.ld.nd,"score_signature",side_effect=AssertionError("replayed parser")), \
                 patch.object(rs.cc,"prepare",side_effect=AssertionError("replayed provider")), \
                 patch.object(rs.ld,"retained_packet",side_effect=AssertionError("recomputed observations")):
                source=rs.load(repo,"one")
                self.assertEqual(source["root"],parent/"continuation-1")
                self.assertEqual(ex.retained(repo,"one")["evidence"],source["evidence"])
                self.assertEqual(ca.track(repo,"one")[1],source["evidence"])
                self.assertIn(b"\r\n",(source["root"]/"production/draft/saved-score.abc").read_bytes())
                with patch.object(ea,"native_song_read",return_value={"id":"one",
                           "metadata":{"job_id":"native-one"},"replay_request":{"truncated":False}}):
                    report=ea.inspect(repo,"one","unused")
                self.assertEqual(report["score"]["score_seconds"],2)
            self.assertEqual(before,{p:nd._sha(p) for p in parent.rglob("*") if p.is_file()})

    def test_mutated_creative_and_continuation_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            for job,path in (("one","creative-result.json"),("two","production/plan-result.json")):
                parent=make_song(repo,job,True)
                target=parent/path
                changed=nd.read(target)
                if job=="one":
                    changed["composition"]["concept"]="tampered concept"
                else:
                    changed["id"]="different"
                nd.atomic_write(target,changed)
                with self.assertRaises(ValueError):
                    rs.load(repo,job)

    def test_ambiguous_root_and_altered_audio_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            parent=make_song(repo,"one",True)
            (parent/"result.json").write_bytes((parent/"continuation-1/result.json").read_bytes())
            with self.assertRaisesRegex(ValueError,"Exactly one"):
                rs.load(repo,"one")
            (parent/"result.json").unlink()
            (parent/"fixture.flac").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                rs.load(repo,"one")

