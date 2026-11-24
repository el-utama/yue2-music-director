import unittest
from yue2_music_director.phrase_rhythm import analyze
from yue2_music_director.music import ScoreError

SCORE = """X:1
T:Rhythm fixture
M:4/4
L:1/8
K:C
%Verse
V:Vocal
"C"C2 z2 E4 | Z1 | "C"G2 G2 G2 G2 |
V:Ins
"C"C8 | "C"C8 | "C"C8 |
"""
LYRICS = "[Verse]\nSing now\nStay here\nOne two three four"

class RhythmTests(unittest.TestCase):
    def test_score_units_and_silence(self):
        result = analyze(SCORE, LYRICS)
        first, second, third = result["phrases"]
        self.assertEqual(result["phrase_count"], 3)
        self.assertEqual(first["allocated_quarter_notes"], 4)
        self.assertEqual(first["sounding_quarter_notes"], 3)
        self.assertEqual(first["non_sounding_quarter_notes"], 1)
        self.assertAlmostEqual(first["words_per_sounding_quarter"], 2/3)
        self.assertEqual(second["sounding_quarter_notes"], 0)
        self.assertIsNone(second["words_per_sounding_quarter"])
        self.assertIn("no_notated_vocal_sound", second["review_flags"])
        self.assertEqual(third["note_events"], 4)
        self.assertEqual(result["audio_jobs_created"], 0)
        self.assertEqual(result["paired_timing_count"], 0)

    def test_reviewed_pair(self):
        rows = [{"section":"verse#1","line_index":1,
                 "A":{"start":2,"end":3,"transcript":"Sing now now"},
                 "B":{"start":4,"end":6,"transcript":"Sing now"}}]
        pair = analyze(SCORE, LYRICS, rows)["paired_timings"][0]
        self.assertEqual(pair["duration_ratio_B_over_A"], 2)
        self.assertEqual(pair["A"]["observed_words_per_second"], 3)
        self.assertEqual(pair["B"]["observed_words_per_second"], 1)
        self.assertEqual(pair["A"]["lyric_fidelity"]["insertions"], 1)
        self.assertEqual(pair["B"]["lyric_fidelity"]["word_error_rate"], 0)

    def test_empty_annotation_and_omitted_annotation(self):
        rows = [{"section":"verse#1","line_index":1,
                 "A":{"start":0,"end":1,"transcript":""},
                 "B":{"start":0,"end":1}}]
        pair = analyze(SCORE, LYRICS, rows)["paired_timings"][0]
        self.assertEqual(pair["A"]["lyric_fidelity"]["deletions"], 2)
        self.assertNotIn("lyric_fidelity", pair["B"])

    def test_invalid_timings(self):
        valid = {"section":"verse#1","line_index":1,
                 "A":{"start":1,"end":2},"B":{"start":1,"end":2}}
        for rows in ([valid,valid], [{**valid,"line_index":4}],
                     [{**valid,"B":{"start":0,"end":0}}],
                     [{**valid,"B":{"start":0,"end":float("nan")}}],
                     [valid,{**valid,"line_index":2}], []):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                analyze(SCORE, LYRICS, rows)
        with self.assertRaises(ScoreError):
            analyze(SCORE, "[Chorus]\nWrong")

    def test_uneven_partition_and_zero_bar(self):
        phrases = analyze(SCORE, "[Verse]\nOne\nTwo\nThree\nFour")["phrases"]
        self.assertIsNone(phrases[0]["bar_start"])
        self.assertEqual([p["bar_start"] for p in phrases], [None,1,2,3])
