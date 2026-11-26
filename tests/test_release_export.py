import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director import release_export as ex, native_draft as nd

URL="http://127.0.0.1:8791/mcp"
LYRICS="[Verse]\nOne two\nThree four"
LRC="[00:01.00]<00:01.00>One <00:01.50>two\n[00:03.25]Three four"
def fixture(repo,job):
    audio=repo/(job+".flac")
    audio.write_bytes(b"synthetic audio")
    sha=nd._sha(audio)
    return {"job":job,"brief":{"title":job,"lyrics":LYRICS},"audio":audio,
            "report":{"acoustic":{"duration_seconds":5.5}},
            "result":{"audio_sha256":sha,"status":"review_required"},
            "evidence":{"job":job,"result_sha256":"fixture"}}


class ExportTests(unittest.TestCase):
    def test_times_and_order(self):
        lrc,srt=ex.timed_text(LRC,LYRICS,5.5)
        self.assertIn("[00:03.250]Three four",lrc)
        self.assertIn("00:00:01,000 --> 00:00:03,250",srt)
        self.assertIn("00:00:03,250 --> 00:00:05,500",srt)
        with self.assertRaises(ValueError):
            ex.timed_text("[00:01.00]One two",LYRICS,5.5)
        with self.assertRaises(ValueError):
            ex.timed_text(LRC.replace("Three four","Wrong"),LYRICS,5.5)

    def test_export_single_album_ep_and_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            tracks={j:fixture(repo,j) for j in ("one","two")}
            with patch.object(ex,"retained",side_effect=lambda r,j:tracks[j]):
                reader=lambda t,u:LRC
                self.assertEqual(ex.launch(repo,"one",["one"],URL,timing_reader=lambda *a:self.fail("read")),0)
                self.assertFalse((repo/"results").exists())
                self.assertEqual(ex.launch(repo,"one",["one"],URL,confirm=True,timing_reader=reader),0)
                self.assertEqual(ex.launch(repo,"one",["one"],URL,confirm=True,timing_reader=lambda *a:self.fail("repeat read")),0)
                for kind,folder in (("album","albums"),("ep","eps")):
                    self.assertEqual(ex.launch(repo,kind,["two","one"],URL,kind=kind,title="Collection",confirm=True,timing_reader=reader),0)
                    root=repo/"results/exports"/folder/("Collection--"+kind)
                    self.assertTrue((root/"01 - two/01 - two.srt").exists())
                    self.assertTrue((root/"02 - one/02 - one.flac").exists())
                root=repo/"results/exports/songs/one--one"
                self.assertEqual((root/"one.flac").read_bytes(),tracks["one"]["audio"].read_bytes())
                (root/"one.txt").write_text("tampered")
                with self.assertRaisesRegex(ValueError,"hashes differ"):
                    ex.launch(repo,"one",["one"],URL,confirm=True,timing_reader=reader)

    def test_missing_timing_is_explicit_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            t=fixture(repo,"one")
            with patch.object(ex,"retained",return_value=t):
                self.assertEqual(ex.launch(repo,"one",["one"],URL,confirm=True,timing_reader=lambda *a:None),2)
            root=repo/"results/exports/songs/one--one"
            self.assertTrue((root/"one.flac").exists())
            self.assertTrue((root/"one.txt").exists())
            self.assertFalse((root/"one.srt").exists())
            self.assertFalse((root/"one.lrc").exists())
            self.assertEqual(nd.read(root/"release.json")["status"],"partial_missing_timing")
