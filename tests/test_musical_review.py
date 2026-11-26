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

    def test_mandatory_and_cap(self):
        for kwargs in ({"constraints":{"key":{"mode":"must","value":"Am"}}},
                       {"max_seconds":19.99},
                       {"constraints":{"section_order":{"mode":"must","value":["verse#1"]}}}):
            r=review_score(ABC,LYRICS,**kwargs)
            self.assertEqual(r["status"],"blocked")
            self.assertTrue(r["hard_violations"])
        self.assertFalse(review_score(ABC,LYRICS,max_seconds=20)["hard_violations"])

    def test_unsupported_vs_invalid(self):
        unknown=ABC.replace("F8B8|","F8[K:D]B8|",1)
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
