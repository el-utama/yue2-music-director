import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yue2_music_director.music import parse_score, ScoreError
from yue2_music_director.musical_review import review_score
from yue2_music_director.cli import main

HEADER = (
    'X:1\nT:\nM:2/4\nL:1/32\nQ:1/4=60\n'
    'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"\n'
    'V: Ins clef=treble name="Ins Melody" snm="Inst."\nK:Dm\n'
)


def group(label, vocal, ins):
    return (f"% {label}\n" if label else "") + f"V: Vocal\n{vocal}\nV: Ins\n{ins}\n"


# Original synthetic fixture, no private reference material.
ABC = (HEADER + group("intro","Z2|","D16|F16|")
       + group("verse",'"Dm7"^F8-F8-|F8B8|',"Z2|")
       + group("chorus",'"Gm6"^C8c8|"A7"z8A8|',"Z2|")
       + group("final chorus",'"Gm6"^C8c8|"A7"z8A8|"Dm"F8z8|',"Z3|")
       + group("outro","Z|","D8z8|"))
LYRICS = "[Intro]\n(Guitar)\n[Verse]\nOne line\n[Chorus]\nTwo lines\n[Bridge]\nMore words\n[Final Chorus]\nTwo lines\n[Outro]\n(Guitar fade)"


class MusicalReviewTests(unittest.TestCase):
    def test_native_minor_and_ties_and_carry(self):
        score = parse_score(ABC,native=True)
        self.assertEqual(score.counts,{"Vocal":10,"Ins":10})
        notes=[e.pitch for e in score.events if e.voice=="Vocal" and e.kind=="note"]
        self.assertEqual(notes[:4],[66,66,66,70]) # tied accidental survives barline; Bb in Dm
        self.assertEqual(notes[4:6],[61,73]) # letter-wide accidental across octaves
        with self.assertRaises(ScoreError):
            parse_score(ABC) # old major-only policy unchanged

    def test_metrics_and_soft_deviations(self):
        r=review_score(ABC,LYRICS,constraints={"key":{"mode":"prefer","value":"Am"}})
        self.assertEqual(r["status"],"artistic_review_required")
        self.assertFalse(r["hard_violations"])
        self.assertFalse(r["render_authorized"])
        self.assertFalse(r["native_midi_verified"])
        self.assertEqual(r["metrics"]["score_seconds"],20)
        self.assertEqual(r["metrics"]["sections"][1]["vocal"]["attacks"],2)
        self.assertEqual(r["metrics"]["sections"][1]["vocal"]["sounding_fraction"],1)
        self.assertEqual(r["metrics"]["chorus_comparisons"][0]["identical_vocal_bars"],2)
        self.assertEqual(r["metrics"]["chorus_comparisons"][0]["second_bars"],3)
        mismatch=next(x for x in r["soft_flags"] if x["code"]=="notated_sung_sequence_differs")
        self.assertEqual(mismatch["missing"],["bridge#1"])
        self.assertFalse(mismatch["extra"])

    def test_wordless_break_and_outro_in_short_form(self):
        lyrics = "[Verse 1]\nA footstep\n[Chorus]\nOne more\n[Instrumental Break]\n[Outro]"
        score = (HEADER + group("verse", "D16|", "Z|") + group("chorus", "F16|", "Z|")
                 + group("interlude", "Z|", "D16|") + group("outro", "Z|", "F16|"))
        report = review_score(score, lyrics, max_seconds=180)
        self.assertEqual(report["status"], "local_review_ready")
        self.assertEqual(report["metrics"]["sung_sections"], ["verse#1", "chorus#1"])
        vocal_tail = score.rsplit("V: Vocal\nZ|", 1)
        report = review_score("V: Vocal\nD16|".join(vocal_tail), lyrics, max_seconds=180)
        flag = next(f for f in report["soft_flags"] if f["code"] == "notated_sung_sequence_differs")
        self.assertEqual(flag["extra"], ["outro#1"])

    def test_instrumental_intro_preview_preserves_timing_and_checks_next_entry(self):
        from yue2_music_director import artist_run
        from yue2_music_director.retained_plan_review import preview_intro

        constraints = {field: {"mode": "must", "value": "instrumental_intro"}
                       for field in ("opening", "opening_timing")}
        intent = {"schema": "artist-intent-v1", "route": "reviewed_native",
                  "concept": "Departure", "emotional_arc": "Loss to resolve",
                  "performance": "Instrumental opening", "section_purposes": {"intro#1": "Set the tone"},
                  "constraints": constraints, "retain_soft_flags": {}, "follow_lyrics": True,
                  "budget": {"score_jobs": 1, "song_jobs": 1, "recognition_calls": 1}}
        brief = {"lyrics": "[Intro]\n[Verse]\nOne step outside", "duration_seconds": 190}
        for intro, instruments, verse, expected in (
            ('"Dm"z8D8|', "D16|", "E16|", "candidate_available"),
            ("z8D8|", "D16|", "Z2|E16|", "not_eligible"),
            ("z8D8-|", "D16|", "D8E8|", "not_eligible"),
            ("z8D8|", "Z|", "E16|", "not_eligible"),
        ):
            with self.subTest(intro=intro, instruments=instruments, verse=verse):
                verse_bars = 3 if verse.startswith("Z2") else 1
                abc = (HEADER + group("intro", intro, instruments)
                       + group("verse", verse, "Z" + (str(verse_bars) if verse_bars > 1 else "") + "|"))
                review = artist_run.evaluate_plan(abc, brief, intent)["score_review"]
                self.assertEqual(len(review["hard_violations"]), 2, review)
                result = preview_intro(abc, brief, intent, review)
                self.assertEqual(result["status"], expected, result)
                self.assertFalse(result["render_authorized"])
                if expected == "candidate_available":
                    self.assertEqual(result["score_seconds"], 4.0)
                    self.assertEqual(result["vocal_notes_replaced_by_rests"], 1)
                    self.assertEqual(result["opening_evidence"]["first_vocal_onset_seconds"], 2.0)

    def test_mandatory_and_cap(self):
        for kwargs in ({"constraints":{"key":{"mode":"must","value":"Am"}}},
                       {"max_seconds":19.99},
                       {"constraints":{"section_order":{"mode":"must","value":["verse#1"]}}}):
            r=review_score(ABC,LYRICS,**kwargs)
            self.assertEqual(r["status"],"blocked")
            self.assertTrue(r["hard_violations"])
        self.assertFalse(review_score(ABC,LYRICS,max_seconds=20)["hard_violations"])

    def test_unsupported_vs_invalid(self):
        unknown=ABC.replace("F8B8|","F8{a}B8|",1)
        r=review_score(unknown,LYRICS)
        self.assertEqual(r["status"],"unassessable")
        self.assertFalse(r["hard_violations"])
        self.assertIsNone(r["metrics"])
        self.assertTrue(review_score(unknown,LYRICS,max_seconds=30)["hard_violations"])
        for bad in (ABC.replace("F8B8|","F8B4|",1),
                    ABC.replace("F8B8|","Z|",1),
                    ABC.replace("F8B8|","G8B8|",1),
                    ABC.replace("Z2|","Z3|",1),
                    ABC.replace('"Dm7"','"H7"',1),
                    ABC.replace("D16|F16|",'"C"D16|F16|',1)):
            r=review_score(bad,LYRICS)
            self.assertEqual(r["status"],"blocked",r)
            self.assertFalse(r["render_authorized"])

    def test_major_4_4_and_exact_repeated_chorus(self):
        header=HEADER.replace("M:2/4","M:4/4").replace("L:1/32","L:1/16").replace("K:Dm","K:C")
        abc=header+group("chorus",'"C"c8z8|',"Z|")+group("chorus",'"C"c8z8|',"Z|")
        r=review_score(abc,"[Chorus]\nLine\n[Chorus]\nLine")
        self.assertEqual(r["metrics"]["score_seconds"],8)
        self.assertEqual(r["metrics"]["vocal"]["sounding_fraction"],.5)
        self.assertEqual(r["metrics"]["chorus_comparisons"][0]["identical_vocal_bars"],1)
        self.assertIn("identical_repeated_chorus",[x["code"] for x in r["soft_flags"]])

    def test_cli_offline_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, patch("yue2_music_director.cli.Client") as client:
            root=Path(tmp)
            abc=root/"score.abc"; abc.write_text(ABC,encoding="utf-8")
            lyrics=root/"lyrics.txt"; lyrics.write_text(LYRICS,encoding="utf-8")
            out=root/"report.json"
            argv=["score-review",str(abc),"--lyrics",str(lyrics),"--out",str(out)]
            self.assertEqual(main(argv),0)
            self.assertEqual(json.loads(out.read_text())["schema"],"native-musical-review-v1")
            self.assertEqual(main(argv),2)
            self.assertEqual(abc.read_text(),ABC)
            client.assert_not_called()

class VariableGridTests(unittest.TestCase):
    def make_score(self):
        header=HEADER.replace("M:2/4","M:4/4").replace("L:1/32","L:1/16").replace("K:Dm","K:C")
        return header+group("verse",'"C"C8D8|',"Z|")+(
            "% chorus\nV: Vocal\nM:3/4\nK:G\n\"G\"F4[K:C]F8|\n"
            "V: Ins\nM:3/4\nK:G\nz4[K:C]z8|\n")

    def test_variable_meter_and_key_timing(self):
        abc=self.make_score()
        report=review_score(abc,"[Verse]\nOne\n[Chorus]\nTwo",max_seconds=7)
        self.assertEqual(report["status"],"local_review_ready",report)
        self.assertEqual(report["metrics"]["score_seconds"],7)
        self.assertEqual(report["metrics"]["sections"][1]["start_seconds"],4)
        self.assertEqual(report["metrics"]["sections"][1]["duration_seconds"],3)
        self.assertEqual([e.pitch for e in parse_score(abc,native=True).events if e.kind=="note"][-2:],[66,65])
        self.assertEqual(review_score(abc,"[Verse]\nOne\n[Chorus]\nTwo",max_seconds=6)["hard_violations"][0]["code"],"score_clock_exceeds_cap")

    def test_unsynchronized_key_changes_block(self):
        abc=self.make_score().replace("z4[K:C]z8|","z8[K:C]z4|")
        self.assertEqual(review_score(abc,"[Verse]\nOne\n[Chorus]\nTwo",max_seconds=8)["status"],"blocked")

    def test_unsynchronized_meters_block(self):
        abc=self.make_score().replace("V: Ins\nM:3/4","V: Ins\nM:4/4").replace("z4[K:C]z8|","z4[K:C]z12|")
        self.assertEqual(review_score(abc,"[Verse]\nOne\n[Chorus]\nTwo",max_seconds=8)["status"],"blocked")
