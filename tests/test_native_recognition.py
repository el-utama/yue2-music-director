import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from yue2_music_director.native_recognition import capture, review, BUSY_KEYS, _busy_keys


def response(text):
    return {"provider":"whisper","text":text}


class NativeRecognitionTests(unittest.TestCase):
    def test_review_localizes_and_preserves_counts(self):
        report = review("[Verse]\none two\nthree four\n[Chorus]\nfive six",
                        response("one extra two three four five six"),
                        response("one two three wrong five six"))
        self.assertEqual(report["arms"]["A"]["insertions"],1)
        self.assertEqual(report["reference_lines"][0]["A_count"],1)
        self.assertEqual(report["reference_lines"][1]["B_count"],1)
        self.assertFalse(report["human_verified"])
        self.assertEqual(report["quality_decision"],"human_review_required")
        self.assertEqual(report["recognition_calls"],0)

    def test_boundary_insertions_not_assigned(self):
        report = review("[Verse]\none two\nthree four",
                        response("one two extra three four"),response("one two three four"))
        self.assertEqual(len(report["boundary_insertions"]["A"]),1)
        self.assertEqual(sum(x["A_count"] for x in report["reference_lines"]),0)
        self.assertEqual(report["boundary_insertions"]["A"][0]["preceding_line"]["line_index"],1)

    def test_invalid_response(self):
        for bad in ({}, {"provider":"openrouter","text":"one"},response(" ")):
            with self.assertRaises(ValueError):
                review("[Verse]\none",bad,response("one"))

    def test_capture_guards_and_no_retry(self):
        with TemporaryDirectory() as d:
            audio=Path(d)/"a.flac"
            audio.write_bytes(b"synthetic fixture")
            out=Path(d)/"result"
            with self.assertRaises(ValueError):
                capture(audio,out)
            c=MagicMock()
            c.tools.return_value=[{"name":x} for x in
                ("karaoke_settings_get","studio_status","lyrics_recognise")]
            settings={"provider":"whisper","enabled":True,"ready":True,"download":None,
                      "models":[{"id":"crisperwhisper-turbo","installed":True}]}
            status={k:None for k in BUSY_KEYS}
            with patch("yue2_music_director.native_recognition.Client") as factory:
                factory.return_value.connect.return_value=c
                c.call.side_effect=[{"structuredContent":{**settings,"provider":"openrouter"}}]
                with self.assertRaises(ValueError):
                    capture(audio,out,"http://localhost:1234/mcp",confirm=True)
                self.assertFalse(out.exists())
                c.call.side_effect=[{"structuredContent":settings},{"structuredContent":status},
                                    TimeoutError("unknown outcome")]
                with self.assertRaises(TimeoutError):
                    capture(audio,out,"http://localhost:1234/mcp",confirm=True)
                self.assertTrue((out/"submission.json").exists())
                self.assertFalse((out/"receipt.json").exists())
                count=c.call.call_count
                with self.assertRaises(ValueError):
                    capture(audio,out,"http://localhost:1234/mcp",confirm=True)
                self.assertEqual(c.call.call_count,count)

    def test_terminal_stem_record_is_not_active(self):
        status = {k:None for k in BUSY_KEYS}
        terminal = {"song_id":"synthetic-id","done":True,"error":None,"progress":1.0}
        status["stems"] = terminal
        self.assertEqual(_busy_keys(status), [])
        for change in ({"done":False},{"error":"failure"},{"progress":0.5},
                       {"progress":True},{"song_id":""}):
            self.assertEqual(_busy_keys({**status,"stems":{**terminal,**change}}),["stems"])
        self.assertEqual(_busy_keys({**status,"processing":{"done":True}}),["processing"])
        self.assertEqual(_busy_keys({**status,"song_jobs":[{"id":"active"}]}),["song_jobs"])
        self.assertEqual(_busy_keys({**status,"stems":{}}),["stems"])
        self.assertEqual(_busy_keys({**status,"stems":{"done":True}}),["stems"])
        with self.assertRaises(ValueError):
            _busy_keys({})

    def test_success_keeps_raw_response(self):
        with TemporaryDirectory() as d:
            audio=Path(d)/"a.wav"
            audio.write_bytes(b"fixture")
            out=Path(d)/"result"
            c=MagicMock()
            c.tools.return_value=[{"name":x} for x in
                ("karaoke_settings_get","studio_status","lyrics_recognise")]
            settings={"provider":"whisper","enabled":True,"ready":True,"download":None,
                      "models":[{"id":"crisperwhisper-turbo","installed":True}]}
            raw=response("one two")
            c.call.side_effect=[{"structuredContent":settings},
                                {"structuredContent":{**{k:None for k in BUSY_KEYS},
                                    "stems":{"song_id":"synthetic-id","done":True,
                                             "error":None,"progress":1.0}}},
                                {"structuredContent":raw}]
            with patch("yue2_music_director.native_recognition.Client") as factory:
                factory.return_value.connect.return_value=c
                result=capture(audio,out,"http://localhost:1234/mcp",confirm=True)
            self.assertEqual(result["recognition_calls"],1)
            self.assertEqual(json.loads((out/"recognition.json").read_text()),raw)
            self.assertTrue((out/"receipt.json").exists())
