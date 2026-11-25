import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director.temporal_evidence import parse_lrc,inspect_timing
from yue2_music_director.native_recognition import _write


class TemporalEvidenceTests(unittest.TestCase):
    def test_enhanced_and_plain_lrc(self):
        rows=parse_lrc("[00:01.00]<00:01.00>one <00:01.50>two\n[00:03.00]three",5)
        self.assertEqual(rows[0]["text"],"one two")
        self.assertEqual(rows[0]["word_anchors"][1]["start_seconds"],1.5)
        self.assertEqual(rows[0]["word_anchors"][0]["provenance"],"unknown_matched_or_interpolated")
        self.assertEqual(rows[1]["word_anchors"],[])

    def test_invalid_timing(self):
        for text in ("[00:60.00]one","[00:05.00]one",
                     "[00:02.00]one\n[00:01.00]two",
                     "[00:01.00]<00:00.99>one",
                     "[00:01.00]one <00:02.00>two",
                     "[00:01.00]<00:03.00>one\n[00:02.00]two"):
            with self.subTest(text=text),self.assertRaises(ValueError):
                parse_lrc(text,5)

    @patch("yue2_music_director.temporal_evidence.Client")
    def test_read_only_existing_metadata(self,factory):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"audio.flac"
            source.write_bytes(b"fixture")
            lyrics=root/"lyrics.txt"
            lyrics.write_text("[Verse]\none two\nthree",encoding="utf-8")
            baseline=root/"baseline.json"
            _write(baseline,{"provider":"whisper","text":"one three"})
            client=factory.return_value.connect.return_value
            client.tools.return_value=[{"name":"library_song_get"},{"name":"library_song_files"}]
            def check(lrc,name,nullable=False):
                def respond(tool,args):
                    if tool=="library_song_files":
                        return {"audio":str(source.resolve())}
                    if tool=="library_song_get":
                        if args["response_format"]=="concise":
                            return {"id":"song","metadata":None if nullable else {"has_karaoke":bool(lrc)}}
                        self.assertEqual(args["response_format"],"detailed")
                        return {"id":"song","metadata":{"lrc":lrc}}
                    raise AssertionError("Unexpected mutation: "+tool)
                client.call.reset_mock()
                client.call.side_effect=respond
                result=inspect_timing(source,"song",lyrics,baseline,"en",5,root/(name+".json"),
                                      "http://127.0.0.1:1234/mcp")
                self.assertFalse(result["correction_allowed"])
                self.assertFalse(result["phonetic_alignment_verified"])
                self.assertEqual(result["recognition_calls"],0)
                self.assertEqual([c.args[0] for c in client.call.call_args_list],
                                 (["library_song_files","library_song_get","library_song_get","library_song_files"] if lrc else
                                  ["library_song_files","library_song_get","library_song_files"]))
                return result
            result=check("[00:01.00]<00:01.00>one <00:01.50>two\n[00:03.00]three","valid")
            self.assertEqual(result["status"],"karaoke_display_anchors_only")
            self.assertEqual(result["lines"][0]["asr_line_edits"],1)
            self.assertFalse(result["audio_timestamps_verified"])
            self.assertEqual(check(None,"missing")["status"],"no_existing_karaoke")
            self.assertEqual(check(None,"null",nullable=True)["status"],"no_existing_karaoke")
            self.assertEqual(check("[00:01.00]wrong words\n[00:03.00]three","wrong")["status"],
                             "karaoke_evidence_blocked")


    def test_unreadable_metadata_never_claims_absence(self):
        from yue2_music_director.temporal_evidence import karaoke_metadata
        for data in ({"content":[{"type":"text","text":"truncated"}]},
                     {"id":"wrong","metadata":None},{"id":"song"},
                     {"id":"song","metadata":[]},
                     {"id":"song","metadata":{"has_karaoke":True}}):
            with self.subTest(data=data),self.assertRaises(ValueError):
                karaoke_metadata(data,"song",detailed=True)


    @patch("yue2_music_director.temporal_evidence.native_song_read")
    @patch("yue2_music_director.temporal_evidence.Client")
    def test_incomplete_mcp_uses_native_read_once(self,factory,native):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"audio.flac"
            source.write_bytes(b"fixture")
            lyrics=root/"lyrics.txt"
            lyrics.write_text("[Verse]\none two",encoding="utf-8")
            baseline=root/"baseline.json"
            _write(baseline,{"provider":"whisper","text":"one"})
            client=factory.return_value.connect.return_value
            client.tools.return_value=[{"name":"library_song_get"},{"name":"library_song_files"}]
            client.call.side_effect=[{"audio":str(source.resolve())},
                {"content":[{"type":"text","text":"truncated"}]},
                {"audio":str(source.resolve())}]
            native.return_value={"id":"song","metadata":{"lrc":"[00:01.00]one two"}}
            url="http://127.0.0.1:1234/mcp"
            result=inspect_timing(source,"song",lyrics,baseline,"en",5,root/"timing.json",url)
            native.assert_called_once_with(url,"song")
            self.assertEqual(result["metadata_transport"],"native_http_get")
            self.assertEqual(result["status"],"karaoke_display_anchors_only")
            self.assertFalse(result["correction_allowed"])
            self.assertEqual(result["recognition_calls"],0)

    def test_native_read_uses_exact_loopback_get_and_rejects_remote(self):
        from yue2_music_director.temporal_evidence import native_song_read
        from email.message import Message
        with patch("yue2_music_director.temporal_evidence.build_opener") as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            headers=Message()
            headers["Content-Type"]="application/json"
            response.headers=headers
            response.read.return_value=b'{"id":"fixture","metadata":null}'
            result=native_song_read("http://127.0.0.1:1234/mcp","fixture")
            self.assertIsNone(result["metadata"])
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url,"http://127.0.0.1:1234/v1/library/songs/fixture")
            self.assertEqual(request.get_method(),"GET")
            with self.assertRaises(ValueError):
                native_song_read("http://example.com/mcp","fixture")
            with self.assertRaises(ValueError):
                native_song_read("http://127.0.0.1:1234/other","fixture")
            opener.return_value.open.assert_called_once()
