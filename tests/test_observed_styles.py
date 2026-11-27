from pathlib import Path
import tempfile
import unittest
from yue2_music_director import observed_styles as os

ROOT = Path(__file__).resolve().parents[1] / "data/observed_styles"

class ObservedStyleTests(unittest.TestCase):
    def test_actual_snapshot_metadata_and_gaps(self):
        rows, counts = os.load(ROOT)
        self.assertEqual(counts, {"blues":11,"jazz":74,"lofi":0,"pop":18,"indie":0,"folk":0,"backsound":100,"hiphop":0,"lofihop":0,"trap":0})
        self.assertEqual(len(rows), 203)
        self.assertEqual(len({row["isrc"] for row in rows}), 203)
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "observed.sqlite"
            stats = os.build(ROOT, db)
            self.assertEqual(stats["metadata_candidates"], 203)
            self.assertEqual(stats["rights_reviewed_tracks"], 0)
            self.assertEqual(stats["lyrics"], 0)
            self.assertEqual(len(os.search(db, "backsound", limit=100)), 100)
            self.assertEqual(os.search(db, "trap"), [])
            self.assertTrue(os.search(db, "jazz", "jazz"))
