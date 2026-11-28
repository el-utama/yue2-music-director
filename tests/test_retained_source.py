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
                 patch.object(rs.ld.nd,"request_for",side_effect=AssertionError("replayed request builder")), \
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



    def test_approved_audio_recovery_remains_a_valid_historical_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            parent=make_song(repo,"recovered",True)
            root=parent/"continuation-1"
            draft=root/"production/draft"
            journal=nd.read(draft/"journal_song.json")
            report=nd.read(draft/"report.json")
            approved=journal["audio_sha256"]
            journal["audio_sha256"]="a"*64
            nd.atomic_write(draft/"journal_song.json",journal)
            nd.atomic_write(draft/"acoustic.json",report["acoustic"])
            nd.atomic_write(draft/"submission-response.json",{"job_id":journal["job_id"]})
            # Construct a synthetic pre-ASR recovery sidecar and its final report.
            (draft/"report.json").unlink()
            record=nd.audio_recovery_record(draft,journal,approved,create=True)
            report["audio_identity_recovery"]=record
            report["status"]="technical_review_required"
            nd.atomic_write(draft/"report.json",report)
            result=nd.read(root/"result.json")
            result["native_report_sha256"]=nd._sha(draft/"report.json")
            nd.atomic_write(root/"result.json",result)
            before={p:nd._sha(p) for p in parent.rglob("*") if p.is_file()}
            source=rs.load(repo,"recovered")
            self.assertEqual(source["row"]["audio_sha256"],approved)
            self.assertEqual(source["report"]["audio_identity_recovery"],record)
            self.assertEqual(ex.retained(repo,"recovered")["evidence"],source["evidence"])
            self.assertEqual(before,{p:nd._sha(p) for p in before})
            self.assertEqual(nd.read(draft/"journal_song.json")["audio_sha256"],"a"*64)
            changed={**record,"original_waveform_equivalence_verified":True}
            nd.atomic_write(draft/"audio-identity-recovery.json",changed)
            with self.assertRaises(ValueError):
                rs.load(repo,"recovered")
