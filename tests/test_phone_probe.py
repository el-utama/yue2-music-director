import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from yue2_music_director import phone_probe as p
from yue2_music_director.native_recognition import _sha


class PhoneProbeTests(unittest.TestCase):
    def test_ctc_blank_and_repeat(self):
        vocab={0:"<pad>",1:"<s>",2:"</s>",3:"<unk>",4:"n",5:"s"}
        self.assertEqual(p.collapse([0,4,4,0,4,5,5,3,0],vocab),["n","n","s","<unk>"])
        self.assertEqual(p.compare_phones(["n","s"],["n","n","s","<unk>"],vocab)["edits"],2)
        with self.assertRaises(ValueError):
            p.compare_phones(["not-in-vocabulary"],["n"],vocab)

    def test_bounded_probe_with_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            weights=root/"model.onnx"
            weights.write_bytes(b"fixture")
            vocab=root/"vocab.json"
            symbols=["<pad>","<s>","</s>","<unk>","n","s","t","ə"]+[f"p{i}" for i in range(8,392)]
            vocab.write_text(json.dumps({s:i for i,s in enumerate(symbols)}),encoding="utf-8")
            audio=root/"audio.wav"
            with wave.open(str(audio),"wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(16000)
                f.writeframes(b"\x00\x01"*16000)
            out=root/"report.json"
            reference=root/"reference.txt"
            reference.write_text("n s",encoding="utf-8")
            with patch.object(p,"WEIGHTS_SHA256",_sha(weights)),patch.object(p,"recognize",return_value=([0,4,4,0,5],"fixture")) as run:
                with self.assertRaises(ValueError):
                    p.probe(audio,weights,vocab,out,reference)
                run.assert_not_called()
                report=p.probe(audio,weights,vocab,out,reference,confirm=True)
                self.assertEqual(report["comparison"]["token_disagreement_rate"],0)
                self.assertFalse(report["pronunciation_verified"])
                self.assertFalse(report["correction_allowed"])
                self.assertEqual(report["phone_inference_calls"],1)
                self.assertEqual(report["hypothesis"],["n","s"])
                with self.assertRaises(ValueError):
                    p.probe(audio,weights,vocab,out,reference,confirm=True)
                run.assert_called_once()

    def test_pcm_wrong_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio=Path(tmp)/"audio.wav"
            with wave.open(str(audio),"wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(8000)
                f.writeframes(b"\x00\x01"*8000)
            with self.assertRaises(ValueError):
                p.read_pcm(audio)
