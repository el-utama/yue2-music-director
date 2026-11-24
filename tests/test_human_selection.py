import unittest
from yue2_music_director.native_recognition import review
from yue2_music_director.human_selection import compare

ASR = review("[Verse]\nSing now\nStay here",
             {"provider":"whisper","text":"sing now stay here"},
             {"provider":"whisper","text":"sing then go there"})


def observations(lyrics="candidate", music="candidate"):
    return {"baseline":"B","candidate":"C","preferences":[
        {"criterion":"overall_lyrics","preference":lyrics},
        {"criterion":"overall_music","preference":music},
        {"criterion":"verse_line","preference":"candidate",
         "line":{"section":"verse#1","line_index":1}}]}


class HumanSelectionTests(unittest.TestCase):
    def test_preference_conflicts_with_asr(self):
        r = compare(ASR,observations())
        self.assertIsNone(r["provisional_preferred"])
        self.assertEqual(r["provisional_lyric_preferred"],"B")
        self.assertEqual(r["human_music_preferred"],"C")
        self.assertEqual(r["selection_status"],"tradeoff_review_required")
        self.assertEqual(r["asr_comparison_counts"]["disagreement"],2)
        self.assertEqual(r["human_preference_counts"]["candidate"],3)
        self.assertFalse(r["automatic_acceptance"])
        self.assertFalse(r["automatic_regeneration"])
        self.assertEqual(r["absolute_fidelity_status"],"not_established_by_relative_review")
        self.assertEqual(r["audio_jobs_created"],0)

    def test_mixed_overall_preferences_require_decision(self):
        for lyrics,music in (("baseline","candidate"),("candidate","tie"),("uncertain","candidate")):
            h = observations(lyrics,music)
            h["lyric_evidence_policy"] = "human_reviewed"
            if lyrics == "candidate" and music == "tie":
                self.assertEqual(compare(ASR,h)["provisional_preferred"],"C")
            else:
                self.assertIsNone(compare(ASR,h)["provisional_preferred"])

    def test_invalid_and_duplicate_criteria(self):
        h = observations()
        h["preferences"].append(h["preferences"][0])
        with self.assertRaises(ValueError):
            compare(ASR,h)
        h = observations()
        h["preferences"][2]["line"]["line_index"] = 9
        with self.assertRaises(ValueError):
            compare(ASR,h)
        h = observations()
        h["preferences"] = h["preferences"][1:]
        with self.assertRaises(ValueError):
            compare(ASR,h)
