import copy
from pathlib import Path
import tempfile
import unittest

from yue2_music_director import craft_features as cf, knowledge_bank as kb
from yue2_music_director import creative_knowledge as ck, autonomous_knowledge as ak
from yue2_music_director import native_draft as nd

ROOT = Path(__file__).resolve().parents[1]


class CraftFeaturesTests(unittest.TestCase):
    def test_exact_lexical_and_melodic_fixtures(self):
        lyric = cf.lyric_features("come back home. Come back home! Stay.")
        self.assertEqual(lyric["punctuation_group_count"], 3)
        self.assertEqual(lyric["mean_words_per_punctuation_group"], 2.3333)
        self.assertEqual(lyric["repeated_word_trigram_fraction"], 0.4)
        self.assertEqual(lyric["repeated_punctuation_group_fraction"], 0.6667)
        self.assertIsNone(cf.lyric_features("one")["repeated_word_trigram_fraction"])
        self.assertEqual(cf.melody_features({"step": 3, "leap": 1, "repeat": 2, "ascending": 2}),
                         {"melodic_step_fraction": 0.5, "melodic_leap_fraction": 0.1667,
                          "melodic_repeat_fraction": 0.3333, "melodic_ascending_fraction": 0.3333})
        self.assertIsNone(cf.melody_features({})["melodic_step_fraction"])

    def test_harmony_tokens_are_not_durations(self):
        actual = cf.harmony_features("Composer: X\nm1 C: I b2 V7/ii\nm2 ii b2 ???\nm3 I")
        self.assertEqual(actual["auto_harmony_recognized_tokens"], 4)
        self.assertEqual(actual["auto_harmony_parse_fraction"], 0.8)
        self.assertEqual(actual["auto_harmony_slash_symbol_fraction"], 0.25)
        self.assertEqual(actual["auto_harmony_distinct_symbol_fraction"], 0.75)
        self.assertIsNone(cf.harmony_features("Title: X")["auto_harmony_slash_symbol_fraction"])

    def test_actual_corpus_and_frozen_v1_compatibility(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            db = repo / "local/knowledge-bank.sqlite"
            self.assertEqual(kb.build(ROOT / "data/knowledge_bank", db)["unique_works"], 7)
            rows = kb.retrieve(db, "Schubert", "composer")
            self.assertTrue(rows)
            for row in rows:
                f = row["features"]
                self.assertGreater(f["auto_harmony_recognized_tokens"], 0)
                self.assertGreater(f["punctuation_group_count"], 0)
                self.assertAlmostEqual(sum(f[k] for k in (
                    "melodic_step_fraction", "melodic_leap_fraction", "melodic_repeat_fraction")), 1, places=3)
            current = ak.select(repo, "Schubert")
            self.assertEqual(current["snapshot"]["schema"], ck.VERSION)
            self.assertIn("melodic_step_fraction", ck.payload(current["snapshot"], "composer")["observations"][0])
            self.assertIn("repeated_word_trigram_fraction", ck.payload(current["snapshot"], "lyricist")["observations"][0])
            legacy = copy.deepcopy(current["snapshot"])
            legacy["schema"] = "creative-knowledge-v1"
            for role, items in legacy["roles"].items():
                for item in items:
                    item["features"] = {key: item["features"][key] for key in ck.LEGACY_FIELDS[role]}
            body = {"schema": ak.SCHEMA, "snapshot": legacy}
            frozen = {**body, "sha256": nd.digest(nd._canonical(body))}
            self.assertEqual(ak.validate(frozen), frozen)
            expected = {"schema": "creative-knowledge-v1", "guidance": ck.GUIDANCE,
                        "observations": [row["features"] for row in legacy["roles"]["composer"]]}
            self.assertEqual(ck.payload(legacy, "composer"), expected)
            broken = copy.deepcopy(current["snapshot"])
            broken["roles"]["composer"][0]["features"]["melodic_step_fraction"] = 1.5
            with self.assertRaises(ValueError):
                ck.payload(broken, "composer")
