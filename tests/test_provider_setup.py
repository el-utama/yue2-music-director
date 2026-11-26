import os
import json
import urllib.error
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

class ProviderTransportTests(unittest.TestCase):
    def test_request_uses_exact_model_and_json_response(self):
        p=TextProvider(ps.PRESETS["1"],"fixture-secret",{r:"fixture-"+r for r in ROLES})
        with patch("urllib.request.build_opener") as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value=json.dumps({"choices":[{"finish_reason":"stop",
                "message":{"content":'{"ready":true}',"reasoning_content":"not the final answer"}}]}).encode()
            self.assertEqual(p.complete("composer","JSON only",{}),{"ready":True})
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(json.loads(request.data)["model"],"fixture-composer")
            self.assertEqual(request.get_header("Authorization"),"Bearer fixture-secret")
            self.assertNotIn("fixture-secret",str(p.identity()))
            self.assertEqual(opener.return_value.open.call_count,1)

    def test_rate_limit_no_fallback_or_retry(self):
        p=TextProvider(ps.PRESETS["1"],"fixture-secret",{r:"fixture" for r in ROLES})
        with patch("urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect=urllib.error.HTTPError(p.url,429,"limit",{},None)
            with self.assertRaisesRegex(ValueError,"429"):
                p.complete("composer","JSON only",{})
            self.assertEqual(opener.return_value.open.call_count,1)

class AuthDiagnosticsTests(unittest.TestCase):
    def test_configuration_source_no_secrets(self):
        from yue2_music_director.creative_provider import configuration_source
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(configuration_source(),"local Windows configuration")
        with patch.dict(os.environ,{"MUSIC_LLM_KEY":"secret"},clear=True):
            self.assertEqual(configuration_source(),"environment")

    def test_auth_errors_preserve_status_without_body(self):
        p=TextProvider(ps.PRESETS["1"],"fixture-secret",{r:"fixture" for r in ROLES})
        for code,word in ((401,"authentication rejected"),(403,"access forbidden")):
            with patch("urllib.request.build_opener") as opener:
                opener.return_value.open.side_effect=urllib.error.HTTPError(p.url,code,"fixture-secret",{},None)
                with self.assertRaisesRegex(ValueError,word) as caught:
                    p.complete("composer","JSON only",{})
                self.assertIn(str(code),str(caught.exception))
                self.assertNotIn("fixture-secret",str(caught.exception))
                self.assertEqual(opener.return_value.open.call_count,1)

class NvidiaCatalogTests(unittest.TestCase):
    def test_catalog_uses_same_key_and_exact_host(self):
        p=TextProvider(ps.PRESETS["1"],"fixture-secret",{r:"fixture" for r in ROLES})
        with patch("urllib.request.build_opener") as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value=b'{"data":[{"id":"fixture"}]}'
            self.assertEqual(p.nvidia_catalog(),(200,{"fixture"}))
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url,"https://integrate.api.nvidia.com/v1/models")
            self.assertEqual(request.get_method(),"GET")
            self.assertEqual(request.get_header("Authorization"),"Bearer fixture-secret")

    def test_catalog_rejection_stops_before_completion(self):
        p=TextProvider(ps.PRESETS["1"],"fixture-secret",{r:"fixture" for r in ROLES})
        with patch.object(TextProvider,"for_repo",return_value=p), patch.object(p,"nvidia_catalog",return_value=(401,set())), patch.object(p,"complete") as completion:
            with self.assertRaisesRegex(ValueError,"401"):
                ps.check(Path("."))
            completion.assert_not_called()

    def test_catalog_success_is_not_completion_success(self):
        p=TextProvider(ps.PRESETS["1"],"fixture-secret",{r:"fixture" for r in ROLES})
        with patch.object(TextProvider,"for_repo",return_value=p), patch.object(p,"nvidia_catalog",return_value=(200,{"fixture"})), patch.object(p,"complete",side_effect=ValueError("Provider HTTP status 403")) as completion:
            with self.assertRaisesRegex(ValueError,"403"):
                ps.check(Path("."))
            completion.assert_called_once()

    def test_malformed_key_rejected_locally(self):
        for key in ("Bearer fixture","fixture\tsecret","fixture\x16secret","fixture\u200bsecret"):
            with self.assertRaises(ValueError):
                TextProvider(ps.PRESETS["1"],key,{r:"fixture" for r in ROLES})

class NemotronStructuredTests(unittest.TestCase):
    def provider(self):
        from yue2_music_director.creative_provider import NEMOTRON_VL
        return TextProvider(ps.PRESETS["1"],"fixture-secret",{r:NEMOTRON_VL for r in ROLES})

    def test_structured_schema_and_budget_for_each_role(self):
        from yue2_music_director.creative_provider import role_schema
        p=self.provider()
        for role in ROLES:
            with patch("urllib.request.build_opener") as opener:
                response=opener.return_value.open.return_value.__enter__.return_value
                response.read.return_value=b'{"choices":[{"finish_reason":"stop","message":{"content":"{}"}}]}'
                p.complete(role,"JSON",{})
                body=json.loads(opener.return_value.open.call_args.args[0].data)
                self.assertEqual(body["response_format"]["json_schema"]["schema"],role_schema(role))
                self.assertTrue(body["response_format"]["json_schema"]["strict"])
                self.assertEqual(body["max_tokens"],16384)
                self.assertTrue(body["chat_template_kwargs"]["enable_thinking"])
                self.assertEqual(opener.return_value.open.call_count,1)

    def test_smoke_schema_is_distinct_and_reasoning_disabled(self):
        p=self.provider()
        with patch("urllib.request.build_opener") as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value=b'{"choices":[{"finish_reason":"stop","message":{"content":"{\\"ready\\":true}"}}]}'
            self.assertEqual(p.complete("composer","JSON",{},smoke=True),{"ready":True})
            body=json.loads(opener.return_value.open.call_args.args[0].data)
            self.assertEqual(body["response_format"]["json_schema"]["schema"]["properties"],{"ready":{"type":"boolean","enum":[True]}})
            self.assertFalse(body["chat_template_kwargs"]["enable_thinking"])
            self.assertEqual(body["max_tokens"],256)

    def test_smoke_does_not_accept_wrong_json_object(self):
        p=self.provider()
        with patch.object(TextProvider,"for_repo",return_value=p), patch.object(p,"nvidia_catalog",return_value=(200,set(p.models.values()))), patch.object(p,"complete",return_value={"test":"connection"}):
            with self.assertRaisesRegex(ValueError,"smoke check failed"):
                ps.check(Path("."))

    def test_generic_provider_no_nvidia_specific_fields(self):
        p=TextProvider("https://example.com/v1/chat/completions","fixture-secret",{r:"fixture" for r in ROLES})
        with patch("urllib.request.build_opener") as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value=b'{"choices":[{"finish_reason":"stop","message":{"content":"{}"}}]}'
            p.complete("composer","JSON",{},smoke=True)
            body=json.loads(opener.return_value.open.call_args.args[0].data)
            self.assertNotIn("response_format",body)
            self.assertNotIn("chat_template_kwargs",body)
