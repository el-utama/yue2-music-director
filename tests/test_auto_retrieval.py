from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yue2_music_director import autonomous as au, autonomous_knowledge as ak
from yue2_music_director import knowledge_bank as kb, native_draft as nd
from test_autonomous import Provider

ROOT = Path(__file__).resolve().parents[1]


class AutoRetrievalTests(unittest.TestCase):
    def test_lexical_query_is_bounded_and_filters_common_words(self):
        self.assertEqual(ak.brief_query("Buatkan lagu tentang Home and snow, home!"), "home snow")
        self.assertEqual(ak.brief_query("Please make a song"), "")
        self.assertEqual(len(ak.brief_query(" ".join("word"+chr(97+i) for i in range(20))).split()), 12)

    def test_matched_and_abstained_jobs_freeze_local_selection(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(au.artist_run, "run") as native:
            repo = Path(temp)
            db = repo / "local/knowledge-bank.sqlite"
            kb.build(ROOT / "data/knowledge_bank", db)
            for job, request, status in (("match", "A song about home", "matched"),
                                         ("empty", "A song about zzzznonexistent", "no_matches"),
                                         ("no-terms", "Please make a song", "no_terms")):
                provider = Provider(stop=True)
                seen = {}
                original = provider.complete
                def complete(role, prompt, data):
                    seen[role] = data
                    return original(role, prompt, data)
                provider.complete = complete
                args = (repo, job, request, "en", 150, "http://127.0.0.1:8791/mcp")
                self.assertEqual(au.launch(*args, knowledge_auto=True, provider_factory=lambda:provider), 0)
                self.assertEqual(provider.calls, [])
                with self.assertRaisesRegex(ValueError, "together"):
                    au.launch(*args, confirm=True, knowledge_auto=True, provider_factory=lambda:provider)
                self.assertEqual(au.launch(*args, confirm=True, knowledge_auto=True,
                                 confirm_knowledge_context=True, provider_factory=lambda:provider), 2)
                identity = nd.read(repo / "results/autonomous" / job / "job.json")
                chosen = identity["knowledge_context"]
                self.assertEqual(chosen["status"], status)
                for role in ("composer", "lyricist"):
                    self.assertEqual("knowledge_context" in seen[role], status == "matched")
                self.assertNotIn("knowledge_context", seen["reviewer"])
                with patch.object(ak, "select_auto", side_effect=AssertionError("must not reretrieve")):
                    with self.assertRaisesRegex(ValueError, "requires --confirm-knowledge-context"):
                        au.launch(*args, confirm=True, provider_factory=lambda:provider)
                    self.assertEqual(au.launch(*args, confirm=True, confirm_knowledge_context=True,
                                     provider_factory=lambda:provider), 2)
                self.assertEqual(provider.calls, ["composer", "lyricist", "reviewer"])
                with self.assertRaisesRegex(ValueError, "mode differs"):
                    au.launch(*args, confirm=True, knowledge_query="home",
                              confirm_knowledge_context=True, provider_factory=lambda:provider)
            native.assert_not_called()

    def test_manual_auto_conflict_stops_without_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "not both"):
                au.launch(Path(temp), "job", "A song about home", "en", 150,
                          "http://127.0.0.1:8791/mcp", knowledge_auto=True, knowledge_query="home")
