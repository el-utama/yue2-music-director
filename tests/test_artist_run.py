import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yue2_music_director import artist_run as ar, native_draft as nd

ABC=('X:1\nT:\nM:2/4\nL:1/32\nQ:1/4=60\n'
     'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"\n'
     'V: Ins clef=treble name="Ins Melody" snm="Inst."\nK:Dm\n'
     '% verse\nV: Vocal\n"Dm"D8F8|\nV: Ins\nZ|\n')
BRIEF={"title":"Fixture","style":"Blues","lyrics":"[Verse]\nOne two",
       "language":"en","seed":42,"duration_seconds":90}
URL="http://127.0.0.1:8791/mcp"


def intent(route="auto",constraints=None,flags=None):
    constraints=constraints or {}
    reviewed=route=="reviewed_native" or (route=="auto" and any(c["mode"]=="must" for c in constraints.values()))
    return {"schema":ar.SCHEMA,"route":route,"concept":"An original song",
            "emotional_arc":"A rise and resolution","performance":"Sparse and warm",
            "section_purposes":{"verse#1":"Tell a story"},"constraints":constraints,
            "retain_soft_flags":flags or {},"follow_lyrics":False,
            "budget":{"score_jobs":int(reviewed),"song_jobs":1,"recognition_calls":1}}


class ArtistTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()

    def test_routes_and_budget(self):
        self.assertEqual(ar.route_for(ar.validate_intent(intent())),"direct_native")
        required=intent(constraints={"key":{"mode":"must","value":"Dm"}})
        self.assertEqual(ar.route_for(ar.validate_intent(required)),"reviewed_native")
        self.assertEqual(ar.route_for(ar.validate_intent(intent("explicit_score"))),"explicit_score")
        required["budget"]["score_jobs"]=0
        with self.assertRaises(ValueError):
            ar.validate_intent(required)

    def test_review_policy(self):
        preferred={"key":{"mode":"prefer","value":"Am"}}
        self.assertEqual(ar.evaluate_plan(ABC,BRIEF,intent("reviewed_native",preferred))["decision"],"stop")
        allowed=intent("reviewed_native",preferred,{"constraint_mismatch":"Creative freedom"})
        self.assertEqual(ar.evaluate_plan(ABC,BRIEF,allowed)["decision"],"retain")
        allowed["constraints"]["key"]["mode"]="must"
        self.assertEqual(ar.evaluate_plan(ABC,BRIEF,allowed)["decision"],"stop")
        self.assertEqual(ar.evaluate_plan("invalid",BRIEF,allowed)["decision"],"stop")

    def test_offline_demo_and_no_mutation(self):
        repo=Path(__file__).resolve().parents[1]
        with patch.object(ar,"Client") as client,patch.object(nd,"execute") as execute:
            self.assertEqual(ar.launch(repo,URL,confirm=False,demo=True),0)
            client.assert_not_called()
            execute.assert_not_called()

    def test_direct_route_and_immutable_identity(self):
        with patch.object(nd,"execute",return_value={"status":"provisional_draft"}) as execute, \
             patch.object(ar,"native_plan") as planner:
            root=self.root/"run"
            ar.run(BRIEF,intent(),root,URL)
            planner.assert_not_called()
            self.assertIsNone(execute.call_args.kwargs["abc"])
            with self.assertRaisesRegex(ValueError,"Retained artistic run differs"):
                ar.run(BRIEF,intent("reviewed_native"),root,URL)
            execute.assert_called_once()

    def test_reviewed_route_and_block_before_song(self):
        preferred={"key":{"mode":"prefer","value":"Am"}}
        with patch.object(ar,"native_plan",return_value=(ABC,{"profile":"same"})), \
             patch.object(nd,"execute",return_value={"status":"provisional_draft"}) as execute:
            blocked=ar.run(BRIEF,intent("reviewed_native",preferred),self.root/"blocked",URL)
            self.assertEqual(blocked["status"],"artistic_plan_stopped")
            execute.assert_not_called()
            approved=intent("reviewed_native",preferred,{"constraint_mismatch":"Creative freedom"})
            ar.run(BRIEF,approved,self.root/"retained",URL)
            self.assertEqual(execute.call_args.kwargs["abc"],ABC)
            self.assertEqual(execute.call_args.kwargs["expected_configuration"],{"profile":"same"})

    def test_plan_journal_resume_and_no_duplicate(self):
        result={"id":"plan","status":"done","lm_seed":42,"abc":ABC,
                "plans":[{"lm_seed":42,"abc":ABC}]}
        with patch.object(ar,"Client") as client_factory,patch.object(ar,"_preflight",return_value={"profile":"same"}):
            client=client_factory.return_value.connect.return_value
            client.call.side_effect=lambda name,args: {"id":"plan","status":"running"} if name=="score_compose" else result
            root=self.root
            self.assertEqual(ar.native_plan(BRIEF,intent("reviewed_native"),root,URL),(ABC,{"profile":"same"}))
            self.assertEqual(ar.native_plan(BRIEF,intent("reviewed_native"),root,URL),(ABC,{"profile":"same"}))
            self.assertEqual(sum(c.args[0]=="score_compose" for c in client.call.call_args_list),1)
            (root/"native-plan.abc").write_text("altered",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"file differs"):
                ar.native_plan(BRIEF,intent("reviewed_native"),root,URL)

    def test_ambiguous_plan_never_resubmitted(self):
        with patch.object(ar,"Client") as factory,patch.object(ar,"_preflight",return_value={}):
            client=factory.return_value.connect.return_value
            client.call.side_effect=nd.MCPError("lost receipt")
            with self.assertRaises(nd.MCPError):
                ar.native_plan(BRIEF,intent("reviewed_native"),self.root,URL)
            with self.assertRaisesRegex(ValueError,"never resubmit"):
                ar.native_plan(BRIEF,intent("reviewed_native"),self.root,URL)
            client.call.assert_called_once()


class IntegratedDraftTests(unittest.TestCase):
    def test_native_reviewed_minor_song_and_recognition_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            audio=root/"audio.flac"; audio.write_bytes(b"fixture")
            config={"profile":"same"}
            run=root/"draft"
            with patch.object(nd,"Client") as factory,patch.object(nd,"reference_configuration",return_value=config), \
                 patch.object(nd,"recognition_preflight"),patch.object(nd.shutil,"which",return_value="fixture"), \
                 patch.object(nd,"_measure",return_value={"sha256":nd._sha(audio),"true_peak_dbtp":-1.2,
                         "integrated_lufs":-17,"duration_seconds":30}), \
                 patch.object(nd,"capture") as capture, \
                 patch("yue2_music_director.midi.extract_midi",return_value=b"fixture"), \
                 patch("yue2_music_director.midi.midi_header",return_value={"tracks":2}), \
                 patch("yue2_music_director.temporal_evidence.native_song_read",return_value={
                     "id":"song","metadata":{"job_id":"job"},"generation_settings":{
                         "abc":ABC,"lyrics":BRIEF["lyrics"],"cot":"full"}}):
                client=factory.return_value.connect.return_value
                names=["song_create","song_job_get","studio_wait","library_song_files","studio_status",
                       "song_defaults","studio_capabilities","models_status","engine_options_get","score_to_midi"]
                client.tools.return_value=[{"name":name,"inputSchema":{"properties":
                    dict.fromkeys([*nd.request_for(BRIEF),"abc"],{})}} for name in names]
                def call(name,args):
                    if name=="song_create": return {"job_id":"job"}
                    if name=="song_job_get":
                        return {"id":"job","status":"completed","seed":42,"lm_seed":42,"adapters":[],
                                "songs":[{"id":"song"}]}
                    if name=="library_song_files": return {"audio":str(audio)}
                    return {}
                client.call.side_effect=call
                def complete(audio,out,url,*,confirm,language):
                    out.mkdir()
                    nd.atomic_write(out/"submission.json",{"audio_sha256":nd._sha(audio),"provider":"whisper",
                                                           "language_requested":language})
                    nd.atomic_write(out/"receipt.json",{"audio_sha256":nd._sha(audio),"state":"RESPONSE_RECEIVED"})
                    nd.atomic_write(out/"recognition.json",{"provider":"whisper","text":"one two"})
                chosen=intent("reviewed_native")
                capture.side_effect=ValueError("Studio busy before recognition")
                with self.assertRaisesRegex(ValueError,"configuration changed"):
                    nd.execute(BRIEF,root/"wrong-config",URL,abc=ABC,artist=chosen,expected_configuration={"profile":"other"})
                self.assertFalse(any(c.args[0]=="song_create" for c in client.call.call_args_list))
                with self.assertRaisesRegex(ValueError,"Studio busy"):
                    nd.execute(BRIEF,run,URL,abc=ABC,artist=chosen,expected_configuration=config)
                capture.side_effect=complete
                result=nd.execute(BRIEF,run,URL,abc=ABC,artist=chosen,expected_configuration=config)
                self.assertTrue(result["saved_score_verified"])
                self.assertEqual(result["generation_path"],"reviewed_native")
                self.assertEqual(result["listening_verdict"],"unrated")
                self.assertFalse(result["automatic_acceptance"])
                self.assertEqual(result["lyric_screen"]["WER"]["edits"],0)
                self.assertEqual(result,nd.execute(BRIEF,run,URL,abc=ABC,artist=chosen,expected_configuration=config))
                self.assertEqual(sum(c.args[0]=="song_create" for c in client.call.call_args_list),1)


class FailureInspectionTests(unittest.TestCase):
    def test_existing_demo_inspection_is_read_only(self):
        source=Path(__file__).resolve().parents[1]/"examples/artist-demo/brief.json"
        brief=nd.load_brief(source)
        with tempfile.TemporaryDirectory() as tmp, patch.object(nd,"Client") as factory:
            repo=Path(tmp)
            fixture=repo/"examples/artist-demo"
            fixture.mkdir(parents=True)
            nd.atomic_write(fixture/"brief.json",brief)
            root=repo/"results/drafts"/("artist-"+nd.digest(nd._canonical(brief)))
            draft=root/"draft"
            draft.mkdir(parents=True)
            request=nd.request_for(brief)
            nd.atomic_write(root/"manifest.json",{"brief":brief,"route":"reviewed_native"})
            nd.atomic_write(root/"plan-decision.json",{"score_review":{"metrics":{"score_seconds":180}}})
            nd.atomic_write(draft/"brief.json",brief)
            nd.atomic_write(draft/"request.json",request)
            nd.atomic_write(draft/"journal_song.json",{"job_id":"known","state":"SUBMITTED",
                "brief_sha256":nd.digest(nd._canonical(brief)),
                "request_sha256":nd.digest(nd._canonical(request))})
            client=factory.return_value.connect.return_value
            job={"id":"known","status":"failed","phase":"generation","message":"fixture engine error"}
            client.call.return_value=job
            self.assertEqual(nd.inspect_artist_demo(repo,URL),0)
            client.call.assert_called_once_with("song_job_get",{"job_id":"known","response_format":"concise"})
            self.assertEqual(nd.read(draft/"job-inspection.json"),job)
            self.assertEqual(nd.read(draft/"journal_song.json")["state"],"SUBMITTED")
