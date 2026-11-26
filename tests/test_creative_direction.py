import unittest
from yue2_music_director import creative_direction as cd
from yue2_music_director.musical_review import review_score

HEADER=('X:1\nT:\nM:2/4\nL:1/32\nQ:1/4=60\n'
        'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"\n'
        'V: Ins clef=treble name="Ins Melody" snm="Inst."\nK:C\n')
INTRO='% intro\nV: Vocal\nZ|\nV: Ins\nC16|\n'
VERSE='% verse\nV: Vocal\n"C"C8D8|\nV: Ins\nZ|\n'
WORDS='[Verse]\nOne two'


class OpeningTests(unittest.TestCase):
    def composition(self,opening):
        return {"performance":"Opening: "+opening+"\nVocal: female\nNarrator: male protagonist\nGentle entrance"}

    def test_separate_narrator_and_vocal(self):
        self.assertEqual(cd.validate_opening(self.composition("instrumental_intro"),"[Intro]\n"+WORDS)["vocal"],"female")
        with self.assertRaises(ValueError):
            cd.validate_opening(self.composition("instrumental_intro"),WORDS)
        with self.assertRaises(ValueError):
            cd.validate_opening(self.composition("instrumental_intro"),"[Intro]\nWords\n"+WORDS)
        self.assertEqual(cd.validate_opening(self.composition("direct_vocal"),WORDS)["opening"],"direct_vocal")
        with self.assertRaises(ValueError):
            cd.validate_opening(self.composition("direct_vocal"),"[Intro]\n"+WORDS)

    def test_score_gate(self):
        con={"opening":{"mode":"must","value":"instrumental_intro"}}
        good=review_score(HEADER+INTRO+VERSE,"[Intro]\n"+WORDS,constraints=con,max_seconds=30)
        self.assertEqual(good["status"],"local_review_ready",good)
        self.assertEqual(good["metrics"]["opening"],"instrumental_intro")
        bad=review_score(HEADER+VERSE,"[Intro]\n"+WORDS,constraints=con,max_seconds=30)
        self.assertEqual(bad["status"],"blocked")
        wrong=review_score(HEADER+INTRO.replace("V: Vocal\nZ|","V: Vocal\nC16|")+VERSE,"[Intro]\n"+WORDS,constraints=con,max_seconds=30)
        self.assertEqual(wrong["status"],"blocked")
        direct=review_score(HEADER+VERSE,WORDS,constraints={"opening":{"mode":"must","value":"direct_vocal"}},max_seconds=30)
        self.assertEqual(direct["status"],"local_review_ready")
        old=review_score(HEADER+VERSE,WORDS,max_seconds=30)
        self.assertNotIn("opening",old["metrics"])
