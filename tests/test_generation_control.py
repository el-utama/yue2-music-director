import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yue2_music_director.generation_control import inspect_plan, plan_requests, result_score, run

BRIEF={"title":"Study","style":"Acoustic pop","lyrics":"[Verse]\nA line\n[Outro]\nGoodbye",
       "language":"en","duration_seconds":60,"seed":42}
HEADER="X:1\nT:\nM:4/4\nL:1/16\nQ:1/4=120\nK:C\n"
def section(label,notes):
    return f"% {label}\nV: Vocal\n{notes}|\nV: Ins\nZ|\n"
GOOD=HEADER+section("intro","z16")+section("verse","C8D8")+section("outro","E8C8")
BAD=HEADER+section("verse","C8D8")+section("chorus","E16")+section("outro","z16")

class FakeClient:
    def __init__(self):
        self.calls=[]
        self.jobs={}
    def call(self,name,args):
        self.calls.append(name)
        if name=="score_compose":
            job=str(len(self.jobs)+1)
            self.jobs[job]=GOOD if args.get("harmony") else BAD
            return {"id":job,"status":"running"}
        if name=="score_job_get":
            job=args["job_id"]
            abc=self.jobs[job]
            return {"id":job,"status":"done","abc":abc,"lm_seed":42,
                    "plans":[{"abc":abc,"lm_seed":42}]}
        raise AssertionError(name)

class StudyTests(unittest.TestCase):
    def test_single_variable(self):
        a,b=plan_requests(BRIEF).values()
        self.assertEqual(b,{**a,"harmony":{"follow_lyrics":True}})

    def test_structure_gate(self):
        good=inspect_plan(GOOD,BRIEF)
        self.assertTrue(good["eligible_for_render"])
        self.assertEqual(good["score_seconds"],6.0)
        self.assertFalse(good["naturalness_verified"])
        bad=inspect_plan(BAD,BRIEF)
        self.assertFalse(bad["eligible_for_render"])
        self.assertEqual(bad["missing_sung_sections"],["outro#1"])
        self.assertEqual(bad["extra_sung_sections"],["chorus#1"])
        self.assertFalse(inspect_plan("invalid",BRIEF)["eligible_for_render"])
        self.assertFalse(inspect_plan(GOOD,{**BRIEF,"duration_seconds":5})["eligible_for_render"])

    def test_seed_mismatch(self):
        with self.assertRaises(ValueError):
            result_score({"status":"done","plans":[{"abc":GOOD,"lm_seed":43}]},42)

    @patch("yue2_music_director.generation_control.preflight",return_value={"profile":"same"})
    def test_two_plans_and_resume_without_submission(self,_):
        client=FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            report=run(BRIEF,root,client)
            self.assertEqual(client.calls.count("score_compose"),2)
            self.assertFalse(report["arms"]["A"]["eligible_for_render"])
            self.assertTrue(report["arms"]["B"]["eligible_for_render"])
            self.assertFalse(report["automatic_render"])
            self.assertEqual(run(BRIEF,root,client),report)
            self.assertEqual(client.calls.count("score_compose"),2)
            self.assertNotIn("song_create",client.calls)

    @patch("yue2_music_director.generation_control.preflight",return_value={"profile":"same"})
    def test_ambiguous_receipt_never_retries(self,_):
        client=FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(client,"call",return_value={"status":"running"}) as call:
                with self.assertRaises(ValueError):
                    run(BRIEF,Path(directory),client)
                with self.assertRaises(ValueError):
                    run(BRIEF,Path(directory),client)
                self.assertEqual(call.call_count,1)
