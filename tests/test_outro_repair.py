import unittest
from yue2_music_director.outro_repair import patch_outro,prepare_replay,CHORDS
from yue2_music_director.music import parse_score

SCORE=("X:1\nT:Test\nM:4/4\nL:1/16\nQ:1/4=120\nK:D\n% chorus\nV: Vocal\n"
       +"D8B8|"*8+"\nV: Ins\nZ8|\n% outro\nV: Vocal\n"+
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


    def test_sparse_native_replay_uses_retained_full_settings(self):
        lyrics="[Chorus]\nOne two\n[Outro]\nThree four\nFive six"
        replay={"abc":SCORE,"lyrics":lyrics,"seed":42,"lm_seed":42,"semantic_tokens":",".join(["7"]*850)}
        song={"replay_request":replay,"generation_settings":{"abc":SCORE,"cot":"full"},
              "metadata":{"cot":"full"}}
        brief={"lyrics":lyrics,"seed":42,"title":"Test"}
        payload,cut,start,end=prepare_replay(song,brief)
        self.assertEqual(payload["replay_request"]["cot"],"full")
        self.assertEqual(cut,400)
        self.assertNotIn("cot",replay)
        for wrong in ("off","melody",None):
            with self.subTest(mode=wrong),self.assertRaisesRegex(ValueError,"Full-score mode"):
                prepare_replay({**song,"replay_request":{**replay,"cot":wrong}},brief)
        with self.assertRaisesRegex(ValueError,"Full-score mode"):
            prepare_replay({"replay_request":replay,"generation_settings":{"abc":SCORE}},brief)
        with self.assertRaisesRegex(ValueError,"Full-score mode"):
            prepare_replay({**song,"metadata":{"cot":"off"}},brief)


class EndingV2Tests(unittest.TestCase):
    @staticmethod
    def source():
        header="X:1\nT:Test\nM:4/4\nL:1/16\nQ:1/4=87\nK:D\n"
        sections=[("intro",9,False),("verse",8,True),("pre-chorus",4,True),
                  ("chorus",9,True),("verse",8,True),("pre-chorus",5,True),
                  ("chorus",9,True),("interlude",8,False),("chorus",8,True)]
        for name,n,sung in sections:
            vocal="D8B8|"*n if sung else f"Z{n}|"
            header+=f"% {name}\nV: Vocal\n{vocal}\nV: Ins\nZ{n}|\n"
        return header+"% outro\nV: Vocal\n"+"".join('"'+c+'"z16|' for c in CHORDS)+"\nV: Ins\nZ9|\n"

    def test_restructure_preserves_first_sixty_bars(self):
        from yue2_music_director.outro_repair import restructure_ending
        source=self.source()
        fixed=restructure_ending(source)
        self.assertEqual(fixed.split("% outro")[0],source[:source.rfind("% chorus")])
        self.assertEqual(parse_score(fixed).counts,{"Vocal":67,"Ins":67})
        self.assertEqual(len([e for e in parse_score(fixed).events
                             if e.voice=="Vocal" and e.section=="outro#1" and e.kind=="note"]),19)
        with self.assertRaises(ValueError):
            restructure_ending(source.replace("Q:1/4=87","Q:1/4=88"))

    def test_replay_scope_and_budget(self):
        from unittest.mock import patch
        from yue2_music_director import outro_repair as repair
        from hashlib import sha256
        source=self.source()
        lyrics="[Chorus]\nOne two\n[Outro]\nThree four\nFive six"
        tokens=",".join(str(i%32768) for i in range(5243))
        replay={"abc":source,"lyrics":lyrics,"seed":42,"lm_seed":42,"semantic_tokens":tokens}
        song={"replay_request":replay,"generation_settings":{"abc":source,"cot":"full"}}
        brief={"lyrics":lyrics,"seed":42,"title":"Test"}
        with self.assertRaisesRegex(ValueError,"listening evidence"):
            repair.prepare_replay_v2(song,brief)
        digest=lambda s:sha256(s.encode()).hexdigest()
        with patch.multiple(repair,V2_SCORE_SHA=digest(source.strip()),
                            V2_LYRICS_SHA=digest(lyrics),
                            V2_PREFIX_SHA=digest(",".join(tokens.split(",")[:4689]))):
            payload,cut,start,end=repair.prepare_replay_v2(song,brief)
        self.assertEqual((cut,start),(4000,160.0))
        self.assertAlmostEqual(end,184.82758620689654)
        fields=payload["replay_request"]
        self.assertEqual(fields["semantic_tokens"].split(","),tokens.split(",")[:4000])
        self.assertEqual(fields["semantic_sampling"]["min_tokens"],4413)
        self.assertEqual(fields["semantic_sampling"]["max_tokens"],4634)
        self.assertTrue(fields["continue_semantic_tokens"])
        self.assertEqual(replay["semantic_tokens"],tokens)
        self.assertTrue(payload["title"].endswith("Ending candidate v2"))


class EndingV3Tests(unittest.TestCase):
    def fixtures(self):
        from yue2_music_director.outro_repair import V3_JOB_ID
        outro="[Outro]\nSemoga damai menemanimu\nKulepas engkau dengan cinta"
        lyrics="[Verse 1]\nSenja jatuh di bahumu\n\n"+outro
        fields={"lyrics":lyrics,"abc":"score","cot":"full","semantic_tokens":"1,2",
                "continue_semantic_tokens":True,"seed":42,"lm_seed":42,
                "duration":185.32758620689654,"semantic_sampling":{"min_tokens":4413,"max_tokens":4634}}
        payload={"title":"Test - Ending candidate v2","replay_request":fields}
        schedule={"mode":"bias","bias":-4.0,"sections":[
            {"start_sec":24.828,"lyric":[0,29]},
            {"start_sec":165.517,"lyric":[lyrics.index("[Outro]"),len(lyrics)]}]}
        receipt={"id":V3_JOB_ID,"generation_settings":{**fields,"lyric_schedule":schedule}}
        return payload,receipt,outro

    def test_only_lyric_conditioning_changes(self):
        from yue2_music_director.outro_repair import prepare_replay_v3
        import copy
        payload,receipt,outro=self.fixtures()
        before=copy.deepcopy(payload)
        candidate=prepare_replay_v3(payload,receipt)
        self.assertEqual(candidate["replay_request"],{**before["replay_request"],"lyrics":outro})
        self.assertEqual(candidate["title"],"Test - Ending candidate v3")
        self.assertEqual(payload,before)

    def test_mismatched_v2_evidence_blocks(self):
        from yue2_music_director.outro_repair import prepare_replay_v3
        import copy
        payload,receipt,_=self.fixtures()
        for key,value in (("seed",43),("semantic_tokens","3,4"),("abc","different")):
            bad=copy.deepcopy(receipt)
            bad["generation_settings"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                prepare_replay_v3(payload,bad)
        bad=copy.deepcopy(receipt)
        bad["generation_settings"]["lyric_schedule"]["sections"][-1]["start_sec"]=187.586
        with self.assertRaises(ValueError):
            prepare_replay_v3(payload,bad)
        with self.assertRaises(ValueError):
            prepare_replay_v3(payload,{**receipt,"id":"wrong"})

    def test_v3_schedule_rebuilt_over_isolated_lyrics(self):
        from yue2_music_director.outro_repair import prepare_replay_v3,verify_v3_receipt
        import copy
        payload,receipt,outro=self.fixtures()
        candidate=prepare_replay_v3(payload,receipt)
        settings={**candidate["replay_request"],"lyric_schedule":{"mode":"bias","bias":-4.0,
                  "sections":[{"start_sec":165.517,"lyric":[0,len(outro)]}]}}
        verify_v3_receipt({"generation_settings":settings},candidate)
        bad=copy.deepcopy(settings)
        bad["lyric_schedule"]["sections"][0]["lyric"]=[640,699]
        with self.assertRaises(ValueError):
            verify_v3_receipt({"generation_settings":bad},candidate)
        with self.assertRaises(ValueError):
            verify_v3_receipt(receipt,candidate)
