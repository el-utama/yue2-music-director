"""Approved release assembly uses real finished FLAC and retained timing only."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from test_release_export import fixture, LRC, URL
from yue2_music_director import acoustic as ac, audio_finishing as fin, finish_audio as fa
from yue2_music_director import audio_variant as av, human_feedback as hf
from yue2_music_director import release_assembly as ra, release_export as ex, native_draft as nd


class ReleaseAssemblyTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo=Path(temp.name)
        self.source=fixture(self.repo,"one")
        self.source["evidence"]["result_sha256"]="a"*64
        self.sources={"one":self.source}
        for module,name in ((ex,"retained"),(hf,"load"),(fin,"load")):
            self.enterContext(patch.object(module,name,side_effect=lambda repo,job:self.sources[job]))
        self.ratings={"kind":"listening","ratings":dict.fromkeys(hf.DIMENSIONS,"good"),
                      "observations":"synthetic test listener","confirmed_preferences":[],"inferred_preferences":[]}
        self.approval={"kind":"release_approval","release":"release","decision":"approve","note":""}
        self.root=self.repo/"results/release-assembly/release/package-v1"
        self.export=self.repo/"results/exports/songs/one--release"

    def approve(self,source,variant="original"):
        key=av.select(self.repo,source,variant)["identity"]
        hf.append(self.repo,source["job"],key,self.ratings)
        hf.append(self.repo,source["job"],key,self.approval)
        return key

    def make_export(self,lrc=LRC):
        return ex.launch(self.repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:lrc)

    def real_candidate(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            if os.environ.get("REQUIRE_REAL_AUDIO_TESTS")=="1":
                self.fail("Required FFmpeg unavailable")
            self.skipTest("FFmpeg required")
        ffmpeg,ffprobe,_=fa.tools()
        audio=self.source["audio"]
        audio.unlink()
        ac._run([ffmpeg,"-nostdin","-v","error","-f","lavfi","-i",
                 "aevalsrc=0.9772*sin(2*PI*440*t)|0.1*sin(2*PI*660*t):s=48000:d=5.5",
                 "-c:a","flac","-sample_fmt","s32","-bits_per_raw_sample","24","-n",str(audio)])
        measured=ac._measure(audio,ffmpeg,ffprobe)
        self.source["result"]["audio_sha256"]=measured["sha256"]
        self.source["report"]["acoustic"]=measured
        self.assertEqual(fin.launch(self.repo,"one",confirm=True),0)
        return av.select(self.repo,self.source,"gain-v1")

    def test_original_requires_approval_and_is_idempotent(self):
        self.assertEqual(self.make_export(),0)
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),2)
        self.assertFalse(self.root.exists())
        key=self.approve(self.source)
        self.assertEqual(ra.launch(self.repo,"release"),0)
        self.assertFalse(self.root.exists())
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),0)
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),0)
        self.assertEqual((self.root/"one.flac").read_bytes(),self.source["audio"].read_bytes())
        self.assertFalse(nd.read(self.root/"assembly.json")["release_approved"])
        hf.append(self.repo,"one",key,{**self.approval,"decision":"revoke"})
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),2)
        self.assertTrue(self.root.exists())

    def test_candidate_has_separate_approval_and_reuses_exact_lyric_files(self):
        selected=self.real_candidate()
        self.assertEqual(self.make_export(),0)
        before={p:nd._sha(p) for p in self.export.rglob("*") if p.is_file()}
        original=self.approve(self.source)
        variant={"one":"gain-v1"}
        key=selected["identity"]
        self.assertNotEqual(key["audio_sha256"],original["audio_sha256"])
        self.assertIsNone(hf.approval_receipt(self.repo,key,"release"))
        self.assertEqual(hf.status(self.repo,self.source,"gain-v1")["listening"],[])
        with self.assertRaisesRegex(ValueError,"listening feedback"):
            hf.append(self.repo,"one",key,self.approval)
        self.assertEqual(ra.launch(self.repo,"release",variants=variant,confirm=True),2)
        self.approve(self.source,"gain-v1")
        with patch.object(fa,"tools",side_effect=AssertionError("no measurement")), \
             patch.object(ex,"read_timing",side_effect=AssertionError("no timing read")):
            self.assertEqual(ra.launch(self.repo,"release",variants=variant,confirm=True),0)
            self.assertEqual(ra.launch(self.repo,"release",variants=variant,confirm=True),0)
        self.assertEqual(nd._sha(self.root/"one.flac"),key["audio_sha256"])
        for suffix in (".txt",".clean.txt",".lrc",".srt"):
            self.assertEqual((self.root/("one"+suffix)).read_bytes(),(self.export/("one"+suffix)).read_bytes())
        self.assertEqual(before,{p:nd._sha(p) for p in before})
        manifest=nd.read(self.root/"assembly.json")
        self.assertEqual(manifest["contract"]["tracks"][0]["identity"],key)
        self.assertFalse(manifest["publishing_authorized"])
        self.assertFalse(manifest["contract"]["tracks"][0]["timing"]["acoustic_timing_verified"])
        self.assertEqual([r["schema"] for r in hf.history(self.repo/"results/feedback/one")],
                         ["human-feedback-v1"]*2+["human-feedback-v2"]*2)
        selected["audio"].write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            ra.launch(self.repo,"release",variants=variant,confirm=True)

    def test_partial_timing_is_not_promoted(self):
        self.assertEqual(self.make_export(None),2)
        self.approve(self.source)
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),2)
        self.assertEqual(nd.read(self.root/"assembly.json")["status"],"partial_missing_timing")
        self.assertFalse((self.root/"one.srt").exists())

    def test_mixed_ordered_album_requires_every_track(self):
        self.sources["two"]=fixture(self.repo,"two")
        self.assertEqual(ex.launch(self.repo,"release",["two","one"],URL,kind="album",
                                   title="Album",confirm=True,timing_reader=lambda *a:LRC),0)
        self.approve(self.source)
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),2)
        self.approve(self.sources["two"])
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),0)
        result=nd.read(self.root/"assembly.json")
        self.assertEqual([s["identity"]["job"] for s in result["contract"]["tracks"]],["two","one"])
        self.assertTrue((self.root/"01 - two/01 - two.flac").exists())

    def test_tampered_base_or_unknown_variant_refused(self):
        self.make_export()
        self.approve(self.source)
        with self.assertRaises(ValueError):
            ra.launch(self.repo,"release",variants={"absent":"gain-v1"},confirm=True)
        (self.export/"one.lrc").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            ra.launch(self.repo,"release",confirm=True)
        self.assertFalse(self.root.exists())

    def test_video_assets_preserved_in_approved_assembly(self):
        self.assertEqual(ex.launch(self.repo,"release",["one"],URL,preset="video",confirm=True,timing_reader=lambda *a:LRC),0)
        self.approve(self.source)
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),0)
        self.assertEqual((self.root/"one.line.lrc").read_bytes(),(self.export/"one.line.lrc").read_bytes())
