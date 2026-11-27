import tempfile
import unittest
from pathlib import Path
from yue2_music_director import artist_memory as am


class ArtistMemoryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo=Path(tmp.name)
        self.profile={"schema":am.PROFILE,"defaults":{"vocal":"female","opening":"direct_vocal",
                        "score_constraints":{"tempo_bpm":{"mode":"prefer","value":90}}},
                      "confirmed_preferences":["Warm acoustic palette"],
                      "inferred_observations":["Maybe prefers long intros"],
                      "provenance":"Synthetic operator entry"}

    def test_explicit_revision_and_conflict(self):
        self.assertEqual(am.history(self.repo,"artist"),[])
        with self.assertRaises(ValueError):
            am.save(self.repo,"artist",self.profile,0)
        first=am.save(self.repo,"artist",self.profile,0,confirm=True)
        second=am.save(self.repo,"artist",{**self.profile,"defaults":{"vocal":"male"}},1,confirm=True)
        self.assertEqual(second["record"]["previous_sha256"],first["sha256"])
        with self.assertRaises(ValueError):
            am.save(self.repo,"artist",self.profile,1,confirm=True)
        self.assertEqual(am.compile_spec(self.repo,"artist",revision=1)["spec"]["vocal"],"female")
        self.assertEqual(am.compile_spec(self.repo,"artist")["spec"]["vocal"],"male")

    def test_explicit_override_and_notes_not_applied(self):
        am.save(self.repo,"artist",self.profile,0,confirm=True)
        value=am.compile_spec(self.repo,"artist",overrides={"schema":"creative-spec-v1",
                   "vocal":"male","opening":None,"score_constraints":{}})
        self.assertEqual(value["spec"]["vocal"],"male")
        self.assertIsNone(value["spec"]["opening"])
        self.assertEqual(value["spec"]["score_constraints"],{})
        self.assertNotIn("inferred_observations",value["spec"])
        self.assertNotIn("confirmed_preferences",value["spec"])
        self.assertFalse(value["execution_authorized"])
        with self.assertRaises(ValueError):
            am.export_spec(self.repo,value)
        path=am.export_spec(self.repo,value,confirm=True)
        self.assertEqual(am.export_spec(self.repo,value,confirm=True),path)
        self.assertEqual(am._read(path)[0],value["spec"])
        path.write_text("{}")
        with self.assertRaises(ValueError):
            am.export_spec(self.repo,value,confirm=True)

    def test_profile_validation_and_tamper(self):
        for artist in ("../x","CON","con","artist/one","x."):
            with self.assertRaises(ValueError):
                am.history(self.repo,artist)
        with self.assertRaises(ValueError):
            am.validate({**self.profile,"defaults":{"lyrics":"private lyrics"}})
        am.save(self.repo,"artist",self.profile,0,confirm=True)
        am.save(self.repo,"artist",self.profile,1,confirm=True)
        path=self.repo/"local/artist-memory/artist/000001.json"
        path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaises(ValueError):
            am.history(self.repo,"artist")

    def test_exact_lyrics_override_preserved_and_conflict(self):
        am.save(self.repo,"artist",self.profile,0,confirm=True)
        raw="[Verse]\\r\\nA line".replace("\\r\\n","\r\n")
        result=am.compile_spec(self.repo,"artist",overrides={"schema":"creative-spec-v1","lyrics":raw})
        self.assertEqual(result["spec"]["lyrics"],raw)
        with self.assertRaises(ValueError):
            am.compile_spec(self.repo,"artist",overrides={"schema":"creative-spec-v1",
                            "lyrics":"[Intro]\n\n[Verse]\nA line"})
