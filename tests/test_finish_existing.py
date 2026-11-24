import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director.finish import finish
from yue2_music_director.multilingual_fidelity import assess, compare


class MultilingualTests(unittest.TestCase):
    def test_word_language(self):
        r=assess("[Verse]\nAku masih di sini","Aku di sini","id")
        self.assertEqual(r["WER"]["edits"],1)
        self.assertEqual(r["primary_metric"],"WER")

    def test_character_language(self):
        r=assess("[Verse]\n君が好き","君がすき","ja")
        self.assertEqual(r["CER"]["edits"],1)
        self.assertNotIn("WER",r)
        self.assertEqual(r["primary_metric"],"CER")

    def test_combining_marks(self):
        r=assess("[Verse]\ncafé","cafe\u0301","fr")
        self.assertEqual(r["CER"]["edits"],0)
        self.assertEqual(r["WER"]["edits"],0)

    def test_unknown_and_regression(self):
        with self.assertRaises(ValueError):
            assess("[Verse]\nHello","Hello","xx")
        self.assertEqual(compare("[Verse]\nHello world","Hello world","Hello","en")["status"],"regression")


class FinishTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.inputs=[self.root/n for n in ("mix.flac","ins.wav","voice.wav","lyrics.txt","asr.json")]
        for p in self.inputs[:3]:
            p.write_bytes(b"fixture")
        self.inputs[3].write_text("[Verse]\nhello world",encoding="utf-8")
        self.inputs[4].write_text(json.dumps({"provider":"whisper","text":"hello world"}),encoding="utf-8")

    @patch("yue2_music_director.finish.capture")
    @patch("yue2_music_director.finish.process")
    def test_no_candidate_no_recognition(self,process,capture):
        process.return_value={"status":"no_safe_effect","attacks_edited":0}
        r=finish(*self.inputs,self.root/"out","en",confirm=True)
        self.assertEqual(r["status"],"no_candidate")
        capture.assert_not_called()
        self.assertEqual(r["recognition_calls"],0)
        with self.assertRaises(ValueError):
            finish(*self.inputs,self.root/"out","en",confirm=True)

    @patch("yue2_music_director.finish.capture")
    @patch("yue2_music_director.finish.process")
    def test_regression_retains_source(self,process,capture):
        def dynamics(a,b,c,out,max_db):
            out.mkdir()
            (out/"candidate.flac").write_bytes(b"candidate")
            return {"status":"candidate_created","attacks_edited":10}
        def recognise(audio,out,url,confirm):
            out.mkdir()
            (out/"recognition.json").write_text(json.dumps({"provider":"whisper","text":"hello"}),encoding="utf-8")
            return {"recognition_calls":1}
        process.side_effect=dynamics
        capture.side_effect=recognise
        r=finish(*self.inputs,self.root/"out","en",confirm=True)
        self.assertEqual(r["status"],"retain_original_asr_regression")
        self.assertEqual(r["provisional_output"],str(self.inputs[0]))
        self.assertFalse(r["automatic_acceptance"])
        capture.assert_called_once()

    @patch("yue2_music_director.finish.capture")
    @patch("yue2_music_director.finish.process")
    def test_no_permission(self,process,capture):
        with self.assertRaises(ValueError):
            finish(*self.inputs,self.root/"out","en")
        process.assert_not_called()
        capture.assert_not_called()
