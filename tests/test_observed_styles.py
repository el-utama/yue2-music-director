from pathlib import Path
import tempfile
import unittest
from yue2_music_director import observed_styles as os

ROOT = Path(__file__).resolve().parents[1] / "data/observed_styles"

class ObservedStyleTests(unittest.TestCase):
    def test_actual_snapshot_metadata_and_gaps(self):
        rows, counts = os.load(ROOT)
        self.assertEqual(counts, {"blues":100,"jazz":100,"lofi":100,"pop":100,"indie":100,"folk":100,"backsound":100,"hiphop":100,"lofihop":27,"trap":26})
        self.assertEqual(len(rows), 853)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "observed.sqlite"
            stats = os.build(ROOT, db)
            self.assertEqual(stats["metadata_candidates"], 853)
            self.assertEqual(stats["rights_reviewed_tracks"], 0)
            self.assertEqual(stats["lyrics"], 0)
            self.assertEqual(len(os.search(db, "backsound", limit=100)), 100)
            self.assertTrue(os.search(db, "trap"))
            self.assertEqual(stats["annotated_clips"], 517)
            self.assertEqual(stats["track_metadata"], 203)
            self.assertEqual(stats["curated_track_candidates"], 95)
            self.assertEqual(stats["disclosed_ai_track_candidates"], 8)
            self.assertEqual(len(os.search(db, "lofi", limit=100)), 100)
            self.assertEqual(sum(r["metadata_origin"] == "creator_catalog_disclosed_suno_v5" for r in os.search(db, "lofihop", limit=100)), 8)
            self.assertEqual(stats["fma_album_candidates"], 30)
            trap = os.search(db, "trap", limit=100)
            clips = [r for r in trap if "youtube_id" in r]
            albums = [r for r in trap if r.get("metadata_origin") == "fma_album_catalog"]
            self.assertEqual(len(clips), 15)
            self.assertEqual(len(albums), 11)
            self.assertTrue(all(r["metadata_license"] == "CC-BY-SA-4.0" for r in clips))
            self.assertTrue(all(r["reported_license"] == "CC0-1.0" and
                                r["rights_status"] == "album_reports_cc0_track_review_pending"
                                for r in albums))
            self.assertTrue(os.search(db, "jazz", "jazz"))
