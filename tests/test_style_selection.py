from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from yue2_music_director import autonomous as au, native_draft as nd, style_selection as ss
from test_autonomous import Provider

ROOT = Path(__file__).resolve().parents[1]

class StyleSelectionTests(unittest.TestCase):
    def test_explicit_style_preview_and_frozen_resume(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(au.artist_run, "run") as native:
            repo = Path(temp)
            shutil.copytree(ROOT / "data/style_library", repo / "data/style_library")
            provider = Provider(stop=True)
            seen = {}
            original = provider.complete
            def complete(role, prompt, data):
                seen[role] = data
                return original(role, prompt, data)
            provider.complete = complete
            args = (repo, "preset", "A quiet goodbye", "en", 150, "http://127.0.0.1:8791/mcp")
            self.assertEqual(au.launch(*args, style_id="folk-001", provider_factory=lambda:provider), 0)
            self.assertEqual(provider.calls, [])
            self.assertFalse((repo / "results").exists())
            self.assertEqual(au.launch(*args, style_id="folk-001", confirm=True, provider_factory=lambda:provider), 2)
            native.assert_not_called()
            self.assertEqual(seen["composer"]["style_recipe"]["genre"], "folk")
            self.assertNotIn("style_recipe", seen["lyricist"])
            self.assertNotIn("style_recipe", seen["reviewer"])
            saved = nd.read(repo / "results/autonomous/preset/job.json")["style_recipe"]
            self.assertEqual(saved["id"], "folk-001")
            shutil.rmtree(repo / "data/style_library")
            self.assertEqual(au.launch(*args, confirm=True, provider_factory=lambda:provider), 2)
            self.assertEqual(provider.calls, ["composer", "lyricist", "reviewer"])
            with self.assertRaisesRegex(ValueError, "Retained style ID differs"):
                au.launch(*args, style_id="folk-002", confirm=True, provider_factory=lambda:provider)
            with self.assertRaises(ValueError):
                ss.validate({**saved, "style": "modified recipe"})
            native.assert_not_called()

    def test_reject_style_added_to_existing_job(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(au.artist_run, "run") as native:
            repo = Path(temp)
            provider = Provider(stop=True)
            args = (repo, "legacy", "A quiet goodbye", "en", 150, "http://127.0.0.1:8791/mcp")
            self.assertEqual(au.launch(*args, confirm=True, provider_factory=lambda:provider), 2)
            with self.assertRaisesRegex(ValueError, "Cannot add a style"):
                au.launch(*args, style_id="folk-001", confirm=True, provider_factory=lambda:provider)
            self.assertEqual(provider.calls, ["composer", "lyricist", "reviewer"])
            native.assert_not_called()
