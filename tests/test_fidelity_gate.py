import unittest
from yue2_music_director.fidelity_gate import diagnose
from yue2_music_director.native_recognition import review

SCORE = """X:1
T:Fixture
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
ASR = review(LYRICS, {"provider":"whisper","text":"sing now stay here one two three four"},
             {"provider":"whisper","text":"sing now stay here one two three four"})


def line(i):
    return {"section":"verse#1","line_index":i}


class FidelityGateTests(unittest.TestCase):
    def test_confirmed_issue_blocks_even_perfect_asr(self):
        obs = {"lines":[{**line(2),"status":"issue_confirmed"}],
               "transitions":[{"after":line(2),"before":line(3),"status":"issue_confirmed"}]}
        r = diagnose(SCORE, LYRICS, ASR, obs)
        self.assertEqual(r["gate"],"blocked_confirmed_issue")
        self.assertEqual(r["confirmed_issue_lines"],1)
        self.assertEqual(r["confirmed_issue_transitions"],1)
        self.assertEqual(r["phrases"][0]["human_status"],"not_reviewed")
        self.assertEqual(r["phrases"][1]["asr_edit_counts"],{"A":0,"B":0})
        self.assertEqual(r["phrases"][1]["bar_start"],2)
        self.assertEqual(r["audio_jobs_created"],0)
        self.assertEqual(r["score_edits"],0)

    def test_unreviewed_not_accepted(self):
        r = diagnose(SCORE,LYRICS,ASR,{"lines":[],"transitions":[]})
        self.assertEqual(r["gate"],"not_assessed_for_acceptance")

    def test_invalid_observations(self):
        good = {**line(1),"status":"issue_confirmed"}
        for obs in ({"lines":[good,good],"transitions":[]},
                    {"lines":[{**line(9),"status":"issue_confirmed"}],"transitions":[]},
                    {"lines":[],"transitions":[{"after":line(1),"before":line(3),"status":"issue_confirmed"}]}):
            with self.assertRaises(ValueError):
                diagnose(SCORE,LYRICS,ASR,obs)

    def test_mismatched_reference(self):
        with self.assertRaises(ValueError):
            diagnose(SCORE,LYRICS.replace("Sing now","Sing again"),ASR,{"lines":[],"transitions":[]})
