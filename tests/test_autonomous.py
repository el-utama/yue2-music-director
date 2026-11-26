import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from yue2_music_director import autonomous as au, native_draft as nd


class Provider:
    def __init__(self,stop=False):
        self.calls=[]
        self.stop=stop
    def identity(self):
        return {"models":"fake"}
    def complete(self,role,prompt,data):
        self.calls.append(role)
        return {"composer":{"title":"A Key","concept":"Moving out","emotional_arc":"loss to relief",
                "performance":"soft guitar","style":"English, folk, gentle alto vocals, acoustic guitar"},
                "lyricist":{"lyrics":"[Verse]\nI left the key beside the door\n[Chorus]\nI do not live there anymore"},
                "reviewer":{"decision":"stop" if self.stop else "retain","rationale":"Review"},
                "director":{"decision":"retain_provisional","rationale":"Limited evidence",
                            "suggested_next_step":"Listen"}}[role]


class AutonomousTests(unittest.TestCase):
    def test_offline_and_editorial_stop(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(au.artist_run,"run") as native:
            f=Provider(stop=True)
            args=(Path(tmp),"one","A quiet goodbye","en",150,"http://127.0.0.1:8791/mcp")
            self.assertEqual(au.launch(*args,provider_factory=lambda:f),0)
            self.assertEqual(f.calls,[])
            self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),2)
            native.assert_not_called()
            self.assertEqual(f.calls,["composer","lyricist","reviewer"])

    def test_listening_failure_preserves_creative_and_native_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Provider()
            repo=Path(tmp)
            args=(repo,"one","A quiet goodbye","en",150,"http://127.0.0.1:8791/mcp")
            audio=repo/"test.flac"
            audio.write_bytes(b"synthetic fixture")
            jobs=[]
            def native(brief,intent,root,url):
                path=root/"draft/report.json"
                if path.exists():
                    return nd.read(path)
                jobs.append("song")
                path.parent.mkdir(parents=True)
                report={"status":"provisional_draft","song_id":"fixture","artistic_intent":intent,"acoustic":{"duration_seconds":120},
                        "lyric_screen":{"primary_metric":"wer","wer":{"disagreement_rate":0.1}},
                        "headroom_pass":True,"duration_cap_screen_pass":True}
                nd.atomic_write(path,report)
                return report
            def verify(*args):
                return {"audio":str(audio),"audio_sha256":nd._sha(audio)}
            def listen(root,*args):
                path=root/"neutral-listening/review-packet.json"
                path.parent.mkdir(exist_ok=True)
                if path.exists():
                    return nd.read(path)
                packet={"observations":[]}
                nd.atomic_write(path,packet)
                return packet
            with patch.object(au.artist_run,"run",side_effect=native), patch.object(au.ld,"verify_take",side_effect=verify), patch.object(au.ld,"listen",side_effect=ValueError("MOSS unavailable")):
                with self.assertRaises(ValueError):
                    au.launch(*args,confirm=True,provider_factory=lambda:f)
            self.assertEqual(f.calls,["composer","lyricist","reviewer"])
            with patch.object(au.artist_run,"run",side_effect=native), patch.object(au.ld,"verify_take",side_effect=verify), patch.object(au.ld,"listen",side_effect=listen):
                self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),0)
                self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),0)
            self.assertEqual(jobs,["song"])
            self.assertEqual(f.calls,["composer","lyricist","reviewer","director"])
            result=nd.read(repo/"results/autonomous/one/result.json")
            self.assertFalse(result["automatic_acceptance"])
            self.assertFalse(result["revision_authorized"])

    def test_invalid_job_rejected_before_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                au.launch(Path(tmp),"../other","idea","en",150,"http://127.0.0.1:8791/mcp",
                          confirm=True,provider_factory=lambda:self.fail("provider called"))

    def test_new_job_uses_reviewed_plan_and_stops_without_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Provider()
            repo=Path(tmp)
            args=(repo,"one","A quiet goodbye","en",195,"http://127.0.0.1:8791/mcp")
            blocked={"status":"artistic_plan_stopped","decision":{"decision":"stop","score_review":{"hard_violations":[{"code":"score_clock_exceeds_cap","actual_seconds":312.1951219512195}]}}}
            with patch.object(au.artist_run,"native_plan",return_value=("fixture",{})), patch.object(au.artist_run,"evaluate_plan",return_value=blocked["decision"]), patch.object(nd,"execute") as render, patch.object(au.ld,"listen") as listen:
                self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),2)
                render.assert_not_called()
                listen.assert_not_called()
            root=repo/"results/autonomous/one"
            intent=nd.read(root/"intent.json")
            self.assertEqual(intent["route"],"reviewed_native")
            self.assertTrue(intent["follow_lyrics"])
            self.assertEqual(intent["budget"]["score_jobs"],1)
            self.assertEqual(f.calls,["composer","lyricist","reviewer"])
            self.assertEqual(nd.read(root/"plan-stop.json")["song_jobs"],0)
            self.assertFalse((root/"result.json").exists())

    def test_old_job_not_migrated_to_new_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            root=repo/"results/autonomous/old"
            root.mkdir(parents=True)
            nd.atomic_write(root/"job.json",{"schema":"autonomous-job-v1"})
            f=Provider()
            with patch.object(au.artist_run,"run") as native:
                with self.assertRaisesRegex(ValueError,"Legacy job"):
                    au.launch(repo,"old","idea","en",195,"http://127.0.0.1:8791/mcp",confirm=True,provider_factory=lambda:f)
                native.assert_not_called()
            self.assertEqual(f.calls,[])

    def test_continuation_plan_only_no_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(au.continue_plan(Path(tmp),"one","http://127.0.0.1:8791/mcp",
                             provider_factory=lambda:self.fail("provider called")),0)

    def test_continuation_reuses_exact_plan_and_creative_receipts(self):
        import hashlib
        from yue2_music_director import retained_plan_review as rp
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            f=Provider()
            url="http://127.0.0.1:8791/mcp"
            args=(repo,"one","A quiet goodbye","en",150,url)
            old={"decision":"stop","score_review":{"status":"unassessable","unknowns":[{"code":"unsupported_local_notation"}]}}
            with patch.object(au.artist_run,"run",return_value={"status":"artistic_plan_stopped","decision":old}):
                self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),2)
            parent=repo/"results/autonomous/one"
            source=parent/"production"
            source.mkdir()
            brief=nd.read(parent/"brief.json")
            intent=nd.read(parent/"intent.json")
            manifest={"schema":"artist-run-v1","brief":brief,"intent":intent,"route":"reviewed_native","explicit_score_sha256":None}
            nd.atomic_write(source/"manifest.json",manifest)
            nd.atomic_write(source/"plan-decision.json",old)
            for name in ("journal_plan.json","plan-result.json","plan-receipt.json"):
                nd.atomic_write(source/name,{"fixture":name})
            (source/"native-plan.abc").write_text("synthetic fixture")
            before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in parent.rglob("*") if p.is_file()}
            recheck={"previous_status":"unassessable","current_decision":{"decision":"retain"}}
            with patch.object(rp,"inspect",return_value=recheck),patch.object(au,"produce",return_value=0) as produce:
                for _ in range(2):
                    self.assertEqual(au.continue_plan(repo,"one",url,confirm=True,provider_factory=lambda:f),0)
                self.assertEqual(produce.call_count,2)
                self.assertEqual(produce.call_args.args[1],parent/"continuation-1")
                self.assertEqual(f.calls,["composer","lyricist","reviewer"])
                for path,digest in before.items():
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
                (parent/"continuation-1/production/native-plan.abc").write_text("changed")
                with self.assertRaisesRegex(ValueError,"source differs"):
                    au.continue_plan(repo,"one",url,confirm=True,provider_factory=lambda:f)
                self.assertEqual(produce.call_count,2)
