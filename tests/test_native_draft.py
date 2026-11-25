import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director import native_draft as nd


class DraftTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()
        self.brief={"title":"Fixture","style":"English folk, 80 BPM.",
                    "lyrics":"[Verse 1]\nOne two","language":"en","seed":42,"duration_seconds":90}
        self.run=self.root/"run"
        self.audio=self.root/"audio.flac"
        self.audio.write_bytes(b"fixture")

    def setup_client(self,client):
        tools=["song_create","song_job_get","studio_wait","library_song_files","studio_status",
               "song_defaults","studio_capabilities","models_status","engine_options_get"]
        client.tools.return_value=[{"name":name,"inputSchema":{"properties":dict.fromkeys(nd.request_for(self.brief),{})}}
                                   for name in tools]
        job={"id":"job","status":"completed","seed":42,"lm_seed":42,"adapters":[],
             "songs":[{"id":"song"}]}
        def call(name,args):
            if name=="song_create":
                return {"job_id":"job"}
            if name=="song_job_get":
                return job
            if name=="library_song_files":
                return {"audio":str(self.audio)}
            if name in ("studio_status","song_defaults","studio_capabilities"):
                return {"fixture":True}
            raise AssertionError(name)
        client.call.side_effect=call

    def fake_capture(self,audio,out,url,*,confirm,language):
        self.assertTrue(confirm)
        out.mkdir()
        nd.atomic_write(out/"submission.json",{"audio_sha256":nd._sha(audio),"provider":"whisper","language_requested":language})
        nd.atomic_write(out/"receipt.json",{"state":"RESPONSE_RECEIVED","audio_sha256":nd._sha(audio)})
        nd.atomic_write(out/"recognition.json",{"provider":"whisper","text":"one two"})

    def test_single_draft_and_cached_review(self):
        with patch.object(nd,"Client") as factory,patch.object(nd,"reference_configuration",return_value={}), \
             patch.object(nd,"recognition_preflight"),patch.object(nd.shutil,"which",return_value="fixture"), \
             patch.object(nd,"_measure",return_value={"sha256":nd._sha(self.audio),
                  "true_peak_dbtp":-1.2,"integrated_lufs":-17,"duration_seconds":30}), \
             patch.object(nd,"capture",side_effect=self.fake_capture) as capture:
            client=factory.return_value.connect.return_value
            self.setup_client(client)
            report=nd.execute(self.brief,self.run,"http://127.0.0.1:8791/mcp")
            self.assertEqual(report["status"],"provisional_draft")
            self.assertFalse(report["automatic_acceptance"])
            self.assertEqual(report["lyric_screen"]["WER"]["edits"],0)
            self.assertEqual(nd.execute(self.brief,self.run,"unused"),report)
            self.assertEqual(sum(c.args[0]=="song_create" for c in client.call.call_args_list),1)
            capture.assert_called_once()
            factory.assert_called_once()

    def test_unknown_submission_never_retries(self):
        with patch.object(nd,"Client") as factory,patch.object(nd,"reference_configuration",return_value={}), \
             patch.object(nd,"recognition_preflight"),patch.object(nd.shutil,"which",return_value="fixture"):
            client=factory.return_value.connect.return_value
            self.setup_client(client)
            old=client.call.side_effect
            def fail(name,args):
                if name=="song_create":
                    raise nd.MCPError("lost receipt")
                return old(name,args)
            client.call.side_effect=fail
            with self.assertRaises(nd.MCPError):
                nd.execute(self.brief,self.run,"http://127.0.0.1:8791/mcp")
            with self.assertRaisesRegex(ValueError,"never resubmit"):
                nd.execute(self.brief,self.run,"http://127.0.0.1:8791/mcp")
            self.assertEqual(sum(c.args[0]=="song_create" for c in client.call.call_args_list),1)

    def test_recognition_failure_never_retries(self):
        with patch.object(nd,"Client") as factory,patch.object(nd,"reference_configuration",return_value={}), \
             patch.object(nd,"recognition_preflight"),patch.object(nd.shutil,"which",return_value="fixture"), \
             patch.object(nd,"_measure",return_value={"sha256":nd._sha(self.audio),
                  "true_peak_dbtp":0,"integrated_lufs":-17,"duration_seconds":30}), \
             patch.object(nd,"capture") as capture:
            self.setup_client(factory.return_value.connect.return_value)
            def fail(audio,out,*args,**kwargs):
                out.mkdir()
                raise nd.MCPError("recognition failed after attempt")
            capture.side_effect=fail
            with self.assertRaises(nd.MCPError):
                nd.execute(self.brief,self.run,"http://127.0.0.1:8791/mcp")
            with self.assertRaises(OSError):
                nd.execute(self.brief,self.run,"http://127.0.0.1:8791/mcp")
            capture.assert_called_once()

    def test_brief_validation_and_no_implicit_generation(self):
        path=self.root/"brief.json"
        path.write_text(json.dumps(self.brief),encoding="utf-8")
        self.assertEqual(nd.load_brief(path),self.brief)
        for field,value in (("duration_seconds",241),("seed",True),("lyrics","[Verse 1]")):
            path.write_text(json.dumps({**self.brief,field:value}),encoding="utf-8")
            with self.assertRaises(ValueError):
                nd.load_brief(path)
        self.assertEqual(nd.request_for(self.brief)["music_source"],{"kind":"local"})
        self.assertNotIn("abc",nd.request_for(self.brief))
