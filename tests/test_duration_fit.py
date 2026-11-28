import unittest
from yue2_music_director.duration_fit import preview

HEADER=('X:1\nT:\nM:2/4\nL:1/32\nQ:1/4=71\n'
        'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"\n'
        'V: Ins clef=treble name="Ins Melody" snm="Inst."\nK:C\n')
# Native ABC requires paired groups of 1–4 bars per voice.
ABC=HEADER+'% verse\n'+''.join('V: Vocal\n'+'C16|'*n+'\nV: Ins\n'+'Z|'*n+'\n' for n in [4]*30+[3])
BRIEF={"lyrics":"[Verse]\nOne two","duration_seconds":195,"style":"English, folk, acoustic guitar"}
INTENT={"schema":"artist-intent-v1","route":"reviewed_native","concept":"Farewell",
        "emotional_arc":"loss to resolve","performance":"Gentle delivery",
        "section_purposes":{"verse#1":"Develop story"},"constraints":{},
        "retain_soft_flags":{},"follow_lyrics":True,
        "budget":{"score_jobs":1,"song_jobs":1,"recognition_calls":1}}


class DurationFitTests(unittest.TestCase):
    def test_small_overrun_preserves_notation(self):
        result=preview(ABC,BRIEF,INTENT)
        self.assertEqual(result["status"],"candidate_available",result)
        self.assertEqual(result["candidate_tempo_bpm"],77)
        self.assertAlmostEqual(result["original_score_seconds"],207.88732394366198)
        self.assertLessEqual(result["candidate_score_seconds"],192)
        self.assertTrue(result["notation_preserved_except_tempo"])
        self.assertFalse(result["render_authorized"])
        self.assertEqual(result["studio_calls"],0)

    def test_refuses_large_change_and_explicit_tempo(self):
        self.assertEqual(preview(ABC,{**BRIEF,"duration_seconds":170},INTENT)["status"],"not_eligible")
        self.assertEqual(preview(ABC,{**BRIEF,"style":"folk, 71 BPM"},INTENT)["status"],"not_eligible")
        constrained={**INTENT,"constraints":{"tempo_bpm":{"mode":"must","value":71}}}
        self.assertEqual(preview(ABC,BRIEF,constrained)["status"],"not_eligible")

    def test_refuses_other_flags_and_already_valid(self):
        self.assertEqual(preview(ABC,{**BRIEF,"duration_seconds":208},INTENT)["status"],"not_eligible")
        self.assertEqual(preview(ABC,{**BRIEF,"lyrics":"[Verse]\nOne\n[Chorus]\nTwo"},INTENT)["status"],"not_eligible")
