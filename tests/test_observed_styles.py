from pathlib import Path
import tempfile
import unittest
from yue2_music_director import observed_styles as os

ROOT = Path(__file__).resolve().parents[1] / "data/observed_styles"

class ObservedStyleTests(unittest.TestCase):
    def test_actual_snapshot_metadata_and_gaps(self):
        rows, counts = os.load(ROOT)
        self.assertEqual(counts, {"blues":100,"jazz":100,"lofi":100,"pop":100,"indie":100,"folk":100,"backsound":100,"hiphop":100,"lofihop":8,"trap":15})
        self.assertEqual(len(rows), 823)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "observed.sqlite"
            stats = os.build(ROOT, db)
            self.assertEqual(stats["metadata_candidates"], 823)
            self.assertEqual(stats["rights_reviewed_tracks"], 0)
            self.assertEqual(stats["lyrics"], 0)
            self.assertEqual(len(os.search(db, "backsound", limit=100)), 100)
            self.assertTrue(os.search(db, "trap"))
            self.assertEqual(stats["annotated_clips"], 517)
            self.assertEqual(stats["track_metadata"], 203)
            self.assertEqual(stats["curated_track_candidates"], 95)
            self.assertEqual(stats["disclosed_ai_track_candidates"], 8)
            self.assertEqual(len(os.search(db, "lofi", limit=100)), 100)
            self.assertTrue(all(r["metadata_origin"] == "creator_catalog_disclosed_suno_v5" for r in os.search(db, "lofihop")))
            self.assertTrue(all(r["metadata_license"] == "CC-BY-SA-4.0" for r in os.search(db, "trap")))
            self.assertTrue(os.search(db, "jazz", "jazz"))
