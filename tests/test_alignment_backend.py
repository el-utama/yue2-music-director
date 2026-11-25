import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director.alignment_backend import endpoint,preflight,MODEL


class BackendTests(unittest.TestCase):
    def test_local_only(self):
        self.assertEqual(endpoint("http://127.0.0.1:8765"),("127.0.0.1",8765))
        for url in ("https://example.org:8765","http://192.168.0.1:8765",
                    "http://127.0.0.1:8765/align","http://user@localhost:8765",
                    "http://localhost:8765/?x=1"):
            with self.assertRaises(ValueError):
                endpoint(url)

    @patch("yue2_music_director.alignment_backend.get_json")
    def test_discovery(self,get):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def responses(installed,language="en"):
                return [{"version":"test"}, {"task":"align","languages":[
                    {"code":language,"models":[{"id":MODEL,"engine":"hubertfa","installed":installed}]}]}]
            for i,(installed,lang,status) in enumerate((
                    (False,"en","model_installation_required"),
                    (True,"en","installed_models_require_validation"),
                    (True,"ja","language_model_unavailable"))):
                get.reset_mock()
                get.side_effect=responses(installed,lang)
                result=preflight("en",root/f"{i}.json")
                self.assertEqual(result["status"],status)
                self.assertFalse(result["correction_allowed"])
                self.assertEqual(result["downloads_requested"],0)
                self.assertEqual([c.args[2] for c in get.call_args_list],
                                 ["/health","/languages?task=align"])

    @patch("yue2_music_director.alignment_backend.get_json",side_effect=ConnectionRefusedError("offline"))
    def test_unavailable(self,get):
        with tempfile.TemporaryDirectory() as tmp:
            result=preflight("id",Path(tmp)/"result.json")
            self.assertEqual(result["status"],"backend_unavailable")
            self.assertIsNone(result["preferred_research_model"])
            self.assertEqual(result["alignment_calls"],0)
