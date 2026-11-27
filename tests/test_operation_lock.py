import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from yue2_music_director import lock_status, operation_lock as ol


class OwnedLockTests(unittest.TestCase):
    def test_active_owner_and_exclusive_acquisition(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / ".active"
            with ol.lock(marker, context={"root": "results/job"}):
                self.assertEqual(ol.inspect(marker)["status"], "active_owner")
                with self.assertRaises(FileExistsError):
                    with ol.lock(marker):
                        self.fail("second owner")
                with self.assertRaises(ValueError):
                    ol.recover(marker, ol.inspect(marker)["marker_sha256"],
                               Path(tmp) / "receipts", confirm=True)
            self.assertEqual(ol.inspect(marker)["status"], "absent")

    def test_dead_process_recovery_archives_only_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            job = repo / "results/autonomous/test-job"
            job.mkdir(parents=True)
            journal = job / "journal_song.json"
            journal.write_text('{"state":"SUBMITTED"}', encoding="utf-8")
            marker = repo / lock_status.LOCKS["autonomous"]
            script = ("import os,sys; from pathlib import Path; "
                      "from yue2_music_director.operation_lock import lock; "
                      "ctx=lock(Path(sys.argv[1]),context={'root':'results/autonomous/test-job'}); "
                      "ctx.__enter__(); os._exit(0)")
            subprocess.run([sys.executable, "-c", script, str(marker)], check=True, timeout=20)
            raw = marker.read_bytes()
            before = journal.read_bytes()
            status = lock_status.inspect(repo, "autonomous")
            self.assertEqual(status["status"], "stale_owner")
            self.assertEqual(status["journals"]["status"], "inspected")
            self.assertEqual(status["journals"]["entries"][0]["state"], "SUBMITTED")
            sha = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError):
                lock_status.recover(repo, "autonomous", sha)
            with self.assertRaises(ValueError):
                lock_status.recover(repo, "autonomous", "wrong", confirm=True)
            receipt = lock_status.recover(repo, "autonomous", sha, confirm=True)
            self.assertEqual((receipt / "original-marker.json").read_bytes(), raw)
            self.assertFalse(json.loads((receipt / "attempt.json").read_bytes())["journal_replay_authorized"])
            self.assertTrue((receipt / "completed.json").exists())
            self.assertEqual(journal.read_bytes(), before)
            self.assertFalse(marker.exists())
            with ol.lock(marker):
                self.assertTrue(marker.exists())

    def test_legacy_unknown_and_replaced_markers_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / ".active"
            marker.touch()
            self.assertEqual(ol.inspect(marker)["status"], "unverified")
            with self.assertRaises(ValueError):
                ol.recover(marker, hashlib.sha256(b"").hexdigest(),
                           Path(tmp) / "receipts", confirm=True)
            marker.unlink()
            with self.assertRaisesRegex(ValueError, "ownership changed"):
                with ol.lock(marker):
                    with patch.object(ol, "process_birth", return_value=("unknown", None)):
                        self.assertEqual(ol.inspect(marker)["status"], "unverified")
                    marker.write_bytes(b"replacement")
            self.assertEqual(marker.read_bytes(), b"replacement")

    def test_pid_reuse_is_not_the_original_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / ".active"
            with ol.lock(marker):
                with patch.object(ol, "process_birth", return_value=("present", "different-birth")):
                    self.assertEqual(ol.inspect(marker)["status"], "stale_owner")


    def test_release_manifest_status_is_inspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp).resolve()
            root=repo/"results/release-delivery/one/one"
            root.mkdir(parents=True)
            (root/"delivery.json").write_text('{"status":"partial_missing_timing"}',encoding="utf-8")
            marker=repo/lock_status.LOCKS["release-delivery"]
            with ol.lock(marker,context={"root":root.relative_to(repo).as_posix()}):
                result=lock_status.inspect(repo,"release-delivery")
                self.assertEqual(result["journals"]["entries"][0]["state"],"partial_missing_timing")


if __name__ == "__main__":
    unittest.main()
