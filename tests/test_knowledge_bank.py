import json
from pathlib import Path
import shutil
import tempfile
import unittest
from yue2_music_director import knowledge_bank as kb

ROOT = Path(__file__).resolve().parents[1] / "data" / "knowledge_bank"


class KnowledgeBankTest(unittest.TestCase):
    def test_real_bundled_data_and_offline_retrieval(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "bank.sqlite"
            stats = kb.build(ROOT, db)
            self.assertEqual(stats["unique_works"], 3)
            self.assertEqual(stats["languages"], {"de": 3})
            hits = kb.retrieve(db, "Schubert", "composer")
            self.assertEqual(len(hits), 3)
            self.assertTrue(all(h["features"]["lyric_bearing_notes"] > 0 for h in hits))
            self.assertTrue(kb.retrieve(db, "Schnee", "lyricist"))
            self.assertEqual(kb.retrieve(db, "zzzznonexistent", "lyricist"), [])
            self.assertNotIn("lyrics", hits[0])
            self.assertEqual(kb.build(ROOT, db), stats)

    def test_rejected_manifest_preserves_existing_database(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            shutil.copytree(ROOT, root)
            db = Path(temp) / "bank.sqlite"
            kb.build(root, db)
            before = db.read_bytes()
            path = root / "manifest.json"
            original = json.loads(path.read_text(encoding="utf-8"))
            for mode in ("rights", "duplicate", "checksum"):
                manifest = json.loads(json.dumps(original))
                if mode == "rights":
                    manifest["works"][0]["rights"] = "unknown"
                elif mode == "duplicate":
                    manifest["works"].append(manifest["works"][0])
                else:
                    manifest["works"][0]["assets"]["lyrics"]["git_blob_sha"] = "0" * 40
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(ValueError):
                    kb.build(root, db)
                self.assertEqual(db.read_bytes(), before)
            with self.assertRaises(ValueError):
                kb.retrieve(db, "", "lyricist")
