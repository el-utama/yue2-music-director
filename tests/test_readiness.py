import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from yue2_music_director import readiness as rd, artist_run as ar, native_draft as nd
from yue2_music_director.creative_provider import TextProvider, ROLES


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.provider=TextProvider("https://example.invalid/v1/chat/completions","private-secret",
                                   dict.fromkeys(ROLES,"fixture"))
        self.client=Mock()
        self.client.connect.return_value=self.client

    def test_preflight_read_only_and_redacted(self):
        with patch.object(rd,"_windows_host",return_value=True),patch.object(rd.shutil,"which",return_value="fixture"), \
             patch.object(ar,"_preflight") as preflight,patch.object(self.provider,"complete") as complete:
            report=rd.inspect(self.root,"http://127.0.0.1:8791/mcp",client_factory=lambda *a,**k:self.client,
                              provider_factory=lambda repo:self.provider)
        self.assertEqual(report["status"],"preflight_pass")
        self.assertEqual(report["checks"]["moss_files"]["status"],"not_checked")
        self.assertFalse(report["execution_authorized"])
        self.assertNotIn("private-secret",json.dumps(report))
        self.assertFalse(preflight.call_args.kwargs["wait"])
        complete.assert_not_called()
        self.client.call.assert_not_called()

    def test_marker_blocks_without_native_calls(self):
        path=self.root/rd.LOCKS["autonomous"]
        path.parent.mkdir(parents=True)
        path.write_text("untouched")
        with patch.object(rd,"_windows_host",return_value=True),patch.object(rd.shutil,"which",return_value="fixture"), \
             patch.object(ar,"_preflight") as preflight:
            report=rd.inspect(self.root,"unused",provider_factory=lambda repo:self.provider)
        self.assertEqual(report["status"],"blocked")
        self.assertEqual(report["checks"]["native_reference"]["status"],"not_checked")
        preflight.assert_not_called()
        self.assertEqual(path.read_text(),"untouched")

    def test_native_error_redacted_and_moss_block(self):
        with patch.object(rd,"_windows_host",return_value=True),patch.object(rd.shutil,"which",return_value="fixture"), \
             patch.object(ar,"_preflight",side_effect=ValueError("secret response")), \
             patch.object(rd.audio_critic,"inventory_media",return_value={"ready":False}):
            report=rd.inspect(self.root,"http://127.0.0.1:8791/mcp",media_dir=self.root/"media",
                              client_factory=lambda *a,**k:self.client,provider_factory=lambda repo:self.provider)
        self.assertEqual(report["status"],"blocked")
        self.assertEqual(report["checks"]["moss_files"]["status"],"blocked")
        self.assertNotIn("secret response",json.dumps(report))

    def test_shared_native_preflight_does_not_wait_or_submit(self):
        brief=rd.BRIEF
        request=ar.plan_request(brief,{"follow_lyrics":True})
        schemas={name:{"properties":{}}
                 for name in ("score_compose","score_job_get","score_to_midi","song_create","song_job_get",
                              "studio_wait","library_song_files","studio_status","song_defaults",
                              "studio_capabilities","models_status","engine_options_get")}
        for name,payload in (("score_compose",request),("song_create",{**nd.request_for(brief),"abc":""}),
                             ("score_job_get",{"job_id":""}),("score_to_midi",{"abc":""})):
            schemas[name]["properties"]=dict.fromkeys(payload,{})
        schemas["score_compose"]["properties"]["harmony"]={"properties":{"follow_lyrics":{}}}
        self.client.tools.return_value=[{"name":name,"inputSchema":schema} for name,schema in schemas.items()]
        self.client.call.return_value={"fixture":True}
        with patch.object(ar.shutil,"which",return_value="fixture"),patch.object(nd,"recognition_preflight"), \
             patch.object(nd,"reference_configuration",return_value={}),patch.object(ar,"assert_idle",return_value={}), \
             patch.object(ar,"wait_for_idle") as wait:
            ar._preflight(self.client,brief,request,wait=False)
        wait.assert_not_called()
        self.assertEqual([c.args[0] for c in self.client.call.call_args_list],["song_defaults","studio_capabilities"])
