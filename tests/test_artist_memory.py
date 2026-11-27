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


    def test_named_artist_preserves_unicode_and_internal_identity(self):
        name="Écho du Matin 星"
        first=am.save_named(self.repo,name,self.profile,0,confirm=True)
        aid=first["record"]["artist"]
        self.assertTrue(aid.startswith("artist-"))
        self.assertEqual(first["record"]["profile"]["display_name"],name)
        compiled=am.compile_spec(self.repo,"E\u0301cho du Matin 星")
        self.assertEqual(compiled["artist"],aid)
        self.assertEqual(compiled["display_name"],name)
        self.assertNotIn("display_name",compiled["spec"])
        renamed={**first["record"]["profile"],"display_name":"Écho Nouveau"}
        am.save_named(self.repo,aid,renamed,1,confirm=True)
        self.assertEqual(am.compile_spec(self.repo,"Écho Nouveau",revision=1)["display_name"],name)
        self.assertEqual(am.compile_spec(self.repo,aid)["display_name"],"Écho Nouveau")

    def test_ambiguous_name_never_selects_arbitrary_profile(self):
        named={**self.profile,"schema":am.NAMED_PROFILE,"display_name":"Same Name"}
        am.save(self.repo,"one",named,0,confirm=True)
        am.save(self.repo,"two",named,0,confirm=True)
        with self.assertRaisesRegex(ValueError,"Ambiguous"):
            am.compile_spec(self.repo,"same name")
        self.assertEqual(am.compile_spec(self.repo,"one")["artist"],"one")

    def test_save_by_name_does_not_use_display_name_as_path(self):
        name="A / B: 星"
        row=am.save_named(self.repo,name,self.profile,0,confirm=True)
        self.assertEqual(am.compile_spec(self.repo,name)["display_name"],name)
        self.assertEqual(len(list((self.repo/"local/artist-memory").iterdir())),1)
        with self.assertRaises(ValueError):
            am.save_named(self.repo,name,self.profile,0,confirm=True)
        self.assertEqual(len(am.history(self.repo,row["record"]["artist"])),1)
