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

    def test_native_empty_adapters_are_null_in_compact_job(self):
        for adapters in (None,[]):
            nd.verify_completed_settings({"seed":42,"lm_seed":42,"adapters":adapters},self.brief)
        for job in ({"seed":42,"lm_seed":42}, {"seed":42,"lm_seed":42,"adapters":["unexpected"]},
                    {"seed":42,"lm_seed":43,"adapters":None}):
            with self.assertRaises(ValueError):
                nd.verify_completed_settings(job,self.brief)

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

    def test_director_demo_structure_and_signature(self):
        from yue2_music_director.music import parse_score
        folder=Path(__file__).resolve().parents[1]/"examples/director-demo"
        brief=nd.load_brief(folder/"brief.json")
        abc=(folder/"score.abc").read_text(encoding="utf-8")
        review=nd.verify_directed_score(abc,brief)
        self.assertEqual(review["actual_sung_sections"],["verse#1","chorus#1","verse#2","chorus#2"])
        self.assertAlmostEqual(review["score_seconds"],40*240/88)
        score=parse_score(abc)
        self.assertEqual(score.counts,{"Vocal":40,"Ins":40})
        pitches=[e.pitch for e in score.events if e.voice=="Vocal" and e.kind=="note"]
        self.assertEqual((min(pitches),max(pitches)),(60,71))
        # Each two-bar phrase has an intentionally designed attack count;
        # these are not inferred acoustic syllable boundaries.
        expected=[[8,7,8,8],[7,7,10,9],[8,7,9,8],[7,7,10,9]]
        for index,counts in enumerate(expected):
            for line,count in enumerate(counts):
                bars=score.bar_events["Vocal"][4+8*index+2*line:6+8*index+2*line]
                self.assertEqual(sum(e.kind=="note" for b in bars for e in b),count)
        saved={"id":"song","metadata":{"job_id":"job"},
               "generation_settings":{"abc":abc,"cot":"full","lyrics":brief["lyrics"]}}
        nd.verify_saved_directed_score(saved,abc,"song","job",brief)
        saved["generation_settings"]["abc"]=abc.replace("E2E2G4G4A4","D2E2G4G4A4",1)
        with self.assertRaisesRegex(ValueError,"differ"):
            nd.verify_saved_directed_score(saved,abc,"song","job",brief)

    def test_directed_draft_rejects_bad_score_before_connecting(self):
        with patch.object(nd,"Client") as client:
            with self.assertRaisesRegex(ValueError,"failed structural review"):
                nd.execute(self.brief,self.run,"unused",abc="invalid")
            client.assert_not_called()

    def test_directed_draft_uses_explicit_score_and_native_compatibility(self):
        abc='X:1\nM:4/4\nL:1/16\nQ:1/4=80\nK:C\n% verse\nV: Vocal\n"C"C8D8|\nV: Ins\nZ|\n'
        with patch.object(nd,"Client") as factory,patch.object(nd,"reference_configuration",return_value={}), \
             patch.object(nd,"recognition_preflight"),patch.object(nd.shutil,"which",return_value="fixture"), \
             patch.object(nd,"_measure",return_value={"sha256":nd._sha(self.audio),
                  "true_peak_dbtp":-1.2,"integrated_lufs":-17,"duration_seconds":30}), \
             patch.object(nd,"capture",side_effect=self.fake_capture), \
             patch("yue2_music_director.midi.extract_midi",return_value=b"fixture"), \
             patch("yue2_music_director.midi.midi_header",return_value={"tracks":2}), \
             patch("yue2_music_director.temporal_evidence.native_song_read",return_value={
                 "id":"song","metadata":{"job_id":"job"},
                 "generation_settings":{"abc":abc,"lyrics":self.brief["lyrics"],"cot":"full"}}):
            client=factory.return_value.connect.return_value
            self.setup_client(client)
            tools=client.tools.return_value
            for t in tools:
                if t["name"]=="song_create":
                    t["inputSchema"]["properties"]["abc"]={}
            tools.append({"name":"score_to_midi","inputSchema":{"properties":{"abc":{}}}})
            old=client.call.side_effect
            client.call.side_effect=lambda name,args: {} if name=="score_to_midi" else old(name,args)
            report=nd.execute(self.brief,self.run,"http://127.0.0.1:8791/mcp",abc=abc)
            self.assertTrue(report["saved_score_verified"])
            calls=client.call.call_args_list
            self.assertLess([c.args[0] for c in calls].index("score_to_midi"),
                            [c.args[0] for c in calls].index("song_create"))
            self.assertEqual(next(c.args[1]["abc"] for c in calls if c.args[0]=="song_create"),abc)
            self.assertEqual(nd.execute(self.brief,self.run,"unused",abc=abc),report)

