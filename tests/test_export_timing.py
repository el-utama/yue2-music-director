"""Offline contract tests for the actual read-only export timing adapter."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yue2_music_director import export_timing as et, release_export as ex, native_draft as nd
from yue2_music_director.mcp import MCPError

URL="http://127.0.0.1:8791/mcp"
LYRICS="[Verse]\nOne two\nThree four"
LRC="[00:01.00]<00:01.00>One <00:01.50>two\r\n[00:03.25]Three four"


class ExportTimingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)
        self.source=self.repo/"original.flac"
        self.other=self.repo/"selected.flac"
        self.source.write_bytes(b"retained synthetic audio")
        self.other.write_bytes(b"different synthetic audio")
        self.track={"job":"one","audio":self.source,
                    "brief":{"title":"one","lyrics":LYRICS},
                    "report":{"song_id":"song","job_id":"native-job","acoustic":{"duration_seconds":5.5}},
                    "result":{"audio_sha256":nd._sha(self.source),"status":"review_required"},
                    "evidence":{"job":"one","result_sha256":"fixture"}}
        self.song={"id":"song","metadata":{"job_id":"native-job","lrc":LRC},
                   "generation_settings":{"lyrics":LYRICS}}
        factory=self.enterContext(patch.object(et,"Client"))
        self.client=factory.return_value.connect.return_value
        self.client.call.return_value={"audio":str(self.source)}
        self.native=self.enterContext(patch.object(et,"native_song_read",side_effect=lambda *a:copy.deepcopy(self.song)))

    def test_stable_source_and_verbatim_lrc(self):
        self.assertEqual(et.read_timing(self.track,URL),LRC)
        self.assertEqual(self.native.call_count,2)
        self.assertEqual([call.args for call in self.client.call.call_args_list],
                         [("library_song_files",{"song_id":"song"})]*2)

    def test_active_audio_switched_before_or_after_read(self):
        for paths in ([self.other],[self.source,self.other]):
            with self.subTest(paths=paths):
                self.client.call.side_effect=[{"audio":str(p)} for p in paths]
                self.native.reset_mock()
                with self.assertRaisesRegex(ValueError,"Library audio identity"):
                    et.read_timing(self.track,URL)
                self.assertEqual(self.native.call_count,0 if paths[0]==self.other else 2)

    def test_changed_timing_or_other_snapshot_metadata_rejected(self):
        for changed in ("lrc","version"):
            with self.subTest(changed=changed):
                after=copy.deepcopy(self.song)
                if changed=="lrc":
                    after["metadata"]["lrc"]=LRC.replace("03.25","03.50")
                else:
                    after["metadata"]["version"]="changed"
                self.native.side_effect=[self.song,after]
                with self.assertRaisesRegex(ValueError,"metadata changed"):
                    et.read_timing(self.track,URL)

    def test_missing_or_malformed_native_fields_and_transport(self):
        for bad in (None,{},{"id":"song","metadata":[]},
                    {**self.song,"generation_settings":{}},
                    {**self.song,"metadata":{"job_id":"different","lrc":LRC}},
                    {**self.song,"metadata":{"job_id":"native-job","lrc":123}}):
            with self.subTest(bad=bad):
                self.native.side_effect=None
                self.native.return_value=bad
                with self.assertRaises(ValueError):
                    et.read_timing(self.track,URL)
        for failure in (TimeoutError("timeout"),MCPError("offline"),TypeError("malformed")):
            self.native.side_effect=failure
            with self.assertRaisesRegex(ValueError,"Native timing read unavailable"):
                et.read_timing(self.track,URL)

    def test_source_hash_mismatch_prevents_native_read(self):
        self.source.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"source audio hash"):
            et.read_timing(self.track,URL)
        self.native.assert_not_called()
        self.client.call.assert_not_called()

    def test_source_mutation_during_read_aborts_export(self):
        def mutate(*args):
            self.source.write_bytes(b"changed")
            return copy.deepcopy(self.song)
        self.native.side_effect=mutate
        with patch.object(ex,"retained",return_value=self.track):
            with self.assertRaisesRegex(ValueError,"Source audio changed"):
                ex.launch(self.repo,"one",["one"],URL,confirm=True)
        self.assertFalse((self.repo/"results/exports/songs/one--one").exists())

    def test_real_adapter_complete_and_partial_export(self):
        with patch.object(ex,"retained",return_value=self.track):
            self.assertEqual(ex.launch(self.repo,"one",["one"],URL,confirm=True),0)
            root=self.repo/"results/exports/songs/one--one"
            self.assertEqual((root/"one.lrc").read_bytes(),LRC.encode("utf-8"))
            self.assertEqual((root/"one.flac").read_bytes(),self.source.read_bytes())
            timing=nd.read(root/"release.json")["tracks"][0]["timing"]
            self.assertEqual(timing["source_lrc_sha256"],nd.digest(LRC.encode("utf-8")))
            self.assertFalse(timing["karaoke_provenance_verified"])
            self.assertFalse(timing["acoustic_timing_verified"])
            self.native.reset_mock()
            self.native.side_effect=TimeoutError("offline")
            self.assertEqual(ex.launch(self.repo,"one",["one"],URL,confirm=True),0)
            self.native.assert_not_called()
            self.assertEqual(ex.launch(self.repo,"partial",["one"],URL,confirm=True),2)
            partial=self.repo/"results/exports/songs/one--partial"
            self.assertTrue((partial/"one.flac").is_file())
            self.assertTrue((partial/"one.txt").is_file())
            self.assertFalse((partial/"one.lrc").exists())
            self.assertFalse((partial/"one.srt").exists())

    def test_missing_and_malformed_lrc_are_partial(self):
        with patch.object(ex,"retained",return_value=self.track):
            for release,lrc in (("missing",None),("malformed","not LRC")):
                self.song["metadata"]["lrc"]=lrc
                self.assertEqual(ex.launch(self.repo,release,["one"],URL,confirm=True),2)
                root=self.repo/"results/exports/songs"/("one--"+release)
                self.assertTrue((root/"one.flac").is_file())
                self.assertFalse((root/"one.lrc").exists())
                self.assertFalse((root/"one.srt").exists())

    def test_timed_output_write_failure_is_not_partial_success(self):
        write=Path.write_bytes
        def fail_srt(path,data):
            if path.suffix==".srt":
                raise OSError("simulated disk error")
            return write(path,data)
        with patch.object(ex,"retained",return_value=self.track),patch.object(Path,"write_bytes",fail_srt):
            with self.assertRaisesRegex(OSError,"disk error"):
                ex.launch(self.repo,"one",["one"],URL,confirm=True)
        self.assertFalse((self.repo/"results/exports/songs/one--one").exists())
        self.assertFalse(list((self.repo/"results/exports/songs").glob(".export-*")))
