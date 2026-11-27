import unittest
from yue2_music_director.native_lyric_schedule import inspect_schedule
from yue2_music_director.director_decision import context


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.lyrics="[Intro]\n\n[Verse 1]\n心の声\n\n[Instrumental Break]\n\n[Chorus]\nécho 🌙\n"
        self.verse="[Verse 1]\n心の声"
        self.chorus="[Chorus]\nécho 🌙"
        self.entries=[self.entry(self.verse,4),self.entry(self.chorus,10)]

    def entry(self,text,start):
        i=self.lyrics.index(text)
        return {"start_sec":start,"lyric":[i,i+len(text)]}

    def settings(self,entries):
        return {"lyrics":self.lyrics,"cot":"full","cfg_scale":1,
                "lyric_schedule":{"mode":"bias","bias":-4,"sections":entries}}

    def test_full_unicode_coverage_and_partial(self):
        result=inspect_schedule(self.settings(self.entries))
        self.assertEqual(result["status"],"all_blocks_recorded")
        self.assertEqual(result["expected_sung_blocks"],2)
        self.assertEqual(result["scheduled_sung_blocks"],2)
        self.assertEqual(result["first_vocal_score_seconds"],4)
        self.assertFalse(result["acoustic_alignment_verified"])
        result=inspect_schedule(self.settings(self.entries[1:]))
        self.assertEqual(result["status"],"partial_blocks_recorded")
        self.assertEqual(result["scheduled_sung_blocks"],1)

    def test_missing_is_not_proof_of_failure_or_alignment(self):
        result=inspect_schedule({"lyrics":self.lyrics,"lyric_timing":True})
        self.assertEqual(result["status"],"not_recorded")
        self.assertIsNone(result["scheduled_sung_blocks"])
        self.assertFalse(result["acoustic_alignment_verified"])
        self.assertEqual(inspect_schedule(None)["status"],"unknown")

    def test_invalid_spans_and_times(self):
        for entries in ([{"start_sec":True,"lyric":self.entries[0]["lyric"]}],
                        [{"start_sec":float("nan"),"lyric":self.entries[0]["lyric"]}],
                        [{"start_sec":4,"lyric":[0,999]}],
                        [self.entries[0],self.entries[0]],
                        self.entries[::-1]):
            with self.subTest(entries=entries):
                self.assertEqual(inspect_schedule(self.settings(entries))["status"],"invalid_or_unrecognized")
        self.assertEqual(inspect_schedule({**self.settings(self.entries),"cfg_scale":2})["status"],"invalid_or_unrecognized")

    def test_context_only_changes_when_report_contains_new_evidence(self):
        report={"acoustic":{},"lyric_screen":{},"headroom_pass":True,"duration_cap_screen_pass":True}
        old=context("request",{}, {},report,{"observations":[]})
        evidence=inspect_schedule(self.settings(self.entries))
        new=context("request",{}, {},{**report,"native_lyric_schedule":evidence},{"observations":[]})
        self.assertNotIn("native_lyric_schedule",old["technical"])
        self.assertEqual(new["technical"].pop("native_lyric_schedule"),evidence)
        self.assertEqual(old,new)
