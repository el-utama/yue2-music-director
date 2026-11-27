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

class OpeningTimingTests(unittest.TestCase):
    def review(self,abc,lyrics,opening):
        return review_score(abc,lyrics,constraints={
            "opening":{"mode":"must","value":opening},
            "opening_timing":{"mode":"must","value":opening}},max_seconds=30)

    def test_intro_evidence_and_empty_conditioning(self):
        good=self.review(HEADER+INTRO+VERSE,"[Intro]\n"+WORDS,"instrumental_intro")
        self.assertEqual(good["status"],"local_review_ready",good)
        evidence=good["metrics"]["opening_evidence"]
        self.assertEqual(evidence["first_vocal_onset_seconds"],2)
        self.assertEqual(evidence["notated_intro_duration_seconds"],2)
        self.assertEqual(evidence["first_ins_onset_seconds"],0)
        self.assertEqual(evidence["intro_accompaniment"],"notated_ins_activity")
        self.assertFalse(evidence["acoustic_verified"])
        silent=HEADER+INTRO.replace("C16|","Z|")+VERSE
        uncertain=self.review(silent,"[Intro]\n"+WORDS,"instrumental_intro")
        self.assertEqual(uncertain["status"],"blocked",uncertain)
        evidence=uncertain["metrics"]["opening_evidence"]
        self.assertEqual(evidence["intro_accompaniment"],"unverified")
        self.assertEqual(evidence["classification"],"unassessed")
        self.assertIsNone(evidence["first_ins_onset_seconds"])
        # An old v2 review must retain its exact shape and behavior.
        old=review_score(silent,"[Intro]\n"+WORDS,constraints={"opening":{"mode":"must","value":"instrumental_intro"}},max_seconds=30)
        self.assertEqual(old["status"],"local_review_ready")
        self.assertNotIn("opening_evidence",old["metrics"])

    def test_direct_short_pickup_vs_long_initial_silence(self):
        pickup=HEADER+VERSE.replace('"C"C8D8|','"C"z4C12|')
        good=self.review(pickup,WORDS,"direct_vocal")
        self.assertEqual(good["status"],"local_review_ready",good)
        self.assertEqual(good["metrics"]["opening_evidence"]["first_vocal_onset_seconds"],0.5)
        late=HEADER+VERSE.replace('"C"C8D8|','"C"z16|z16|C16|').replace("V: Ins\nZ|","V: Ins\nZ3|")
        bad=self.review(late,WORDS,"direct_vocal")
        self.assertEqual(bad["status"],"blocked",bad)
        self.assertEqual(bad["metrics"]["opening_evidence"]["first_vocal_onset_seconds"],4)
        self.assertEqual(bad["metrics"]["opening_evidence"]["classification"],"unassessed")
        self.assertIn("opening_timing",[v.get("field") for v in bad["hard_violations"]])
        after_intro=self.review(HEADER+INTRO+late[len(HEADER):],"[Intro]\n"+WORDS,"instrumental_intro")
        self.assertEqual(after_intro["status"],"blocked",after_intro)
        self.assertEqual(after_intro["metrics"]["opening_evidence"]["first_vocal_onset_seconds"],6)

    def test_free_constraint_does_not_force_opening(self):
        report=review_score(HEADER+VERSE,WORDS,constraints={"opening_timing":{"mode":"free","value":None}})
        self.assertFalse(report["hard_violations"])
        self.assertEqual(report["metrics"]["opening_evidence"]["classification"],"direct_vocal")

    def test_director_context_version_and_lra(self):
        from yue2_music_director import director_decision as dd
        report={"acoustic":{"duration_seconds":3,"integrated_lufs":-17,
                            "true_peak_dbtp":-1.2,"loudness_range_lu":5.7},
                "lyric_screen":{},"headroom_pass":True,"duration_cap_screen_pass":True,
                "saved_score_review":self.review(HEADER+VERSE,WORDS,"direct_vocal")}
        old={"constraints":{"opening":{"mode":"must","value":"direct_vocal"}}}
        new={"constraints":{**old["constraints"],"opening_timing":{"mode":"must","value":"direct_vocal"}}}
        previous=dd.context("fixture",{},old,report,{"observations":[]})
        self.assertIsNone(previous["technical"]["lra_lu"])
        self.assertNotIn("context_schema",previous)
        self.assertNotIn("opening_evidence",previous["score_evidence"])
        current=dd.context("fixture",{},new,report,{"observations":[]})
        self.assertEqual(current["context_schema"],"director-context-v3")
        self.assertEqual(current["technical"]["loudness_range_lu"],5.7)
        self.assertNotIn("lra_lu",current["technical"])
        self.assertEqual(current["score_evidence"]["opening_evidence"]["first_vocal_onset_seconds"],0)
