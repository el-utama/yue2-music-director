import io
from pathlib import Path
import sys
import tempfile
import unittest

from yue2_music_director.logged_command import run


class LoggedCommandTests(unittest.TestCase):
    def test_transcript_and_failure_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp)/"results/eval-output.txt"
            console = io.StringIO()
            rc = run(log, [sys.executable,"-c",
                           "import sys; print('progress'); print('failure', file=sys.stderr); sys.exit(7)"],
                     console=console)
            self.assertEqual(rc,7)
            saved = log.read_text(encoding="utf-8")
            for line in ("progress","failure","Exit code: 7"):
                self.assertIn(line,saved)
                self.assertIn(line,console.getvalue())

    def test_missing_executable_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root/"eval-output.txt"
            self.assertEqual(run(log,[str(root/"missing-executable")],io.StringIO()),2)
            self.assertIn("ERROR:",log.read_text(encoding="utf-8"))
