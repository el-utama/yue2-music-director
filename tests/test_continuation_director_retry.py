import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_cover_art import make_song, MusicProvider
from yue2_music_director import autonomous as au, retained_source as rs, native_draft as nd


URL="http://127.0.0.1:8791/mcp"


class RecordingProvider(MusicProvider):
    def __init__(self,job,fail=False):
        super().__init__(job)
        self.calls=[]
        self.fail=fail
    def complete(self,role,prompt,data):
        self.calls.append(role)
        if role!="director":
            raise AssertionError("Replayed upstream text stage")
        if self.fail:
            raise ValueError("simulated unavailable Director")
        return super().complete(role,prompt,data)


class ContinuationDirectorRetryTests(unittest.TestCase):
    def fixture(self,repo):
        parent=make_song(repo,"one",True)
        root=parent/"continuation-1"
        # Fixture simulates a successful native/listening workflow and unresolved
        # Director attempt before a result was written.
        (root/"director.json").unlink()
        (root/"result.json").unlink()
        return parent,root

    def test_exact_child_only_retry_without_native_or_listening(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            parent,root=self.fixture(repo)
            before={p:nd._sha(p) for p in parent.rglob("*") if p.is_file()}
            provider=RecordingProvider("one")
            with patch.object(au.artist_run,"run",side_effect=AssertionError("native replay")), \
                 patch.object(au.cc,"prepare",side_effect=AssertionError("creative replay")), \
                 patch.object(au.ld,"listen",side_effect=AssertionError("listening replay")), \
                 patch.object(au.nd,"request_for",side_effect=AssertionError("request replay")), \
                 patch.object(au.nd,"score_signature",side_effect=AssertionError("parser replay")):
                with self.assertRaisesRegex(ValueError,"confirm-run"):
                    au.continue_plan(repo,"one",URL,retry_role="director",provider_factory=lambda:provider)
                self.assertEqual(au.continue_plan(repo,"one",URL,confirm=True,retry_role="director",
                                                  provider_factory=lambda:provider),0)
                self.assertEqual(provider.calls,["director"])
                self.assertEqual(rs.load(repo,"one")["root"],root)
                self.assertEqual(nd.read(root/"director.retry-1.attempt.json"),nd.read(root/"director.attempt.json"))
                self.assertFalse(nd.read(root/"result.json")["automatic_acceptance"])
                self.assertEqual(before,{p:nd._sha(p) for p in before})
                with self.assertRaisesRegex(ValueError,"Only one"):
                    au.continue_plan(repo,"one",URL,confirm=True,retry_role="director",
                                     provider_factory=lambda:provider)
                self.assertEqual(provider.calls,["director"])

    def test_failed_retry_is_exhausted_and_other_roles_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            _,root=self.fixture(repo)
            provider=RecordingProvider("one",fail=True)
            with self.assertRaisesRegex(ValueError,"Only the child Director"):
                au.continue_plan(repo,"one",URL,confirm=True,retry_role="composer",
                                 provider_factory=lambda:provider)
            with self.assertRaisesRegex(ValueError,"unavailable Director"):
                au.continue_plan(repo,"one",URL,confirm=True,retry_role="director",
                                 provider_factory=lambda:provider)
            self.assertTrue((root/"director.retry-1.attempt.json").is_file())
            self.assertFalse((root/"result.json").exists())
            with self.assertRaisesRegex(ValueError,"Only one"):
                au.continue_plan(repo,"one",URL,confirm=True,retry_role="director",
                                 provider_factory=lambda:provider)
            self.assertEqual(provider.calls,["director"])

    def test_tampered_source_or_attempt_prevents_provider_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            parent,root=self.fixture(repo)
            provider=RecordingProvider("one")
            attempt=nd.read(root/"director.attempt.json")
            original=attempt.copy()
            attempt["prompt"]="changed"
            nd.atomic_write(root/"director.attempt.json",attempt)
            with self.assertRaisesRegex(ValueError,"inputs or contract"):
                au.continue_plan(repo,"one",URL,confirm=True,retry_role="director",
                                 provider_factory=lambda:provider)
            nd.atomic_write(root/"director.attempt.json",original)
            (parent/"fixture.flac").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                au.continue_plan(repo,"one",URL,confirm=True,retry_role="director",
                                 provider_factory=lambda:provider)
            self.assertEqual(provider.calls,[])
