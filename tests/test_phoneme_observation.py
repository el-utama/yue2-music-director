import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from yue2_music_director import phoneme_observation as po
from yue2_music_director.native_recognition import _sha


class PhonemeObservationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.audio = self.root/"fixture.wav"
        with wave.open(str(self.audio), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(b"\x01\x00"*16000)
        self.weights = self.root/"model.onnx"
        self.weights.write_bytes(b"fixture")
        self.vocab = self.root/"vocab.json"
        tokens = ["<pad>","<s>","</s>","<unk>","a","b"] + [
            f"phone{i}" for i in range(6,392)]
        self.vocab.write_text(json.dumps(dict(zip(tokens,range(392)))),encoding="utf-8")
        self.reference = self.root/"reference.lab"
        self.reference.write_text("0 5000000 a\n5000000 10000000 b\n",encoding="utf-8")
        self.out = self.root/"report.json"

    def test_ctc_repetition_and_blank_order(self):
        rows = po.collapse_ctc([4,4,0,4,5,5,0,3],po.vocabulary(self.vocab))
        self.assertEqual([row["token"] for row in rows],["a","a","b","<unk>"])
        self.assertEqual(rows[0]["end_frame_exclusive"],2)
        self.assertEqual(rows[1]["first_frame"],3)

    def test_observation_independent_of_reference_and_no_acceptance(self):
        with patch.object(po,"WEIGHTS_SHA",_sha(self.weights)), \
             patch.object(po,"infer",return_value=([4,0,5],"fixture")) as infer:
            report=po.observe(self.audio,self.weights,self.vocab,self.out,
                              reference=self.reference,confirm=True)
            infer.assert_called_once_with(self.audio,self.weights,1.0)
            self.assertEqual(report["reference_comparison"]["token_edits"],0)
            self.assertFalse(report["reference_conditioned"])
            self.assertFalse(report["correction_allowed"])
            self.assertFalse(report["automatic_acceptance"])
            self.assertTrue(self.out.exists())

    def test_unknown_reference_inventory_blocks_before_inference(self):
        self.reference.write_text("0 10000000 SIL\n",encoding="utf-8")
        with patch.object(po,"WEIGHTS_SHA",_sha(self.weights)),patch.object(po,"infer") as infer:
            with self.assertRaisesRegex(ValueError,"inventory"):
                po.observe(self.audio,self.weights,self.vocab,self.out,
                           reference=self.reference,confirm=True)
            infer.assert_not_called()
            self.assertFalse(self.out.exists())

    def test_weights_and_confirmation_block_before_inference(self):
        with patch.object(po,"infer") as infer:
            for confirm in (True,False):
                with self.assertRaises(ValueError):
                    po.observe(self.audio,self.weights,self.vocab,self.out,confirm=confirm)
            infer.assert_not_called()
