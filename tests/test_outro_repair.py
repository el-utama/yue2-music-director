import unittest
from yue2_music_director.outro_repair import patch_outro,prepare_replay,CHORDS
from yue2_music_director.music import parse_score

SCORE=("X:1\nT:Test\nM:4/4\nL:1/16\nQ:1/4=120\nK:D\n% chorus\nV: Vocal\n"
       "D8B8|"*8+"\nV: Ins\nZ8|\n% outro\nV: Vocal\n"+
       "".join('"'+c+'"z16|' for c in CHORDS[:4])+"\nV: Ins\nZ4|\nV: Vocal\n"+
       "".join('"'+c+'"z16|' for c in CHORDS[4:])+"\nV: Ins\nZ5|\n")

class OutroRepairTests(unittest.TestCase):
    def test_only_silent_outro_is_patched(self):
        candidate,start,end=patch_outro(SCORE)
        self.assertEqual((start,end),(16,34))
        parsed=parse_score(candidate)
        self.assertEqual(parsed.counts,{"Vocal":17,"Ins":17})
        self.assertEqual(sum(e.voice=="Vocal" and e.kind=="note" and e.section=="outro#1" for e in parsed.events),19)
        self.assertTrue(candidate.endswith('"Dmaj7"z16|\nV: Ins\nZ5|\n'))
        self.assertEqual(candidate.split("% outro")[0],SCORE.split("% outro")[0])

    def test_continuation_carries_only_prefix(self):
        lyrics="[Chorus]\nOne two\n[Outro]\nThree four\nFive six"
        replay={"abc":SCORE,"lyrics":lyrics,"seed":42,"lm_seed":42,"cot":"full","semantic_tokens":",".join(["7"]*850)}
        payload,cut,start,end=prepare_replay({"replay_request":replay,"generation_settings":{"abc":SCORE}},
                                            {"lyrics":lyrics,"seed":42,"title":"Test"})
        self.assertEqual(cut,400)
        self.assertTrue(payload["replay_request"]["continue_semantic_tokens"])
        self.assertEqual(payload["replay_request"]["semantic_tokens"].split(","),["7"]*400)
        self.assertEqual(replay["semantic_tokens"].split(","),["7"]*850)
        self.assertGreater(payload["replay_request"]["semantic_sampling"]["min_tokens"],cut)

    def test_unexpected_score_fails_closed(self):
        with self.assertRaises(ValueError):
            patch_outro(SCORE.replace('"Em7"z16','"Em7"E16',1))
