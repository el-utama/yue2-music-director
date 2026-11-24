import unittest
from yue2_music_director.music import (ScoreError, parse_score, humanize_pitch, section_sequence,
                                        chord_tones, repeated_pitch_fraction)
from yue2_music_director.prosody import parse_lyrics, alignment, estimate_syllables

ABC = (
'X:1\nT:Test\nM:2/4\nL:1/16\nK:Bb\n'
'% verse\nV: Vocal\n"Bb"z2B,F2F2F-|"Bb"F2DD3CC-|"Eb"CB,z6|"Eb"z8|\n'
'V: Ins\nZ4|\n'
'% chorus\nV: Vocal\n"Bb"z2BBBd2d-|"F"dccc2B2B-|"Eb"Bz6z|"Eb"z8|\n'
'V: Ins\nZ4|\n'
)
LYRICS = '[Verse 1]\nOne morning\nYou took the road\n[Chorus]\nI will stay\nAnd let you go\n'


class MusicTests(unittest.TestCase):
    def test_01_parse(self):
        score=parse_score(ABC)
        self.assertEqual(score.counts,{'Vocal':8,'Ins':8})
        self.assertEqual(section_sequence(score),['verse','chorus'])
    def test_02_chords(self):
        self.assertEqual(chord_tones('Bb'),{10,2,5})
        self.assertEqual(chord_tones('Eb'),{3,7,10})
    def test_03_reproducibility(self):
        a=humanize_pitch(ABC,LYRICS,42,8)
        b=humanize_pitch(ABC,LYRICS,42,8)
        self.assertEqual(a,b)
    def test_04_never_change_chorus(self):
        output=humanize_pitch(ABC,LYRICS,42,8)['abc']
        old=[e.raw for e in parse_score(ABC).events if e.section=='chorus#1']
        new=[e.raw for e in parse_score(output).events if e.section=='chorus#1']
        self.assertEqual(old,new)
    def test_05_no_change_instrument(self):
        output=humanize_pitch(ABC,LYRICS,42,8)['abc']
        old=[e.raw for e in parse_score(ABC).events if e.voice=='Ins']
        new=[e.raw for e in parse_score(output).events if e.voice=='Ins']
        self.assertEqual(old,new)
    def test_06_fail_mismatch(self):
        with self.assertRaises(ScoreError):
            humanize_pitch(ABC,'[Chorus]\nWrong section',42)
    def test_07_invalid_bar(self):
        with self.assertRaises(ScoreError):
            parse_score(ABC.replace('CB,z6','CB,z5'))
    def test_08_invalid_tie(self):
        with self.assertRaises(ScoreError):
            parse_score(ABC.replace('"Bb"F2DD3CC-','"Bb"G2DD3CC-'))
    def test_09_unknown_key(self):
        with self.assertRaises(ScoreError):
            parse_score(ABC.replace('K:Bb','K:Bmin'))
    def test_10_unknown_ornament(self):
        with self.assertRaises(ScoreError):
            parse_score(ABC.replace('z2B,F2','z2{a}B,F2'))
    def test_11_lyric_parser(self):
        self.assertEqual([s['name'] for s in parse_lyrics(LYRICS)],['verse','chorus'])
    def test_12_syllables(self):
        self.assertGreater(estimate_syllables('One morning walking'),2)
    def test_13_stats(self):
        self.assertGreaterEqual(repeated_pitch_fraction(parse_score(ABC)),0)
    def test_15_short_lyric_phrases_can_change_score(self):
        result=humanize_pitch(ABC,LYRICS,seed=42,max_edits=8)
        self.assertGreater(result['report']['change_count'],0)
        self.assertNotEqual(result['abc'],ABC)
        self.assertEqual(parse_score(ABC).counts,parse_score(result['abc']).counts)

    def test_14_no_output_if_budget_zero(self):
        self.assertEqual(humanize_pitch(ABC,LYRICS,max_edits=0)['abc'],ABC)


if __name__=='__main__':
    unittest.main()
