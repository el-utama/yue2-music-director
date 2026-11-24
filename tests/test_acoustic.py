import json
import math
from pathlib import Path
import shutil
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave
from yue2_music_director.acoustic import _parse_loudness, compare


class AcousticTests(unittest.TestCase):
    def test_input_not_output_stats(self):
        stats = _parse_loudness('noise {"input_i":"-14.97","input_tp":"0.09",'
                                '"input_lra":"8.90","output_i":"-23.0"} noise')
        self.assertEqual(stats["integrated_lufs"], -14.97)
        self.assertEqual(stats["true_peak_dbtp"], .09)
        self.assertEqual(stats["loudness_range_lu"], 8.9)

    def test_nonfinite_and_invalid(self):
        stats = _parse_loudness('{"input_i":"-inf","input_tp":"nan","input_lra":"0.0"}')
        self.assertIsNone(stats["integrated_lufs"])
        self.assertIsNone(stats["true_peak_dbtp"])
        with self.assertRaises(ValueError):
            _parse_loudness("missing")

    def test_missing_tools(self):
        with patch("yue2_music_director.acoustic.shutil.which", return_value=None):
            with self.assertRaises(ValueError):
                compare("a.wav", "b.wav")

    def test_gain_and_delta(self):
        from types import SimpleNamespace
        a = {"sha256":"a","duration_seconds":188.5,"channels":2,
             "integrated_lufs":-15.0,"true_peak_dbtp":0.1,"loudness_range_lu":8.0}
        b = {"sha256":"b","duration_seconds":185.5,"channels":2,
             "integrated_lufs":-16.6,"true_peak_dbtp":0.0,"loudness_range_lu":7.0}
        with patch("yue2_music_director.acoustic.shutil.which", return_value="fake"), \
             patch("yue2_music_director.acoustic._run",return_value=SimpleNamespace(stdout="version 1")), \
             patch("yue2_music_director.acoustic._measure",side_effect=[a,b]):
            report = compare("a.wav","b.wav")
        self.assertEqual(report["B_minus_A"]["duration_seconds"],-3.0)
        self.assertEqual(report["B_minus_A"]["integrated_lufs"],-1.6)
        self.assertEqual(report["suggested_playback_gain_db"],{"A":-2.6,"B":-1.0})
        self.assertEqual(report["audio_jobs_created"],0)
        json.dumps(report,allow_nan=False)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"optional FFmpeg tools")
    def test_real_local_wav(self):
        with TemporaryDirectory() as d:
            a,b = Path(d)/"a.wav",Path(d)/"b.wav"
            for p,amp in ((a,10000),(b,5000)):
                with wave.open(str(p),"wb") as f:
                    f.setnchannels(1)
                    f.setsampwidth(2)
                    f.setframerate(16000)
                    f.writeframes(b"".join(struct.pack("<h",round(amp*math.sin(2*math.pi*440*i/16000)))
                                           for i in range(48000)))
            before = a.read_bytes(),b.read_bytes()
            report = compare(a,b)
            self.assertEqual(report["arms"]["A"]["duration_seconds"],3)
            self.assertAlmostEqual(report["B_minus_A"]["integrated_lufs"],-6.02,delta=.2)
            self.assertEqual(before,(a.read_bytes(),b.read_bytes()))
            self.assertFalse(report["identical_file_bytes"])
