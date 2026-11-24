import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from yue2_music_director.acoustic import compare,_run
from yue2_music_director.native_headroom import gain_plan,corrected_pass,continue_preview
from yue2_music_director.native_process import effect_request
from yue2_music_director.native_recognition import _sha,_write,BUSY_KEYS


class HeadroomTests(unittest.TestCase):
    def test_observed_measurement_shape(self):
        a={"duration_seconds":185.438667,"sample_rate_hz":48000,"channels":2,
           "integrated_lufs":-16.6,"true_peak_dbtp":0.0,"sha256":"a"}
        b={**a,"integrated_lufs":-17.07,"true_peak_dbtp":-0.45,"sha256":"b"}
        before={"arms":{"A":a,"B":b}}
        self.assertAlmostEqual(gain_plan(before),-0.60)
        after={"arms":{"A":a,"B":{**b,"integrated_lufs":-17.67,"true_peak_dbtp":-1.05}}}
        self.assertTrue(corrected_pass(before,after,-0.6))
        for change in ({"channels":1},{"true_peak_dbtp":0.01},{"integrated_lufs":-18.0},
                       {"true_peak_dbtp":None},{"true_peak_dbtp":-1.1}):
            with self.assertRaises(ValueError):
                gain_plan({"arms":{"A":a,"B":{**b,**change}}})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
    @patch("yue2_music_director.native_headroom.Client")
    @patch("yue2_music_director.native_headroom.recognition_preflight")
    @patch("yue2_music_director.native_headroom.capture")
    def test_existing_preview_continuation(self,capture,ready,factory):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=root/"source.flac"
            directory=root/"transaction"
            directory.mkdir()
            raw=directory/"preview.flac"
            exe=shutil.which("ffmpeg")
            for path,gain in ((source,0.97),(raw,0.94)):
                _run([exe,"-nostdin","-v","error","-f","lavfi","-i",
                      f"aevalsrc={gain}*sin(2*PI*440*t):s=48000:d=4",
                      "-ac","1","-c:a","flac","-sample_fmt","s32","-bits_per_raw_sample","24",str(path)])
            lyrics=root/"lyrics.txt"
            lyrics.write_text("[Verse]\none two",encoding="utf-8")
            baseline=root/"baseline.json"
            _write(baseline,{"provider":"whisper","text":"one two"})
            request=effect_request("song","naturalize",0.2)
            run={"id":"run","song_id":"song","stages":["naturalize"],
                 "request":{"naturalize":request["naturalize"]},"done":True,"preview_ready":True,"error":None}
            original,preview_hash=_sha(source),_sha(raw)
            _write(directory/"submission.json",{"state":"SUBMITTING","request":request,
                   "source_sha256":original,"screening":{"language":"en","lyrics_sha256":_sha(lyrics),
                   "baseline_asr_sha256":_sha(baseline)}})
            _write(directory/"receipt.json",{"started":True})
            _write(directory/"run_identity.json",{"run_id":"run","request":request})
            _write(directory/"report.json",{"status":"preview_acoustic_blocked","run_id":"run",
                   "request":request,"source_sha256":original,"preview_sha256":preview_hash,
                   "acoustic":compare(source,raw)})
            client=factory.return_value.connect.return_value
            def response(name,args):
                if name=="processing_get":
                    return {"run":run}
                if name=="studio_status":
                    return {**{k:None for k in BUSY_KEYS},"processing":run}
                raise AssertionError(name)
            client.call.side_effect=response
            def recognize(audio,out,url,**kwargs):
                self.assertEqual(kwargs["pending_processing"],run)
                out.mkdir()
                _write(out/"recognition.json",{"provider":"whisper","text":"one two"})
                return {"recognition_calls":1}
            capture.side_effect=recognize
            result=continue_preview(source,directory,lyrics,baseline,"en","http://localhost:1234/mcp",confirm=True)
            self.assertEqual(result["status"],"candidate_nonregression_unverified")
            self.assertLessEqual(result["after"]["arms"]["B"]["true_peak_dbtp"],-1)
            self.assertEqual(result["processing_calls"],0)
            self.assertEqual(result["recognition_calls"],1)
            self.assertEqual(_sha(source),original)
            self.assertEqual(_sha(raw),preview_hash)
            capture.assert_called_once()
            with self.assertRaises(ValueError):
                continue_preview(source,directory,lyrics,baseline,"en","http://localhost:1234/mcp",confirm=True)
            capture.assert_called_once()
