import tempfile
from pathlib import Path
import unittest
from yue2_music_director import creative_core as cc, lyricist
from yue2_music_director.creative_provider import TextProvider, strict_json


class Fake:
    def __init__(self, fail=None):
        self.calls=[]
        self.fail=fail
    def identity(self):
        return {"models":"fake"}
    def complete(self,role,prompt,data):
        self.calls.append(role)
        if role==self.fail:
            raise ValueError("Simulated provider failure")
        return {"composer":{"title":"A Key","concept":"Moving out","emotional_arc":"loss to relief",
                "performance":"soft guitar","style":"English, folk, gentle alto vocals, acoustic guitar"},
                "lyricist":{"lyrics":"[Verse]\nI left the key beside the door\n[Chorus]\nI do not live there anymore"},
                "reviewer":{"decision":"retain","rationale":"Coherent"}}[role]


class CreativeCoreTests(unittest.TestCase):
    def test_checkpoint_and_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Fake()
            args=(Path(tmp),"one","A quiet goodbye","en",150)
            cc.launch(*args,provider_factory=lambda:f)
            self.assertEqual(f.calls,[])
            cc.launch(*args,confirm_text=True,provider_factory=lambda:f)
            cc.launch(*args,confirm_text=True,provider_factory=lambda:f)
            self.assertEqual(f.calls,["composer","lyricist","reviewer"])

    def test_lyricist_failure_does_not_replay_composer_or_call_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Fake("lyricist")
            args=(Path(tmp),"one","A quiet goodbye","en",150)
            with self.assertRaises(ValueError):
                cc.launch(*args,confirm_text=True,provider_factory=lambda:f)
            self.assertTrue((Path(tmp)/"results/creative/one/composer.json").is_file())
            f.fail=None
            with self.assertRaises(ValueError):
                cc.launch(*args,confirm_text=True,provider_factory=lambda:f)
            self.assertEqual(f.calls,["composer","lyricist"])

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            strict_json('{"x":1,"x":2}')
        with self.assertRaises(ValueError):
            TextProvider("http://example.com/chat/completions","secret",{})
        with self.assertRaises(ValueError):
            lyricist.validate({"lyrics":"untagged lyrics"})

    def test_opt_in_knowledge_freezes_numeric_payload_and_resume(self):
        from yue2_music_director import knowledge_bank as kb
        from yue2_music_director import native_draft as nd
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            db = repo/"local/knowledge-bank.sqlite"
            kb.build(Path(__file__).resolve().parents[1]/"data/knowledge_bank", db)
            f = Fake()
            seen = {}
            original = f.complete
            def complete(role, prompt, data):
                seen[role] = data
                return original(role, prompt, data)
            f.complete = complete
            args = (repo, "one", "A quiet goodbye", "en", 150)
            cc.launch(*args, knowledge_query="home", provider_factory=lambda:f)
            self.assertEqual(f.calls, [])
            with self.assertRaises(ValueError):
                cc.launch(*args, confirm_text=True, knowledge_query="home", provider_factory=lambda:f)
            self.assertEqual(f.calls, [])
            cc.launch(*args, confirm_text=True, knowledge_query="home",
                      confirm_knowledge_context=True, provider_factory=lambda:f)
            for role in ("composer", "lyricist"):
                context = seen[role]["knowledge_context"]
                self.assertTrue(context["observations"])
                self.assertNotIn("work_id", str(context))
                self.assertNotIn("Home, Sweet Home", str(context))
                self.assertNotIn("query", context)
            self.assertNotIn("knowledge_context", seen["reviewer"])
            saved = nd.read(repo/"results/creative/one/job.json")
            self.assertEqual(saved["knowledge"]["query"], "home")
            db.unlink()
            cc.launch(*args, confirm_text=True, confirm_knowledge_context=True,
                      provider_factory=lambda:f)
            self.assertEqual(f.calls, ["composer","lyricist","reviewer"])
            with self.assertRaises(ValueError):
                cc.launch(*args, confirm_text=True, provider_factory=lambda:f)
