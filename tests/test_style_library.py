from pathlib import Path
import tempfile
import unittest
from yue2_music_director import style_library as sl

ROOT = Path(__file__).resolve().parents[1] / "data/style_library"

class StyleLibraryTest(unittest.TestCase):
    def test_exact_quota_and_offline_search(self):
        rows = sl.load(ROOT)
        self.assertEqual(len(rows), 1000)
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "style.sqlite"
            stats = sl.build(ROOT, db)
            self.assertEqual(stats["by_genre"], {g: 100 for g in sl.GENRES})
            self.assertEqual(stats["real_track_references"], 0)
            self.assertEqual(stats["lyrics"], 0)
            self.assertEqual(len(sl.search(db, "trap", limit=100)), 100)
            self.assertTrue(sl.search(db, "backsound", "dialogue"))
            self.assertTrue(all(r["genre"] == "lofihop" for r in sl.search(db, "lofihop", "jazz")))
            self.assertEqual(sl.search(db, "blues", "zzzznonexistent"), [])
