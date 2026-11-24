import unittest

from yue2_music_director.music import (
    ScoreError, conservative_rejection, humanize_pitch, parse_score,
)


def score(chord, melody):
    return (
        'X:1\nT:Regression\nM:2/4\nL:1/16\nK:Bb\n'
        '% verse\nV: Vocal\n'
        f'"{chord}"{melody}|\n'
        'V: Ins\nZ|\n'
    )


LYRICS = '[Verse]\nThis line has four syllables\n'


class ConservativePitchTests(unittest.TestCase):
    def test_four_semitone_edit_is_deferred_not_filled(self):
        # F4 -> A4 is a valid F-major chord tone but exceeds the conservative
        # three-semitone pitch shift threshold.
        original = score('F', 'F2F2F2z2')
        old = humanize_pitch(original, LYRICS, seed=42, profile='legacy')
        self.assertEqual(old['report']['change_count'], 1)
        self.assertEqual(old['report']['changes'][0]['pitch_before'], 65)
        self.assertEqual(old['report']['changes'][0]['pitch_after'], 69)
        revised = humanize_pitch(original, LYRICS, seed=42)
        self.assertEqual(revised['abc'], original)
        self.assertEqual(revised['report']['proposed_change_count'], 1)
        self.assertEqual(revised['report']['change_count'], 0)
        self.assertEqual(len(revised['report']['deferred_changes']), 1)
        self.assertIn('pitch_shift_exceeds_3_semitones',
                      revised['report']['deferred_changes'][0]['reasons'])

    def test_worsened_melodic_leap_is_deferred(self):
        # Bb3 -> G3 widens the following leap up to F4 from 7 to 10.
        original = score('Eb', 'B,2B,2F2z2')
        old = humanize_pitch(original, LYRICS, seed=42, profile='legacy')
        self.assertEqual(old['report']['change_count'], 1)
        self.assertEqual(old['report']['changes'][0]['pitch_before'], 58)
        self.assertEqual(old['report']['changes'][0]['pitch_after'], 55)
        new = humanize_pitch(original, LYRICS, seed=42)
        self.assertEqual(new['report']['change_count'], 0)
        self.assertEqual(new['report']['proposed_change_count'], 1)
        self.assertTrue(any('next_leap_worsened' in reason
                            for reason in new['report']['deferred_changes'][0]['reasons']))

    def test_benign_edit_allowed_and_deterministic(self):
        original = score('Bb', 'z2B,F2F2F-') # needs tied continuation
        # Use the existing validated fixture rather than pretending an invalid
        # score is usable.
        sample = ('X:1\nT:Demo\nM:2/4\nL:1/16\nK:Bb\n'
                  '% verse\nV: Vocal\n"Bb"z2B,F2F2F-|"Bb"F2DD3CC-|"Eb"CB,z6|"Eb"z8|\n'
                  'V: Ins\nZ4|\n')
        a = humanize_pitch(sample, '[Verse]\nSmall roads\n', profile='conservative')
        b = humanize_pitch(sample, '[Verse]\nSmall roads\n', profile='conservative')
        self.assertEqual(a,b)
        self.assertGreater(a['report']['change_count'], 0)
        self.assertEqual(parse_score(a['abc']).counts,parse_score(sample).counts)
        self.assertEqual(a['report']['profile'],'conservative')

    def test_rejection_function_both_sides(self):
        self.assertEqual(conservative_rejection(62,65,65,65),[])
        self.assertIn('previous_leap_worsened_to_7_semitones',
                      conservative_rejection(58,55,62,None))
        self.assertIn('next_leap_worsened_to_7_semitones',
                      conservative_rejection(65,69,None,62))
        self.assertEqual(conservative_rejection(65,65,50,80),[])

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            humanize_pitch(score('Bb','B,2B,2B,2z2'),LYRICS,profile='surprise')

    def test_zero_budget_unchanged_in_both_profiles(self):
        original=score('F','F2F2F2z2')
        for profile in ('legacy','conservative'):
            result=humanize_pitch(original,LYRICS,max_edits=0,profile=profile)
            self.assertEqual(result['abc'],original)
            self.assertEqual(result['report']['change_count'],0)
            self.assertEqual(result['report']['profile'],profile)


if __name__=='__main__':
    unittest.main()
