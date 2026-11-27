"""Required synthetic real-audio FFmpeg regressions, no Studio or provider."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from yue2_music_director import audio_finishing as fin, finish_audio as fa, acoustic as ac


class GainPolicyTests(unittest.TestCase):
    def test_gain_plan_and_invalid_evidence(self):
        base={"integrated_lufs":-14.0,"true_peak_dbtp":-0.19,"loudness_range_lu":4.5}
        self.assertEqual(fa.plan_gain(base),-0.86)
        self.assertEqual(fa.plan_gain({**base,"true_peak_dbtp":-1}),0)
        for key,value in (("integrated_lufs",None),("integrated_lufs",-70),
                          ("integrated_lufs",float("-inf")),("true_peak_dbtp",0.1),
                          ("true_peak_dbtp",float("nan")),("loudness_range_lu",-1),
                          ("loudness_range_lu",None)):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                fa.plan_gain({**base,key:value})


class RealFinishingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            if os.environ.get("REQUIRE_REAL_AUDIO_TESTS")=="1":
                raise AssertionError("Required FFmpeg/ffprobe unavailable in CI")
            raise unittest.SkipTest("FFmpeg and ffprobe required for local real-audio tests")
        cls.ffmpeg,cls.ffprobe,cls.versions=fa.tools()

    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo=Path(tmp.name)
        self.audio=self.repo/"fixture.flac"

    def fixture(self,*,level=0.9772,channels=2,bits=24,rate=48000):
        signal=f"{level}*sin(2*PI*440*t)"
        if channels==2:
            signal+="|0.1*sin(2*PI*660*t)"
        ac._run([self.ffmpeg,"-nostdin","-v","error","-f","lavfi","-i",
                 f"aevalsrc={signal}:s={rate}:d=4","-c:a","flac",
                 "-sample_fmt","s16" if bits==16 else "s32","-bits_per_raw_sample",str(bits),
                 "-n",str(self.audio)])
        sha=ac._hash(self.audio)
        measured=ac._measure(self.audio,self.ffmpeg,self.ffprobe)
        source={"job":"one","audio":self.audio,"result":{"audio_sha256":sha},
                "report":{"acoustic":measured},"evidence":{"result_sha256":"a"*64}}
        self.load=self.enterContext(patch.object(fin,"load",return_value=source))
        self.source=source
        self.original=self.audio.read_bytes()
        return self.repo/"results/audio-finishing/one/gain-v1"

    def test_real_stereo_gain_pcm_and_idempotent_resume(self):
        root=self.fixture()
        with patch.object(fa,"tools",side_effect=AssertionError("plan must not probe")):
            self.assertEqual(fin.launch(self.repo,"one"),0)
        self.assertFalse(root.exists())
        self.assertEqual(fin.launch(self.repo,"one",confirm=True),0)
        result=fin.nd.read(root/"report.json")
        self.assertEqual(result["status"],"candidate_verified")
        a,b=result["source_measurement"],result["candidate_measurement"]
        self.assertEqual(a["geometry"]["sample_count_per_channel"],192000)
        self.assertEqual(b["geometry"],a["geometry"])
        self.assertLessEqual(b["acoustic"]["true_peak_dbtp"],-1)
        self.assertEqual(result["candidate_pcm_sha256"],fin.nd.read(root/"plan.json")["expected_pcm_sha256"])
        self.assertEqual(result["candidate_pcm_sha256"],fa.pcm_hash(root/"candidate.flac",self.ffmpeg))
        self.assertEqual(self.audio.read_bytes(),self.original)
        self.assertEqual(result["preferred_variant"],"original")
        self.assertFalse(result["automatic_acceptance"])
        self.assertFalse(result["release_approved"])
        self.assertFalse(result["clipping_repaired"])
        self.assertTrue(result["timeline_preserved"])
        self.assertEqual([result[k] for k in ("studio_jobs","recognition_calls","moss_calls","provider_calls")],[0]*4)
        with patch.object(fa,"tools",side_effect=AssertionError("already complete")), \
             patch.object(fa,"render",side_effect=AssertionError("duplicate render")):
            self.assertEqual(fin.launch(self.repo,"one",confirm=True),0)
            self.assertEqual(fin.launch(self.repo,"one"),0)
        (root/"candidate.flac").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError,"candidate identity"):
            fin.launch(self.repo,"one",confirm=True)

    def test_real_mono_16_bit_to_24_bit(self):
        root=self.fixture(channels=1,bits=16,rate=44100)
        self.assertEqual(fin.launch(self.repo,"one",confirm=True),0)
        result=fin.nd.read(root/"report.json")
        a,b=result["source_measurement"]["geometry"],result["candidate_measurement"]["geometry"]
        self.assertEqual(a["bits_per_sample"],16)
        self.assertEqual(b["bits_per_sample"],24)
        for key in ("channels","sample_count_per_channel","sample_rate_hz"):
            self.assertEqual(a[key],b[key])
        self.assertEqual(self.audio.read_bytes(),self.original)

    def test_real_already_safe_no_candidate(self):
        root=self.fixture(level=0.2)
        with patch.object(fa,"render",side_effect=AssertionError("no-change must not render")):
            self.assertEqual(fin.launch(self.repo,"one",confirm=True),0)
        result=fin.nd.read(root/"report.json")
        self.assertEqual(result["status"],"no_change")
        self.assertIsNone(result["candidate_file"])
        self.assertFalse((root/"candidate.flac").exists())
        self.assertEqual(self.audio.read_bytes(),self.original)

    def test_real_silence_refused(self):
        root=self.fixture(level=0,channels=1)
        with self.assertRaises(ValueError):
            fin.launch(self.repo,"one",confirm=True)
        self.assertFalse(root.exists())

    def test_interrupted_complete_candidate_verified_without_rerender(self):
        root=self.fixture()
        render=fa.render
        def interrupt(*args):
            render(*args)
            raise OSError("simulated interruption after lossless render")
        with patch.object(fa,"render",side_effect=interrupt),self.assertRaises(OSError):
            fin.launch(self.repo,"one",confirm=True)
        partial=root/".candidate-incomplete.flac"
        sha=ac._hash(partial)
        plan=(root/"plan.json").read_bytes()
        self.assertFalse((root/"report.json").exists())
        with patch.object(fa,"render",side_effect=AssertionError("existing output must not rerender")):
            self.assertEqual(fin.launch(self.repo,"one",confirm=True),0)
        self.assertEqual(sha,ac._hash(root/"candidate.flac"))
        self.assertEqual(plan,(root/"plan.json").read_bytes())
        self.assertFalse(partial.exists())

    def test_interrupted_corrupt_candidate_preserved(self):
        root=self.fixture()
        def interrupt(source,target,*args):
            target.write_bytes(b"partial flac")
            raise ValueError("interruption")
        with patch.object(fa,"render",side_effect=interrupt),self.assertRaises(ValueError):
            fin.launch(self.repo,"one",confirm=True)
        partial=root/".candidate-incomplete.flac"
        with patch.object(fa,"render",side_effect=AssertionError("must not overwrite")),self.assertRaises(ValueError):
            fin.launch(self.repo,"one",confirm=True)
        self.assertEqual(partial.read_bytes(),b"partial flac")
        self.assertFalse((root/"report.json").exists())
        self.assertEqual(fin.launch(self.repo,"one",variant="gain-retry",confirm=True),0)
        self.assertEqual(partial.read_bytes(),b"partial flac")

    def test_source_mutation_blocks_completion(self):
        root=self.fixture()
        render=fa.render
        def changed(source,target,*args):
            render(source,target,*args)
            source.write_bytes(b"changed source")
        with patch.object(fa,"render",side_effect=changed),self.assertRaisesRegex(ValueError,"Original source changed"):
            fin.launch(self.repo,"one",confirm=True)
        self.assertFalse((root/"report.json").exists())
        self.assertTrue((root/".candidate-incomplete.flac").exists())
