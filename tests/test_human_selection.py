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
        self.assertEqual(r["provisional_preferred"],"C")
        self.assertEqual(r["asr_comparison_counts"]["disagreement"],2)
        self.assertEqual(r["human_preference_counts"]["candidate"],3)
        self.assertFalse(r["automatic_acceptance"])
        self.assertFalse(r["automatic_regeneration"])
        self.assertEqual(r["absolute_fidelity_status"],"not_established_by_relative_review")
        self.assertEqual(r["audio_jobs_created"],0)

    def test_mixed_overall_preferences_require_decision(self):
        for lyrics,music in (("baseline","candidate"),("candidate","tie"),("uncertain","candidate")):
            self.assertIsNone(compare(ASR,observations(lyrics,music))["provisional_preferred"])

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
