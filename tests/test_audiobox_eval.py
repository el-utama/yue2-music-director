import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from yue2_music_director import audiobox_eval as aes
from yue2_music_director.native_recognition import _sha


class AudioBoxTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.audio = [self.root/"A.flac", self.root/"B.flac"]
        for p in self.audio:
            p.write_bytes(p.name.encode())
        self.weights = self.root/"model.safetensors"
        self.weights.write_bytes(b"fixture")
        self.out = self.root/"result.json"

    def test_confirmation_and_checkpoint_guards(self):
        with self.assertRaises(ValueError):
            aes.evaluate(self.audio,self.weights,self.out)
        with self.assertRaises(ValueError):
            aes.evaluate(self.audio,self.weights,self.out,confirm=True)
        self.assertFalse(self.out.exists())

    def test_valid_output_from_official_api_shape(self):
        predictor = Mock()
        predictor.forward.side_effect = [
            [{"CE":5.0,"CU":6.0,"PC":3.0,"PQ":7.0}],
            [{"CE":5.2,"CU":6.1,"PC":3.0,"PQ":7.1}]]
        probe = SimpleNamespace(stdout=json.dumps({"streams":[
            {"duration":"185.438667","channels":2,"sample_rate":"48000"}]}))
        with patch.object(aes,"WEIGHTS_SHA256",_sha(self.weights)), \
             patch.object(aes,"_predictor",return_value=(predictor,{"audiobox":"0.0.4"})), \
             patch("shutil.which",return_value="ffprobe"), \
             patch("yue2_music_director.acoustic._run",return_value=probe):
            result = aes.evaluate(self.audio,self.weights,self.out,confirm=True)
            self.assertEqual([r["audio_sha256"] for r in result["rows"]],
                             [_sha(p) for p in self.audio])
            self.assertEqual(result["rows"][1]["scores"]["PQ"],7.1)
            self.assertFalse(result["automatic_acceptance"])
            self.assertEqual(predictor.forward.call_count,2)
            with self.assertRaises(ValueError):
                aes.evaluate(self.audio,self.weights,self.out,confirm=True)
            self.assertEqual(predictor.forward.call_count,2)

    def test_nonfinite_output_not_saved(self):
        predictor=Mock()
        predictor.forward.return_value=[{"CE":5,"CU":6,"PC":3,"PQ":float("nan")}]
        probe=SimpleNamespace(stdout=json.dumps({"streams":[
            {"duration":"10","channels":1,"sample_rate":"16000"}]}))
        with patch.object(aes,"WEIGHTS_SHA256",_sha(self.weights)), \
             patch.object(aes,"_predictor",return_value=(predictor,{})), \
             patch("shutil.which",return_value="ffprobe"), \
             patch("yue2_music_director.acoustic._run",return_value=probe):
            with self.assertRaises(ValueError):
                aes.evaluate(self.audio,self.weights,self.out,confirm=True)
        self.assertFalse(self.out.exists())
