import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from yue2_music_director.expression import plan
from yue2_music_director.lyric_fidelity import compare_lyrics
from yue2_music_director.music import parse_score, ScoreError
from yue2_music_director.cli import main

SCORE = """X:1
T:Synthetic
M:4/4
L:1/8
K:C
%Verse
V:Vocal
"C"C2 E2 G2 C2 | "C"C2 "Dm"E E E G3 | "C"B2 G2 E2 C2 |
V:Ins
"C"C8 | "Dm"D8 | "C"C8 |
"""
LYRICS = "[Verse]\nOne synthetic line\n"


class ExpressionTests(unittest.TestCase):
    def test_onset_not_first_chord_and_round_trip(self):
        result = plan(SCORE, LYRICS)
        report = result["report"]
        self.assertEqual(report["change_count"], 1)
        edit = report["changes"][0]
        self.assertEqual((edit["bar"], edit["chord_at_onset"]), (2, "Dm"))
        self.assertEqual((edit["pitch_before"], edit["pitch_after"]), (64, 65))
        a, b = parse_score(SCORE), parse_score(result["abc"])
        self.assertEqual(a.counts, b.counts)
        self.assertEqual(a.bar_chords, b.bar_chords)
        self.assertEqual([(e.voice,e.duration,e.offset,e.tied) for e in a.events],
                         [(e.voice,e.duration,e.offset,e.tied) for e in b.events])
        self.assertEqual(sum(x.pitch != y.pitch for x,y in zip(a.events,b.events)), 1)
        self.assertEqual([e for e in a.events if e.voice=="Ins"],
                         [e for e in b.events if e.voice=="Ins"])
        self.assertEqual(result, plan(SCORE, LYRICS))
        self.assertEqual(report["audio_jobs_created"], 0)

    def test_no_edit_is_valid(self):
        for kwargs in ({"max_edits": 0}, {"protected_bars": [2]}):
            with self.subTest(kwargs=kwargs):
                result = plan(SCORE, LYRICS, **kwargs)
                self.assertEqual(result["abc"], SCORE)
                self.assertEqual(result["report"]["status"], "no_safe_edits")

    def test_unknown_chord_and_long_repetition(self):
        for source in (SCORE.replace('"Dm"E E E', '"Ddim"E E E'),
                       SCORE.replace('E E E G3', 'E E E E G2'),
                       SCORE.replace('E E E G3', 'E- E E G3'),
                       SCORE.replace('E E E G3', '=E E E G3')):
            with self.subTest(source=source):
                self.assertEqual(plan(source, LYRICS)["report"]["change_count"], 0)

    def test_protected_section_and_phrase(self):
        self.assertEqual(plan(SCORE.replace("%Verse","%Chorus"),
                              LYRICS.replace("Verse","Chorus"))["report"]["change_count"], 0)
        self.assertEqual(plan(SCORE, "[Verse]\none\ntwo\nthree")["report"]["change_count"], 0)

    def test_contour_diversity_across_sections(self):
        # Two verse occurrences, each with identical local choices.
        header, body = SCORE.split("%Verse\n", 1)
        source = header + "%Verse\n" + body + "%Verse\n" + body
        result = plan(source, LYRICS + LYRICS)
        edits = result["report"]["changes"]
        self.assertEqual(len(edits), 2)
        self.assertEqual(len({tuple(e["intervals_after"]) for e in edits}), 2)
        self.assertEqual({e["pitch_after"] for e in edits}, {62,65})

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            plan(SCORE, LYRICS, protected_bars=[4])
        with self.assertRaises(ValueError):
            plan(SCORE, LYRICS, max_edits=-1)
        with self.assertRaises(ScoreError):
            plan(SCORE, "[Chorus]\nwrong")

    def test_cli_does_not_overwrite_or_write_fake_candidate(self):
        with TemporaryDirectory() as tmp, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            root = Path(tmp)
            abc, lyrics = root/"a.abc", root/"lyrics.txt"
            abc.write_text(SCORE, encoding="utf-8")
            lyrics.write_text(LYRICS, encoding="utf-8")
            out = root/"preview"
            args = ["expression",str(abc),"--lyrics",str(lyrics),"--out",str(out),"--max-edits","0"]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            self.assertEqual(abc.read_text(encoding="utf-8"), SCORE)
            self.assertFalse((out/"candidate_expression.abc").exists())
            self.assertEqual(json.loads((out/"expression_report.json").read_text())["change_count"], 0)


class FidelityTests(unittest.TestCase):
    def test_extra_words(self):
        result = compare_lyrics("[Verse]\nI sing tonight", "I really sing tonight")
        self.assertEqual(result["insertions"], 1)
        self.assertEqual(result["deletions"], 0)
        self.assertEqual(result["substitutions"], 0)
        self.assertAlmostEqual(result["word_error_rate"], 1/3)
        self.assertEqual(result["edits"][0]["observed"], "really")

    def test_other_errors(self):
        self.assertEqual(compare_lyrics("[Verse]\none two three", "one three")["deletions"], 1)
        self.assertEqual(compare_lyrics("[Verse]\none two three", "one four three")["substitutions"], 1)
        self.assertEqual(compare_lyrics("[Verse]\nJangan pergi!", "jangan PERGI")["word_error_rate"], 0)
        with self.assertRaises(ValueError):
            compare_lyrics("[Verse]\nhello", "")
