"""Real local image import and immutable package review integration."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from test_release_export import fixture, LRC, URL
from yue2_music_director import acoustic as ac, cover_import as ci
from yue2_music_director import human_feedback as hf, release_assembly as ra
from yue2_music_director import release_delivery as rd, release_export as ex, native_draft as nd


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo=Path(temp.name)
        self.source=fixture(self.repo,"one")
        self.enterContext(patch.object(ex,"retained",return_value=self.source))
        self.enterContext(patch.object(hf,"load",return_value=self.source))
        self.key=hf.identity(self.source)
        self.ratings={"kind":"listening","ratings":dict.fromkeys(hf.DIMENSIONS,"good"),
                      "observations":"Synthetic fixture only","confirmed_preferences":[],"inferred_preferences":[]}
        self.approval={"kind":"release_approval","release":"release","decision":"approve","note":""}
        self.root=self.repo/"results/release-delivery/release/delivery-v1"
        self.ledger=self.repo/"results/release-review/release/delivery-v1"

    def image(self,name="cover.png",size=3000):
        ffmpeg=shutil.which("ffmpeg")
        if not ffmpeg or not shutil.which("ffprobe"):
            if os.environ.get("REQUIRE_REAL_AUDIO_TESTS")=="1":
                self.fail("Required FFmpeg unavailable")
            self.skipTest("FFmpeg required")
        path=self.repo/name
        ac._run([ffmpeg,"-nostdin","-v","error","-f","lavfi","-i",
                 f"color=c=blue:s={size}x{size}","-frames:v","1",
                 "-threads","1","-pix_fmt","rgb24" if path.suffix==".png" else "yuvj420p",
                 "-update","1","-y",str(path)])
        return path

    def assemble(self,artist="Test artist",lrc=LRC):
        expected=0 if lrc else 2
        self.assertEqual(ex.launch(self.repo,"release",["one"],URL,artist=artist,
                                   confirm=True,timing_reader=lambda *a:lrc),expected)
        hf.append(self.repo,"one",self.key,self.ratings)
        hf.append(self.repo,"one",self.key,self.approval)
        self.assertEqual(ra.launch(self.repo,"release",confirm=True),expected)

    def test_real_png_delivery_and_review_without_rewriting(self):
        self.assemble()
        cover=self.image()
        self.assertEqual(rd.launch(self.repo,"release",artwork=cover),0)
        self.assertFalse(self.root.exists())
        self.assertEqual(rd.launch(self.repo,"release",artwork=cover,confirm=True),0)
        self.assertEqual((self.root/"cover.png").read_bytes(),cover.read_bytes())
        manifest=nd.read(self.root/"delivery.json")
        self.assertFalse(manifest["release_approved"])
        self.assertEqual(manifest["metadata"]["artist"],"Test artist")
        self.assertEqual(manifest["metadata"]["tracks"][0]["title"],"one")
        self.assertFalse(self.ledger.exists())
        before={p:nd._sha(p) for p in self.root.rglob("*") if p.is_file()}
        with patch.object(ci,"inspect",side_effect=AssertionError("Do not decode completed cover twice")):
            self.assertEqual(rd.launch(self.repo,"release",confirm=True),0)
            with patch("builtins.input",return_value="no"),self.assertRaises(ValueError):
                rd.launch(self.repo,"release",decision="approve",confirm=True)
            with patch("builtins.input",return_value="APPROVE"):
                self.assertEqual(rd.launch(self.repo,"release",decision="approve",confirm=True),0)
            receipt=nd.read(self.ledger/"000001.json")
            self.assertTrue(receipt["rights_typography_credits_reviewed"])
            self.assertFalse(receipt["publishing_authorized"])
            self.assertEqual(receipt["delivery_manifest_sha256"],before[self.root/"delivery.json"])
            with patch("builtins.input",return_value="REVOKE"):
                self.assertEqual(rd.launch(self.repo,"release",decision="revoke",confirm=True),0)
        self.assertEqual(before,{p:nd._sha(p) for p in before})
        self.assertEqual(nd.read(self.ledger/"000002.json")["decision"],"revoke")
        hf.append(self.repo,"one",self.key,{**self.approval,"decision":"revoke"})
        with self.assertRaisesRegex(ValueError,"approval differs"):
            rd.launch(self.repo,"release")

    def test_real_jpeg_dimensions_and_invalid_images(self):
        good=self.image("cover.jpg")
        self.assertEqual(ci.inspect(good)["codec"],"mjpeg")
        truncated=self.repo/"truncated.jpg"
        truncated.write_bytes(good.read_bytes()[:-2])
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            ci.inspect(truncated)
        small=self.image("small.png",64)
        with self.assertRaisesRegex(ValueError,"3000"):
            ci.inspect(small)
        wrong=self.repo/"wrong.png"
        wrong.write_bytes(good.read_bytes())
        with self.assertRaisesRegex(ValueError,"signature"):
            ci.inspect(wrong)
        good_png=self.image()
        bad=self.repo/"bad.png"
        bad.write_bytes(good_png.read_bytes()[:-12])
        with self.assertRaises(ValueError):
            ci.inspect(bad)
        bad.write_bytes(good_png.read_bytes()+b"trailing")
        with self.assertRaises(ValueError):
            ci.inspect(bad)

    def test_partial_delivery_never_promoted(self):
        self.assemble(lrc=None)
        cover=self.image()
        self.assertEqual(rd.launch(self.repo,"release",artwork=cover,confirm=True),2)
        self.assertEqual(nd.read(self.root/"delivery.json")["status"],"partial_missing_timing")
        with self.assertRaisesRegex(ValueError,"Partial timing"):
            rd.launch(self.repo,"release",decision="approve",confirm=True)
        self.assertFalse(self.ledger.exists())

    def test_missing_credit_and_tampering_fail_closed(self):
        self.assemble(artist="")
        cover=self.image()
        self.assertEqual(rd.launch(self.repo,"release",artwork=cover,confirm=True),0)
        with self.assertRaisesRegex(ValueError,"artist credit"):
            rd.launch(self.repo,"release",decision="approve",confirm=True)
        (self.root/"cover.png").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            rd.launch(self.repo,"release",confirm=True)
        self.assertFalse(self.ledger.exists())

    def test_tampered_delivery_claim_cannot_be_verified(self):
        self.assemble()
        cover=self.image()
        self.assertEqual(rd.launch(self.repo,"release",artwork=cover,confirm=True),0)
        path=self.root/"delivery.json"
        manifest=nd.read(path)
        manifest["release_approved"]=True
        nd.atomic_write(path,manifest)
        with self.assertRaisesRegex(ValueError,"Delivery contract"):
            rd.launch(self.repo,"release")

    def test_fill_omitted_credit_without_reexport_or_inherited_approval(self):
        self.assemble(artist="")
        cover=self.image()
        original=self.repo/"results/exports/songs/one--release"
        before={p:nd._sha(p) for p in original.rglob("*") if p.is_file()}
        with patch.object(ex,"read_timing",side_effect=AssertionError("no timing read")), \
             patch.object(ex,"launch",side_effect=AssertionError("no export replay")):
            self.assertEqual(rd.launch(self.repo,"release",artwork=cover,artist="Explicit Artist",confirm=True),0)
            self.assertEqual(rd.launch(self.repo,"release"),0)
            manifest=nd.read(self.root/"delivery.json")
            self.assertEqual(manifest["metadata"]["artist"],"Explicit Artist")
            self.assertEqual(manifest["metadata"]["tracks"][0]["artist"],"Explicit Artist")
            self.assertEqual(manifest["contract"]["artist_completion"]["original"],"")
            self.assertFalse(manifest["release_approved"])
            self.assertFalse(self.ledger.exists())
            with self.assertRaisesRegex(ValueError,"Existing delivery differs"):
                rd.launch(self.repo,"release",artist="Changed Artist",confirm=True)
            with patch("builtins.input",return_value="APPROVE"):
                self.assertEqual(rd.launch(self.repo,"release",decision="approve",confirm=True),0)
            self.assertEqual(before,{p:nd._sha(p) for p in before})
            self.assertEqual(nd.read(original/"release.json")["contract"]["artist"],"")

    def test_established_artist_cannot_be_replaced(self):
        self.assemble()
        with self.assertRaisesRegex(ValueError,"established export artist"):
            rd.launch(self.repo,"release",artist="Different",confirm=True)
        self.assertFalse(self.root.exists())
