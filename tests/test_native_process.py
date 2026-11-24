import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from yue2_music_director.native_process import effect_request, preflight, preview, _verify_run
from yue2_music_director.native_recognition import BUSY_KEYS


class NativeProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"original.flac"
        self.source.write_bytes(b"source")
        self.request=effect_request("test-song","naturalize",0.2)
        self.client=Mock()
        self.client.tools.return_value=[
            {"name":n,"inputSchema":{"properties":{"song_id":{},"naturalize":{},"lifter":{}}}}
            for n in ("studio_status","library_song_files","processing_get","processing_start")]
        self.run={"id":"test-run","song_id":"test-song","stages":["naturalize"],
                  "request":{"naturalize":self.request["naturalize"]},"done":True,
                  "preview_ready":True,"error":None}

    def response(self,name,args):
        if name=="studio_status":
            return {k:None for k in BUSY_KEYS}
        if name=="library_song_files":
            return {"audio":str(self.source.resolve())}
        if name=="processing_get":
            return {"run":None}
        raise AssertionError(name)

    def test_preflight_no_mutation(self):
        self.client.call.side_effect=self.response
        self.assertEqual(preflight(self.client,self.source.resolve(),self.request).name,"processing")
        self.assertEqual([c.args[0] for c in self.client.call.call_args_list],
                         ["processing_get","studio_status","library_song_files"])

    def test_existing_preview_blocks(self):
        self.client.call.return_value={"run":self.run}
        with self.assertRaisesRegex(ValueError,"existing processing run"):
            preflight(self.client,self.source,self.request)
        self.assertEqual(self.client.call.call_count,1)

    def test_unrelated_workspace_blocks(self):
        self.client.call.side_effect=self.response
        work=self.root/"processing"
        work.mkdir()
        (work/"other.flac").write_bytes(b"unrelated")
        with self.assertRaisesRegex(ValueError,"not empty"):
            preflight(self.client,self.source,self.request)

    def test_request_constraints(self):
        with self.assertRaises(ValueError):
            effect_request("x","normalize",0.2)
        with self.assertRaises(ValueError):
            effect_request("x","naturalize",1)
        self.assertEqual(_verify_run(self.run,self.request),"test-run")
        with self.assertRaises(ValueError):
            _verify_run(self.run,self.request,"other-run")
        self.run["request"]["region"]={"start_seconds":0,"end_seconds":1}
        with self.assertRaises(ValueError):
            _verify_run(self.run,self.request)

    @patch("yue2_music_director.native_process.Client")
    @patch("yue2_music_director.native_process.compare")
    @patch("yue2_music_director.native_process.shutil.which",return_value="ffmpeg")
    def test_capture_single_preview(self,which,compare,client):
        client.return_value.connect.return_value=self.client
        count=[0]
        def response(name,args):
            if name=="processing_start":
                count[0]+=1
                work=self.root/"processing"
                work.mkdir()
                (work/"preview.flac").write_bytes(b"preview")
                return {"started":True}
            if name=="processing_get" and count[0]:
                return {"run":self.run}
            return self.response(name,args)
        self.client.call.side_effect=response
        arm={"duration_seconds":5.0,"true_peak_dbtp":-1.5,"integrated_lufs":-16.0}
        compare.return_value={"arms":{"A":arm,"B":arm}}
        report=preview(self.source,"test-song","naturalize",0.2,self.root/"out",
                       "http://127.0.0.1:1234/mcp",confirm=True)
        self.assertEqual(report["status"],"preview_acoustic_pass")
        self.assertEqual(count[0],1)
        self.assertFalse(report["automatic_acceptance"])
        self.assertEqual((self.root/"out"/"preview.flac").read_bytes(),b"preview")
        self.assertEqual(self.source.read_bytes(),b"source")
        self.assertTrue((self.root/"processing"/"preview.flac").exists())
        self.assertNotIn("processing_keep",[c.args[0] for c in self.client.call.call_args_list])
        self.assertNotIn("processing_discard",[c.args[0] for c in self.client.call.call_args_list])
        with self.assertRaises(ValueError):
            preview(self.source,"test-song","naturalize",0.2,self.root/"out",
                    "http://127.0.0.1:1234/mcp",confirm=True)
