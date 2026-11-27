"""Coordinator failure isolation using existing offline release component contracts."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_release_export import fixture,LRC,URL
from yue2_music_director import release_workflow as rw, release_assembly as ra
from yue2_music_director import release_delivery as rd, release_export as ex
from yue2_music_director import human_feedback as hf, native_draft as nd


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo=Path(tmp.name)
        self.source=fixture(self.repo,"one")
        self.enterContext(patch.object(ex,"retained",return_value=self.source))
        self.enterContext(patch.object(hf,"load",return_value=self.source))
        self.key=hf.identity(self.source)
        self.rating={"kind":"listening","ratings":dict.fromkeys(hf.DIMENSIONS,"good"),
                     "observations":"Fixture","confirmed_preferences":[],"inferred_preferences":[]}
        self.approval={"kind":"release_approval","release":"release","decision":"approve","note":""}
        self.art=self.repo/"cover.png"
        self.art.write_bytes(b"synthetic artwork fixture")
        self.image=self.enterContext(patch.object(rd.ci,"inspect",side_effect=self.inspect_image))
        self.workflow=self.repo/"results/release-workflow/release/release-v1"
        self.assembly=self.repo/"results/release-assembly/release/release-v1"
        self.delivery=self.repo/"results/release-delivery/release/release-v1"

    def inspect_image(self,path):
        return {"schema":"cover-import-v1","file":"cover.png","sha256":nd._sha(path),
                "codec":"png","width":3000,"height":3000,"pixel_format":"rgb24",
                "size_bytes":Path(path).stat().st_size,"profile":"local-3000-square-opaque-v1",
                "rights_review":"operator_required","color_profile_verified":False}

    def export(self,lrc=LRC):
        return ex.launch(self.repo,"release",["one"],URL,artist="Fixture",
                         confirm=True,timing_reader=lambda *a:lrc)

    def approve(self):
        hf.append(self.repo,"one",self.key,self.rating)
        hf.append(self.repo,"one",self.key,self.approval)

    def test_plan_missing_approval_and_completed_reuse(self):
        self.export()
        self.assertEqual(rw.launch(self.repo,"release",artwork=self.art,confirm=True),2)
        self.assertFalse(self.workflow.exists())
        self.approve()
        self.assertEqual(rw.launch(self.repo,"release",artwork=self.art),0)
        self.assertFalse(self.workflow.exists())
        self.assertEqual(rw.launch(self.repo,"release",artwork=self.art,confirm=True),0)
        paths=[self.workflow,self.assembly,self.delivery]
        before={p:nd._sha(p) for root in paths for p in root.rglob("*") if p.is_file()}
        self.assertEqual(rw.launch(self.repo,"release",confirm=True),0)
        self.assertEqual(rw.launch(self.repo,"release"),0)
        self.assertEqual(self.image.call_count,1)
        self.assertEqual(before,{p:nd._sha(p) for p in before})
        result=nd.read(self.workflow/"result.json")
        self.assertFalse(result["publishing_authorized"])
        self.assertTrue(result["package_approval_separate"])
        self.assertEqual(result["stages"]["delivery"]["manifest_sha256"],before[self.delivery/"delivery.json"])
        hf.append(self.repo,"one",self.key,{**self.approval,"decision":"revoke"})
        self.assertEqual(rw.launch(self.repo,"release"),2)
        self.assertEqual(before,{p:nd._sha(p) for p in before})

    def test_failed_delivery_resume_without_recreating_audio(self):
        self.export()
        self.approve()
        with patch.object(rd.ci,"inspect",side_effect=ValueError("image validation failed")), \
                self.assertRaisesRegex(ValueError,"image validation"):
            rw.launch(self.repo,"release",artwork=self.art,confirm=True)
        plan=(self.workflow/"plan.json").read_bytes()
        before={p:nd._sha(p) for p in self.assembly.rglob("*") if p.is_file()}
        self.assertTrue(before)
        self.assertFalse((self.workflow/"result.json").exists())
        self.assertFalse(self.delivery.exists())
        other=self.repo/"other.png"
        other.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"Frozen workflow differs"):
            rw.launch(self.repo,"release",artwork=other,confirm=True)
        self.assertEqual(rw.launch(self.repo,"release",artwork=self.art,confirm=True),0)
        self.assertEqual(before,{p:nd._sha(p) for p in before})
        self.assertEqual(plan,(self.workflow/"plan.json").read_bytes())

    def test_partial_remains_partial(self):
        self.assertEqual(self.export(None),2)
        self.approve()
        self.assertEqual(rw.launch(self.repo,"release",artwork=self.art,confirm=True),2)
        self.assertEqual(nd.read(self.workflow/"result.json")["status"],"partial_missing_timing")
        self.assertEqual(rw.launch(self.repo,"release"),2)
        self.assertFalse((self.delivery/"one.srt").exists())

    def test_legacy_omitted_credit_is_frozen_and_restored_on_resume(self):
        ex.launch(self.repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:LRC)
        self.approve()
        with patch.object(rd.ci,"inspect",side_effect=ValueError("interruption")),self.assertRaises(ValueError):
            rw.launch(self.repo,"release",artwork=self.art,artist="Explicit Artist",confirm=True)
        plan=(self.workflow/"plan.json").read_bytes()
        with self.assertRaisesRegex(ValueError,"Frozen workflow differs"):
            rw.launch(self.repo,"release",artwork=self.art,artist="Different",confirm=True)
        self.assertEqual(rw.launch(self.repo,"release",artwork=self.art,confirm=True),0)
        self.assertEqual(rw.launch(self.repo,"release"),0)
        self.assertEqual((self.workflow/"plan.json").read_bytes(),plan)
        delivery=nd.read(self.delivery/"delivery.json")
        self.assertEqual(delivery["metadata"]["artist"],"Explicit Artist")
        self.assertEqual(delivery["contract"]["artist_completion"]["artist"],"Explicit Artist")
        self.assertFalse(delivery["release_approved"])
