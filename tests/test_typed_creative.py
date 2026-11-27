"""Explicit typed music policy, frozen exact lyrics and backward compatibility."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_cover_art import make_song, MusicProvider
from test_release_export import URL
from yue2_music_director import autonomous as au, typed_creative as tc, composer_typed as ct
from yue2_music_director import creative_core as cc, native_draft as nd, artist_run as ar
from yue2_music_director import retained_source as rs, release_export as ex
from yue2_music_director.creative_provider import role_schema
from yue2_music_director import composer

WORDS="[Verse]\r\nPrivate words  \r\n"
SPEC={"schema":tc.SPEC_SCHEMA,"opening":"direct_vocal","vocal":"female",
      "narrator":"first person","lyrics":WORDS,
      "section_purposes":{"verse#1":"Introduce the departure"},
      "score_constraints":{"section_order":{"mode":"must","value":["verse#1"]}}}


class Provider(MusicProvider):
    def __init__(self,job,*,conflict=False,wrong_words=False,stop=False):
        super().__init__(job)
        self.calls=[]
        self.conflict=conflict
        self.wrong_words=wrong_words
        self.stop=stop
    def complete(self,role,prompt,data):
        self.calls.append(role)
        result=super().complete(role,prompt,data)
        if role=="composer" and self.conflict:
            result["direction"]["vocal"]="male"
        if role=="lyricist" and self.wrong_words:
            result["lyrics"]="[Chorus]\nWrong section"
        if role=="reviewer" and self.stop:
            result["decision"]="stop"
        return result


class TypedCreativeTests(unittest.TestCase):
    def test_exact_operator_lyrics_and_supported_native_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            p=Provider("one")
            with patch.object(au,"produce",return_value=0) as produce:
                args=(repo,"one","A departure","en",90,URL)
                self.assertEqual(au.launch(*args,typed_spec=SPEC,provider_factory=lambda:p),0)
                self.assertEqual(p.calls,[])
                self.assertEqual(au.launch(*args,typed_spec=SPEC,confirm=True,provider_factory=lambda:p),0)
                self.assertEqual(p.calls,["composer","reviewer"])
                root=repo/"results/autonomous/one"
                brief,intent=produce.call_args.args[3:5]
                self.assertEqual(brief["lyrics"],WORDS)
                self.assertEqual(intent["direction"]["vocal"],"female")
                self.assertEqual(intent["direction"]["narrator"],"first person")
                self.assertEqual(intent["section_purposes"],SPEC["section_purposes"])
                self.assertEqual(intent["constraints"]["section_order"],SPEC["score_constraints"]["section_order"])
                self.assertEqual(set(ar.plan_request(brief,intent)),{"style","lyrics","cot","lm_seed","lm_batch_size","harmony"})
                self.assertEqual(ar.plan_request(brief,intent)["lyrics"],WORDS)
                self.assertEqual(nd.request_for(brief)["lyrics"],WORDS)
                self.assertFalse((root/"lyricist.attempt.json").exists())
                self.assertEqual(nd.read(root/"operator-lyrics.json")["provider_calls"],0)
                before={f:nd._sha(f) for f in root.iterdir() if f.is_file()}
                self.assertEqual(au.launch(*args,typed_spec=SPEC,confirm=True,provider_factory=lambda:p),0)
                self.assertEqual(p.calls,["composer","reviewer"])
                self.assertEqual(before,{f:nd._sha(f) for f in before})
                with self.assertRaises(ValueError):
                    au.launch(*args,typed_spec={**SPEC,"lyrics":WORDS+"more"},confirm=True,provider_factory=lambda:p)
                self.assertEqual(p.calls,["composer","reviewer"])

    def test_explicit_conflicts_stop_before_provider_or_success_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            args=(repo,"one","A departure","en",90,URL)
            with self.assertRaisesRegex(ValueError,"opening conflicts"):
                au.launch(*args,typed_spec={**SPEC,"opening":"instrumental_intro"},confirm=True,
                          provider_factory=lambda:self.fail("provider called"))
            p=Provider("one",conflict=True,stop=True)
            with patch.object(au,"produce",side_effect=AssertionError("native called")):
                with self.assertRaisesRegex(ValueError,"explicit vocal"):
                    au.launch(*args,typed_spec=SPEC,confirm=True,provider_factory=lambda:p)
                root=repo/"results/autonomous/one"
                self.assertFalse((root/"composer.json").exists())
                reject=(root/"composer.rejected.json").read_bytes()
                self.assertEqual(p.calls,["composer"])
                p.conflict=False
                self.assertEqual(au.launch(*args,typed_spec=SPEC,confirm=True,retry_role="composer",
                                            provider_factory=lambda:p),2)
                self.assertEqual(p.calls,["composer","composer","reviewer"])
                self.assertEqual((root/"composer.rejected.json").read_bytes(),reject)

    def test_generated_lyrics_must_match_typed_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            p=Provider("one",wrong_words=True,stop=True)
            spec={**SPEC,"lyrics":None}
            args=(repo,"one","A departure","en",90,URL)
            with patch.object(au,"produce",side_effect=AssertionError("native called")):
                with self.assertRaisesRegex(ValueError,"section plan"):
                    au.launch(*args,typed_spec=spec,confirm=True,provider_factory=lambda:p)
                root=repo/"results/autonomous/one"
                self.assertTrue((root/"composer.json").is_file())
                self.assertFalse((root/"lyricist.json").exists())
                p.wrong_words=False
                self.assertEqual(au.launch(*args,typed_spec=spec,confirm=True,retry_role="lyricist",
                                            provider_factory=lambda:p),2)
                self.assertEqual(p.calls,["composer","lyricist","lyricist","reviewer"])

    def test_completed_typed_continuation_read_and_exact_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            parent=make_song(repo,"one",True,typed_spec=SPEC)
            before={p:nd._sha(p) for p in parent.rglob("*") if p.is_file()}
            with patch.object(cc,"prepare",side_effect=AssertionError("provider replay")), \
                 patch.object(nd,"request_for",side_effect=AssertionError("current builder replay")):
                source=rs.load(repo,"one")
                self.assertEqual(source["brief"]["lyrics"],WORDS)
                self.assertEqual(ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:None),2)
            output=repo/"results/exports/songs/one--release/one.txt"
            self.assertEqual(output.read_bytes(),WORDS.encode("utf-8"))
            self.assertEqual(before,{p:nd._sha(p) for p in before})
            receipt=nd.read(parent/"operator-lyrics.json")
            receipt["result"]["lyrics"]="changed"
            nd.atomic_write(parent/"operator-lyrics.json",receipt)
            with self.assertRaises(ValueError):
                rs.load(repo,"one")

    def test_typed_wire_schema_is_opt_in_and_literal_style_conflict(self):
        self.assertEqual(role_schema("composer"),composer.SCHEMA)
        self.assertEqual(role_schema("composer",{"typed_requirements":SPEC}),ct.SCHEMA)
        self.assertNotIn("direction",composer.SCHEMA["properties"])
        p=Provider("one")
        music=p.complete("composer",ct.PROMPT,{"typed_requirements":SPEC})
        music["style"]="English folk, male and female vocals"
        with self.assertRaisesRegex(ValueError,"Conflicting literal"):
            tc.check_composer(music,tc.validate_spec(SPEC))

    def test_impossible_exact_style_is_rejected_locally(self):
        for style in ("English folk with acoustic guitar","English folk male female vocals"):
            with self.subTest(style=style),self.assertRaisesRegex(ValueError,"compatible literal vocal cue"):
                tc.validate_spec({**SPEC,"style":style,"vocal":None})



class ArtistProfileProductionTests(unittest.TestCase):
    def test_profile_selected_on_new_job_and_frozen_on_cli_resume(self):
        import sys
        from yue2_music_director import artist_memory as am
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            profile={"schema":am.PROFILE,"defaults":{"vocal":"female","opening":"direct_vocal"},
                     "confirmed_preferences":["private confirmed note"],
                     "inferred_observations":["private inference"],"provenance":"operator"}
            first=am.save(repo,"fixture",profile,0,confirm=True)
            override=repo/"override.json"
            nd.atomic_write(override,{"schema":tc.SPEC_SCHEMA,"lyrics":WORDS,"narrator":"first person",
                                      "section_purposes":SPEC["section_purposes"]})
            p=Provider("one")
            common=["music","--repo",str(repo),"--url",URL,"--job","one"]
            args=common+["--request","A departure","--duration","90","--artist-profile","fixture",
                         "--creative-spec",str(override)]
            with patch.object(au.TextProvider,"for_repo",return_value=p),patch.object(au,"produce",return_value=0):
                with patch.object(sys,"argv",args):
                    self.assertEqual(au.main(),0)
                self.assertFalse((repo/"results").exists())
                self.assertEqual(p.calls,[])
                with patch.object(sys,"argv",args+["--confirm-run"]):
                    self.assertEqual(au.main(),0)
                self.assertEqual(p.calls,["composer","reviewer"])
                root=repo/"results/autonomous/one"
                saved=nd.read(root/"job.json")
                self.assertEqual(saved["artist_profile"],{"artist":"fixture","revision":1,"profile_sha256":first["sha256"]})
                self.assertEqual(saved["creative_spec"]["lyrics"],WORDS)
                self.assertEqual(saved["creative_spec"]["vocal"],"female")
                self.assertNotIn("private confirmed note",str(saved))
                self.assertNotIn("private inference",str(saved))
                am.save(repo,"fixture",{**profile,"defaults":{"vocal":"male"}},1,confirm=True)
                with patch.object(sys,"argv",common+["--confirm-run"]),patch.object(am,"compile_spec",side_effect=AssertionError("profile reread")):
                    self.assertEqual(au.main(),0)
                self.assertEqual(nd.read(root/"job.json"),saved)
                self.assertEqual(p.calls,["composer","reviewer"])
                with patch.object(sys,"argv",args+["--confirm-run"]):
                    self.assertEqual(au.main(),2)
                self.assertEqual(p.calls,["composer","reviewer"])
