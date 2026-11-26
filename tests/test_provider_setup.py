import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from yue2_music_director import provider_setup as ps, creative_core as cc
from yue2_music_director.creative_provider import TextProvider, ROLES
from yue2_music_director import composer


class ProviderSetupTests(unittest.TestCase):
    def test_local_configuration_roundtrip_no_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            secret="fixture-private-key"
            models={r:"fixture" for r in ROLES}
            ps.save(repo,ps.PRESETS["1"],secret,models,protect=lambda b:b"encrypted-fixture")
            self.assertNotIn(secret,ps.location(repo).read_text(encoding="utf-8"))
            p=ps.load(repo,unprotect=lambda b,**kw:secret.encode())
            self.assertEqual(p.identity(),{"url":ps.PRESETS["1"],"models":models})
            self.assertNotIn(secret,str(p.identity()))

    @unittest.skipUnless(os.name=="nt","Windows current-user DPAPI")
    def test_actual_dpapi_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            secret="synthetic-credential-for-test"
            ps.save(repo,ps.PRESETS["1"],secret,{r:"fixture" for r in ROLES})
            self.assertNotIn(secret,ps.location(repo).read_text(encoding="utf-8"))
            self.assertEqual(ps.load(repo)._key,secret)

    def test_env_is_explicit_not_mixed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{"MUSIC_LLM_MODEL":"fixture"},clear=True):
            with patch.object(ps,"load") as load:
                with self.assertRaises(ValueError):
                    TextProvider.for_repo(Path(tmp))
                load.assert_not_called()

    def test_setup_absent_is_actionable(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,"--setup"):
                TextProvider.for_repo(Path(tmp))


class RetryTests(unittest.TestCase):
    def test_explicit_one_time_retry_keeps_original_attempt(self):
        class Fake:
            def __init__(self):
                self.calls=0
            def identity(self):
                return {"fixture":True}
            def complete(self,*args):
                self.calls+=1
                if self.calls==1:
                    raise ValueError("timeout")
                return {"title":"A","concept":"B","emotional_arc":"C","performance":"D","style":"E"}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            f=Fake()
            args=(root,"composer",composer,f,{"request":"fixture"})
            with self.assertRaises(ValueError):
                cc.stage(*args)
            original=(root/"composer.attempt.json").read_bytes()
            with self.assertRaises(ValueError):
                cc.stage(*args)
            self.assertEqual(cc.stage(*args,retry=True)["title"],"A")
            self.assertEqual((root/"composer.attempt.json").read_bytes(),original)
            self.assertTrue((root/"composer.retry-1.attempt.json").is_file())
            self.assertEqual(cc.stage(*args)["title"],"A")
            self.assertEqual(f.calls,2)

    def test_failed_retry_cannot_loop(self):
        class Fake:
            def identity(self):
                return {}
            def complete(self,*args):
                raise ValueError("failed")
        with tempfile.TemporaryDirectory() as tmp:
            args=(Path(tmp),"composer",composer,Fake(),{})
            for retry in (False,True,True):
                with self.assertRaises(ValueError):
                    cc.stage(*args,retry=retry)
            self.assertTrue((Path(tmp)/"composer.retry-1.attempt.json").is_file())
