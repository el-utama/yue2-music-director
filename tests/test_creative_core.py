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
