from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yue2_music_director import autonomous as au, autonomous_knowledge as ak
from yue2_music_director import knowledge_bank as kb, native_draft as nd
from test_autonomous import Provider

ROOT = Path(__file__).resolve().parents[1]


class AutonomousKnowledgeTests(unittest.TestCase):
    def test_numeric_only_context_consent_and_frozen_resume(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(au.artist_run, "run") as native:
            repo = Path(temp)
            database = repo / "local/knowledge-bank.sqlite"
            kb.build(ROOT / "data/knowledge_bank", database)
            provider = Provider(stop=True)
            seen = {}
            original = provider.complete
            def complete(role, prompt, data):
                seen[role] = data
                return original(role, prompt, data)
            provider.complete = complete
            args = (repo, "knowledge", "A quiet goodbye", "en", 150, "http://127.0.0.1:8791/mcp")
            self.assertEqual(au.launch(*args, knowledge_query="Schubert", provider_factory=lambda:provider), 0)
            self.assertFalse((repo / "results").exists())
            self.assertEqual(provider.calls, [])
            with self.assertRaisesRegex(ValueError, "together"):
                au.launch(*args, knowledge_query="Schubert", confirm=True, provider_factory=lambda:provider)
            self.assertEqual(provider.calls, [])
            self.assertEqual(au.launch(*args, knowledge_query="Schubert", confirm=True,
                             confirm_knowledge_context=True, provider_factory=lambda:provider), 2)
            for role in ("composer", "lyricist"):
                context = seen[role]["knowledge_context"]
                self.assertEqual(set(context), {"schema", "guidance", "observations"})
                self.assertTrue(context["observations"])
                self.assertNotIn("Schubert", str(context))
                self.assertTrue(all(v is None or type(v) in (int, float)
                                    for row in context["observations"] for v in row.values()))
            self.assertNotIn("knowledge_context", seen["reviewer"])
            selected = nd.read(repo / "results/autonomous/knowledge/job.json")["knowledge_context"]
            self.assertEqual(selected["snapshot"]["query"], "Schubert")
            database.unlink()
            with self.assertRaisesRegex(ValueError, "requires --confirm-knowledge-context"):
                au.launch(*args, confirm=True, provider_factory=lambda:provider)
            with self.assertRaisesRegex(ValueError, "Retained knowledge query differs"):
                au.launch(*args, confirm=True, knowledge_query="home", confirm_knowledge_context=True,
                          provider_factory=lambda:provider)
            self.assertEqual(au.launch(*args, confirm=True, confirm_knowledge_context=True,
                             provider_factory=lambda:provider), 2)
            self.assertEqual(provider.calls, ["composer", "lyricist", "reviewer"])
            native.assert_not_called()
            with self.assertRaisesRegex(ValueError, "checksum"):
                ak.validate({**selected, "sha256": "0" * 64})

    def test_empty_query_result_and_invalid_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            kb.build(ROOT / "data/knowledge_bank", repo / "local/knowledge-bank.sqlite")
            args = (repo, "empty", "A quiet goodbye", "en", 150, "http://127.0.0.1:8791/mcp")
            with self.assertRaisesRegex(ValueError, "No historical knowledge matches"):
                au.launch(*args, knowledge_query="zzzznonexistent")
            with self.assertRaisesRegex(ValueError, "requires --confirm-run"):
                au.launch(*args, confirm_knowledge_context=True)
            self.assertFalse((repo / "results").exists())

    def test_cannot_add_context_to_existing_job(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(au.artist_run, "run") as native:
            repo = Path(temp)
            p = Provider(stop=True)
            args = (repo, "legacy", "A quiet goodbye", "en", 150, "http://127.0.0.1:8791/mcp")
            self.assertEqual(au.launch(*args, confirm=True, provider_factory=lambda:p), 2)
            with self.assertRaisesRegex(ValueError, "Cannot add knowledge"):
                au.launch(*args, confirm=True, knowledge_query="home", confirm_knowledge_context=True,
                          provider_factory=lambda:p)
            self.assertEqual(p.calls, ["composer", "lyricist", "reviewer"])
            native.assert_not_called()
