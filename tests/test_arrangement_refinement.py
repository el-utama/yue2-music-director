import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from yue2_music_director import arrangement_refinement as ar
from yue2_music_director import listening_director as ld


class ArrangementRefinementTests(unittest.TestCase):
    def test_only_style_request_differs(self):
        repo = Path(__file__).resolve().parents[1]
        brief, intent = ld.inputs(repo, True)
        candidate = ar.revised_brief(brief)
        a, b = ar.nd.request_for(brief), ar.nd.request_for(candidate)
        self.assertEqual({k for k in a if a[k] != b[k]}, {"style"})
        self.assertLessEqual(len(candidate["style"]), 2000)
        self.assertEqual(ld.artist_run.route_for(intent), "direct_native")

    def test_plan_is_offline(self):
        repo = Path(__file__).resolve().parents[1]
        with patch.object(ar, "baseline") as baseline, patch.object(ar.nd, "execute") as execute:
            self.assertEqual(ar.launch_revision(repo, "unused"), 0)
            baseline.assert_not_called()
            execute.assert_not_called()

    def test_missing_baseline_blocks_before_generation(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ld, "inputs", return_value=ld.inputs(repo, True)), \
                 patch.object(ar.nd, "execute") as execute:
                with self.assertRaises(FileNotFoundError):
                    ar.launch_revision(Path(tmp), "unused", confirm=True)
                execute.assert_not_called()
