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
        self.assertEqual(lrc,LRC)
        self.assertIn("00:00:01,000 --> 00:00:02,000",srt)
        self.assertIn("00:00:03,250 --> 00:00:05,500",srt)
        with self.assertRaises(ValueError):
            ex.timed_text("[00:01.00]One two",LYRICS,5.5)
        with self.assertRaises(ValueError):
            ex.timed_text(LRC.replace("Three four","Wrong"),LYRICS,5.5)

    def test_native_gap_example_and_section_labels(self):
        source="[00:01.50][Verse 1]\n[00:02.00]<00:02.00>First <00:02.40>line\n[00:05.25]Second line\n[01:02.10]Last line"
        words="[Verse 1]\nFirst line\nSecond line\nLast line"
        raw,srt=ex.timed_text(source,words,70)
        self.assertEqual(raw,source)
        self.assertEqual(srt,"1\n00:00:02,000 --> 00:00:02,800\nFirst line\n\n"
                             "2\n00:00:05,250 --> 00:00:09,250\nSecond line\n\n"
                             "3\n00:01:02,100 --> 00:01:05,100\nLast line\n")
        _,short=ex.timed_text(source,words,63)
        self.assertIn("00:01:02,100 --> 00:01:03,000",short)

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
                    self.assertEqual((root/"01 - two/01 - two.clean.txt").read_bytes(),b"One two\nThree four\n")
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


    def test_clean_lyrics_preserve_repeated_stanzas_and_sung_parentheticals(self):
        track={"brief":{"lyrics":"[Intro]\n[Verse 1]\nDon't go (stay)\n\nWe’re here\n[Chorus]\nHold on\n[Instrumental]\n[Chorus]\nHold on\n"}}
        self.assertEqual(ex.clean_lyric_bytes(track).decode("utf-8"),
                         "Don't go (stay)\nWe’re here\n\nHold on\n\nHold on\n")
        self.assertIn(b"[Verse 1]",ex.lyric_bytes(track))

    def test_distribution_preset_is_offline_and_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            t=fixture(repo,"one")
            with patch.object(ex,"retained",return_value=t):
                args=(repo,"one",["one"],URL)
                self.assertEqual(ex.launch(*args,preset="distribution",confirm=True,
                                 timing_reader=lambda *a:self.fail("native read")),0)
                root=repo/"results/exports/songs/one--one"
                manifest=nd.read(root/"release.json")
                self.assertEqual(manifest["tracks"][0]["timing"]["status"],"not_requested")
                self.assertEqual(manifest["status"],"complete")
                self.assertEqual((root/"one.clean.txt").read_bytes(),b"One two\nThree four\n")
                self.assertEqual((root/"one.txt").read_bytes(),ex.lyric_bytes(t))
                self.assertFalse((root/"one.lrc").exists())
                self.assertFalse((root/"one.srt").exists())
                self.assertEqual(ex.launch(*args,preset="distribution",confirm=True,
                                 timing_reader=lambda *a:self.fail("repeat read")),0)
                with self.assertRaises(ValueError):
                    ex.launch(*args,preset="production",confirm=True)

    def test_video_preset_preserves_native_lrc_and_derives_line_onsets(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            t=fixture(repo,"one")
            raw="\ufeff[ti:One]\r\n[ar:Artist]\r\n[offset:0]\r\n"+LRC.replace("\n","\r\n")
            with patch.object(ex,"retained",return_value=t):
                self.assertEqual(ex.launch(repo,"video",["one"],URL,preset="video",confirm=True,timing_reader=lambda *a:raw),0)
                root=repo/"results/exports/songs/one--video"
                self.assertEqual((root/"one.lrc").read_bytes(),raw.encode("utf-8"))
                self.assertEqual((root/"one.line.lrc").read_bytes(),b"[00:01.00]One two\n[00:03.25]Three four\n")
                timing=nd.read(root/"release.json")["tracks"][0]["timing"]
                self.assertEqual((timing["lyric_line_count"],timing["enhanced_line_count"]),(2,1))
                self.assertFalse(timing["acoustic_timing_verified"])
                before={p:nd._sha(p) for p in root.rglob("*") if p.is_file()}
                updated=raw.replace("[00:03.25]","[00:03.40]")
                self.assertEqual(ex.launch(repo,"video",["one"],URL,preset="video",snapshot="v2",confirm=True,timing_reader=lambda *a:updated),0)
                revision=repo/"results/exports/revisions/video/v2"
                self.assertIn(b"[00:03.40]",(revision/"one.line.lrc").read_bytes())
                self.assertEqual(before,{p:nd._sha(p) for p in root.rglob("*") if p.is_file()})
                self.assertEqual(ex.launch(repo,"offset",["one"],URL,preset="video",confirm=True,timing_reader=lambda *a:raw.replace("[offset:0]","[offset:500]")),2)
                self.assertFalse((repo/"results/exports/songs/one--offset/one.srt").exists())

    def test_native_line_fallback_does_not_invent_onsets(self):
        raw="[00:01.00]<00:01.50>One <00:01.20>two\n[00:03.25]Three four"
        lrc,srt,issue=ex.native_timing_assets(raw,LYRICS,5.5)
        self.assertEqual(lrc,"[00:01.00]One two\n[00:03.25]Three four\n")
        self.assertIn("Malformed or unordered",issue)
        self.assertIn("00:00:01,000 --> 00:00:03,250",srt)
        for bad in (raw.replace("Three four","Wrong"),raw.replace("[00:03.25]","[00:00.25]"),raw.replace("<00:01.20>","<bad>")):
            with self.assertRaises(ValueError):
                ex.native_timing_assets(bad,LYRICS,5.5)
        with self.assertRaises(ValueError):
            ex.timed_text(raw,LYRICS,5.5)
