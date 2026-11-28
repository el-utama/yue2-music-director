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
        result={"composer":{"title":"A Key","concept":"Moving out","emotional_arc":"loss to relief",
                "performance":"soft guitar","style":"English, folk, gentle alto vocals, acoustic guitar"},
                "lyricist":{"lyrics":"[Verse]\nI left the key beside the door\n[Chorus]\nI do not live there anymore"},
                "reviewer":{"decision":"stop" if self.stop else "retain","rationale":"Review"},
                "director":{"decision":"retain_provisional","rationale":"Limited evidence",
                            "suggested_next_step":"Listen"}}[role]
        if role=="composer" and "direction_guidance" in data:
            result["performance"]="Opening: direct_vocal\nVocal: female\nNarrator: first person\nSoft guitar, intimate alto"
        return result


class AutonomousTests(unittest.TestCase):
    def test_new_song_form_and_duration_reach_all_text_roles(self):
        import sys
        from yue2_music_director import lyricist
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = repo / "results/autonomous/compact"
            provider = Provider(stop=True)
            argv = ["music", "--repo", tmp, "--url", "http://127.0.0.1:8791/mcp",
                    "--job", "compact", "--request", "A quiet goodbye", "--confirm-run"]
            with patch.object(sys, "argv", argv), patch.object(au.TextProvider, "for_repo", return_value=provider), \
                 patch.object(au, "produce", side_effect=AssertionError("synthesis after editorial stop")):
                self.assertEqual(au.main(), 2)
                self.assertEqual(au.main(), 2)
            self.assertEqual(provider.calls, ["composer", "lyricist", "reviewer"])
            for role in provider.calls:
                data = nd.read(root / (role + ".attempt.json"))["input"]
                self.assertEqual(data["song_form_guidance"]["preferred_sections"],
                                 ["[Intro]", "[Verse 1]", "[Pre-Chorus]", "[Chorus]", "[Verse 2]",
                                  "[Bridge]", "[Instrumental Break]", "[Outro]"])
                self.assertIn(role, data["song_form_guidance"])
                self.assertEqual(data["duration_plan"]["hard_cap_seconds"], 180)
                self.assertLess(data["duration_plan"]["target_score_seconds"], 180)
            self.assertEqual(nd.read(root / "job.json")["song_form"], lyricist.COMPACT_FORM)

    def test_outro_compares_lines_with_only_the_last_chorus(self):
        from yue2_music_director.lyricist import diagnostics
        lyrics = ("[Chorus]\nOld hook\n[Final Chorus]\nA new line\nWe're leaving\n"
                  "[Outro]\nOld hook\nWe’re leaving!\nOne more word")
        self.assertEqual(diagnostics(lyrics, "en", compact_form=True)[-1]["final_chorus_line_matches"], [2])
        self.assertNotIn("final_chorus_line_matches", diagnostics(lyrics, "en")[-1])
        instrumental = "[Chorus]\nA new line\n[Instrumental Break]\n[Outro]"
        self.assertEqual(diagnostics(instrumental, "en", compact_form=True)[-1]["final_chorus_line_matches"], [])


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

    def test_new_policy_records_opening_without_migrating_old_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            f=Provider(stop=True)
            args=(repo,"one","A quiet goodbye","en",150,"http://127.0.0.1:8791/mcp")
            self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),2)
            root=repo/"results/autonomous/one"
            identity=nd.read(root/"job.json")
            self.assertEqual(identity["production_policy"],au.POLICY)
            result=nd.read(root/"creative-result.json")
            _,intent=au.make_inputs(result,identity)
            self.assertEqual(intent["constraints"]["opening"],{"mode":"must","value":"direct_vocal"})
            self.assertEqual(intent["constraints"]["opening_timing"],{"mode":"must","value":"direct_vocal"})
            previous={**identity,"production_policy":au.cd.PREVIOUS_POLICY}
            _,previous_intent=au.make_inputs(result,previous)
            self.assertEqual(previous_intent["constraints"],{"opening":{"mode":"must","value":"direct_vocal"}})
            legacy={**identity,"production_policy":au.LEGACY_POLICY}
            _,old_intent=au.make_inputs(result,legacy)
            self.assertEqual(old_intent["constraints"],{})


class CreativeSemanticRecoveryTests(unittest.TestCase):
    def test_composer_and_lyricist_rejections_recover_without_replay(self):
        for role in ("composer","lyricist"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as tmp:
                repo=Path(tmp)
                provider=Provider(stop=True)
                valid=provider.complete
                bad=True
                def complete(stage,prompt,data):
                    result=valid(stage,prompt,data)
                    if bad and stage==role:
                        if stage=="composer":
                            result["performance"]="Missing required headers"
                        else:
                            result["lyrics"]="[Intro]\n[Verse]\nI left the key beside the door"
                    return result
                provider.complete=complete
                args=(repo,"one","A quiet goodbye","en",150,"http://127.0.0.1:8791/mcp")
                root=repo/"results/autonomous/one"
                with patch.object(au.artist_run,"run") as native:
                    with self.assertRaises(ValueError):
                        au.launch(*args,confirm=True,provider_factory=lambda:provider)
                    self.assertFalse((root/(role+".json")).exists())
                    rejected=root/(role+".rejected.json")
                    evidence=rejected.read_bytes()
                    self.assertEqual(nd.read(rejected)["schema"],"creative-stage-rejected-v1")
                    self.assertEqual(provider.calls,["composer"] if role=="composer" else ["composer","lyricist"])
                    before=list(provider.calls)
                    with self.assertRaises(ValueError):
                        au.launch(*args,confirm=True,provider_factory=lambda:provider)
                    self.assertEqual(provider.calls,before)
                    bad=False
                    self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:provider,retry_role=role),2)
                    self.assertEqual(provider.calls,["composer","composer","lyricist","reviewer"] if role=="composer" else ["composer","lyricist","lyricist","reviewer"])
                    self.assertEqual(rejected.read_bytes(),evidence)
                    self.assertEqual(nd.read(root/(role+".json"))["schema"],"creative-stage-semantic-v1")
                    with self.assertRaises(ValueError):
                        au.launch(*args,confirm=True,provider_factory=lambda:provider,retry_role=role)
                    native.assert_not_called()

    def test_second_invalid_response_exhausts_retry_and_preserves_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            provider=Provider()
            valid=provider.complete
            def complete(role,prompt,data):
                result=valid(role,prompt,data)
                result["performance"]="Bad opening header"
                return result
            provider.complete=complete
            args=(repo,"one","A quiet goodbye","en",150,"http://127.0.0.1:8791/mcp")
            root=repo/"results/autonomous/one"
            with patch.object(au.artist_run,"run") as native:
                with self.assertRaises(ValueError):
                    au.launch(*args,confirm=True,provider_factory=lambda:provider)
                for _ in range(2):
                    with self.assertRaises(ValueError):
                        au.launch(*args,confirm=True,provider_factory=lambda:provider,retry_role="composer")
                self.assertEqual(provider.calls,["composer","composer"])
                self.assertFalse((root/"composer.json").exists())
                self.assertTrue((root/"composer.rejected.json").is_file())
                self.assertTrue((root/"composer.retry-1.rejected.json").is_file())
                native.assert_not_called()

    def test_legacy_receipts_are_not_rewritten(self):
        from yue2_music_director import creative_core as cc
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            provider=Provider()
            args=(root,provider,"A quiet goodbye","en",150)
            result=cc.prepare(*args,duration_guidance=True)
            before={p:p.read_bytes() for p in root.iterdir()}
            self.assertNotIn("schema",nd.read(root/"composer.json"))
            self.assertEqual(cc.prepare(*args,duration_guidance=True),result)
            self.assertEqual(provider.calls,["composer","lyricist","reviewer"])
            self.assertEqual({p:p.read_bytes() for p in root.iterdir()},before)


    def test_v2_retained_job_has_no_new_guidance_or_replay(self):
        from yue2_music_director import creative_core as cc
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            provider=Provider(stop=True)
            url="http://127.0.0.1:8791/mcp"
            root=repo/"results/autonomous/one"
            root.mkdir(parents=True)
            identity={"schema":"autonomous-job-v1","job":"one","request":"A quiet goodbye",
                      "language":"en","duration_seconds":150,"provider":provider.identity(),
                      "studio_url":url,"production_policy":au.cd.PREVIOUS_POLICY}
            nd.atomic_write(root/"job.json",identity)
            result=cc.prepare(root,provider,identity["request"],"en",150,
                              duration_guidance=True,direction_guidance=True)
            nd.atomic_write(root/"creative-result.json",result)
            before={p:p.read_bytes() for p in root.iterdir()}
            self.assertNotIn("opening_timing_guidance",nd.read(root/"composer.attempt.json")["input"])
            with patch.object(au.artist_run,"run") as native:
                self.assertEqual(au.launch(repo,"one",identity["request"],"en",150,url,
                                          confirm=True,provider_factory=lambda:provider),2)
                native.assert_not_called()
            self.assertEqual(provider.calls,["composer","lyricist","reviewer"])
            self.assertEqual({p:p.read_bytes() for p in root.iterdir()},before)


class StructuredComposerTests(unittest.TestCase):
    def test_indonesian_brief_structured_response_and_resume(self):
        from yue2_music_director.creative_provider import role_schema
        from yue2_music_director import composer
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            f=Provider(stop=True)
            original=f.complete
            def complete(role,prompt,data):
                value=original(role,prompt,data)
                if role=="composer":
                    self.assertEqual(prompt,composer.Structured.PROMPT)
                    self.assertEqual(role_schema(role,data),composer.Structured.SCHEMA)
                    value.update(performance="Close-mic baritone, sparse guitar, gentle swell.",
                                 opening="direct_vocal", vocal="male", narrator="first person",
                                 musical_rationale="Immediate entry emphasizes an intimate farewell.")
                return value
            f.complete=complete
            args=(repo,"structured","Aku pergi agar dia bahagia","id",150,"http://127.0.0.1:8791/mcp")
            # Editorial stop ensures no native calls; the receipt is validated on resume.
            with patch.object(au.artist_run,"run") as native:
                self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),2)
                self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),2)
                native.assert_not_called()
            root=repo/"results/autonomous/structured"
            saved=nd.read(root/"composer.json")["result"]
            self.assertEqual(au.cd.parse_direction(saved),{"opening":"direct_vocal","vocal":"male","narrator":"first person"})
            self.assertIn("Musical rationale:",saved["performance"])
            self.assertEqual(f.calls,["composer","lyricist","reviewer"])

    def test_missing_direction_is_not_fabricated(self):
        from yue2_music_director import composer
        value={"title":"Farewell","concept":"Parting","emotional_arc":"loss to resolve",
               "performance":"Direct vocal, baritone, sparse guitar","style":"Indonesian, folk, male vocals"}
        with self.assertRaises(ValueError):
            composer.Structured.validate(value)
        value.update(opening="direct_vocal",vocal="male",narrator="first person",
                     musical_rationale=" ")
        with self.assertRaises(ValueError):
            composer.Structured.validate(value)

    def test_v3_receipts_keep_old_prompt_and_timing(self):
        from yue2_music_director import creative_core as cc, composer
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            root=repo/"results/autonomous/old"
            root.mkdir(parents=True)
            f=Provider(stop=True)
            url="http://127.0.0.1:8791/mcp"
            identity={"schema":"autonomous-job-v1","job":"old","request":"Farewell",
                      "language":"en","duration_seconds":150,"provider":f.identity(),
                      "studio_url":url,"production_policy":au.cd.POLICY}
            nd.atomic_write(root/"job.json",identity)
            result=cc.prepare(root,f,"Farewell","en",150,duration_guidance=True,
                              direction_guidance=True,timing_guidance=True)
            nd.atomic_write(root/"creative-result.json",result)
            before={p:p.read_bytes() for p in root.iterdir()}
            self.assertEqual(nd.read(root/"composer.attempt.json")["prompt"],composer.PROMPT)
            self.assertEqual(au.launch(repo,"old","Farewell","en",150,url,
                                       confirm=True,provider_factory=lambda:f),2)
            self.assertEqual(before,{p:p.read_bytes() for p in root.iterdir()})
            _,intent=au.make_inputs(result,identity)
            self.assertIn("opening_timing",intent["constraints"])


class ApprovedDurationContinuationTests(unittest.TestCase):
    def test_approved_fit_retains_original_and_reuses_child(self):
        from test_duration_fit import ABC
        from yue2_music_director import retained_plan_review as rp, duration_fit as df
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            f=Provider()
            original=f.complete
            def complete(role,prompt,data):
                value=original(role,prompt,data)
                if role=="composer":
                    value["style"]="English, folk, 70 BPM"
                elif role=="lyricist":
                    value["lyrics"]="[Verse]\nOne two"
                return value
            f.complete=complete
            url="http://127.0.0.1:8791/mcp"
            args=(repo,"fit","A quiet goodbye","en",195,url)
            parent=repo/"results/autonomous/fit"
            def native(brief,intent,root,url):
                root.mkdir(parents=True)
                nd.atomic_write(root/"manifest.json",{"schema":"artist-run-v1","brief":brief,"intent":intent,"route":"reviewed_native","explicit_score_sha256":None})
                review=au.artist_run.evaluate_plan(ABC,brief,intent)
                nd.atomic_write(root/"plan-decision.json",review)
                nd.atomic_write(root/"journal_plan.json",{"state":"COMPLETED","score_sha256":nd.digest(ABC.encode()),"configuration":{"fixture":True}})
                for name in ("plan-result.json","plan-receipt.json"):
                    nd.atomic_write(root/name,{"fixture":True})
                (root/"native-plan.abc").write_bytes(ABC.encode())
                return {"status":"artistic_plan_stopped","decision":review}
            with patch.object(au.artist_run,"run",side_effect=native):
                self.assertEqual(au.launch(*args,confirm=True,provider_factory=lambda:f),2)
            before={p:p.read_bytes() for p in parent.rglob("*") if p.is_file()}
            old=nd.read(parent/"production/plan-decision.json")
            with patch.object(rp,"inspect",return_value={"previous_status":"blocked","current_decision":old}),patch.object(au,"produce",return_value=0) as produce:
                with self.assertRaisesRegex(ValueError,"approve exact BPM"):
                    au.continue_plan(repo,"fit",url,confirm=True,provider_factory=lambda:f,approve_tempo=76)
                for _ in range(2):
                    self.assertEqual(au.continue_plan(repo,"fit",url,confirm=True,provider_factory=lambda:f,approve_tempo=77),0)
                self.assertEqual(produce.call_count,2)
                child=parent/"continuation-1"
                contract=nd.read(child/"continuation.json")
                self.assertEqual(contract["schema"],df.FIT_SCHEMA)
                self.assertEqual(df.verify_frozen(parent,child,contract)[0],ABC.replace("Q:1/4=71","Q:1/4=77"))
                self.assertEqual(produce.call_args.kwargs["planner_configuration"],{"fixture":True})
                self.assertEqual(f.calls,["composer","lyricist","reviewer"])
                self.assertEqual(before,{p:p.read_bytes() for p in before})
                (child/"production/duration-fit.abc").write_bytes(ABC.encode())
                with self.assertRaises(ValueError):
                    au.continue_plan(repo,"fit",url,confirm=True,provider_factory=lambda:f,approve_tempo=77)
                self.assertEqual(produce.call_count,2)


class DefaultLyricLanguageTests(unittest.TestCase):
    def test_indonesian_idea_defaults_to_english_unless_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv=["autonomous","--repo",tmp,"--url","http://127.0.0.1:8791/mcp",
                  "--job","language-fixture","--request","Sebuah hubungan harus berakhir"]
            for flags,expected in (([],"en"),(["--language","id"],"id")):
                with self.subTest(language=expected),patch("sys.argv",argv+flags),patch.object(au,"launch",return_value=0) as launch:
                    self.assertEqual(au.main(),0)
                    self.assertEqual(launch.call_args.args[3],expected)
