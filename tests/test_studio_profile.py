import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yue2_music_director.mcp import MCPError
from yue2_music_director.studio_profile import READS, capture_profile


class ProfileTests(unittest.TestCase):
    def setup_client(self, factory, missing=()):
        client=factory.return_value.connect.return_value
        client.version="2026-07-28"
        client.tools.return_value=[
            {"name":n,"inputSchema":{"type":"object"}} for n,_ in READS if n not in missing
        ] + [{"name":"song_create","inputSchema":{"type":"object"}}]
        client.call.return_value={"structuredContent":{"private_path":"local-only","private_id":"fixture"}}
        return client

    @patch("yue2_music_director.studio_profile.Client")
    def test_full_read_only_inventory(self,factory):
        client=self.setup_client(factory)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"profile.json"
            result=capture_profile(out,"http://127.0.0.1:1234/mcp")
            self.assertEqual(result["status"],"reads_complete_unverified")
            self.assertEqual(client.call.call_args_list[0].args,("studio_status",{}))
            self.assertEqual([c.args for c in client.call.call_args_list],list(READS))
            self.assertFalse(result["execution_authorized"])
            self.assertFalse(result["compatibility_verified"])
            self.assertNotIn("local-only",json.dumps(result))
            report=json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(report["private"])
            self.assertEqual(report["observations"]["studio_status"]["private_path"],"local-only")
            self.assertIn("song_create",report["tool_input_schemas"])
            with self.assertRaises(ValueError):
                capture_profile(out,"http://127.0.0.1:1234/mcp")
            self.assertEqual(client.call.call_count,len(READS))

    @patch("yue2_music_director.studio_profile.Client")
    def test_partial_no_retry(self,factory):
        client=self.setup_client(factory,("music_pair_status",))
        def response(name,args):
            if name=="lora_list":
                raise MCPError("private error")
            return {"structuredContent":{"ok":True}}
        client.call.side_effect=response
        with tempfile.TemporaryDirectory() as tmp:
            result=capture_profile(Path(tmp)/"profile.json","http://127.0.0.1:1234/mcp")
            self.assertEqual(result["status"],"partial_inventory")
            self.assertEqual(result["missing_reads"],["music_pair_status"])
            self.assertEqual(result["failed_reads"],{"lora_list":"MCPError"})
            self.assertEqual(client.call.call_count,len(READS)-1)
            self.assertNotIn("private error",json.dumps(result))

    @patch("yue2_music_director.studio_profile.Client")
    def test_unknown_server_stops(self,factory):
        client=self.setup_client(factory,("studio_status",))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                capture_profile(Path(tmp)/"profile.json","http://127.0.0.1:1234/mcp")
            client.call.assert_not_called()
