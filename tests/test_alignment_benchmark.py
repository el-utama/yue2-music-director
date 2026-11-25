import tempfile
import unittest
from pathlib import Path
from yue2_music_director.alignment_benchmark import compare, parse_htk, benchmark


class AlignmentBenchmarkTests(unittest.TestCase):
    def test_shared_boundaries_and_ms(self):
        a="0 1000000 a\n1000000 2000000 b"
        b="0 1200000 a\n1200000 2200000 b"
        result=compare(a,b)
        self.assertEqual(result["status"],"boundary_metrics_available")
        stats=result["boundary_metrics"]
        self.assertEqual(stats["boundary_count"],3)
        self.assertAlmostEqual(stats["mean_absolute_ms"],40/3)
        self.assertEqual(stats["p95_absolute_ms"],20)
        self.assertEqual(stats["within_20ms_fraction"],1)
        self.assertFalse(result["correction_allowed"])

    def test_mismatch_no_false_metrics(self):
        result=compare("0 1000000 a","0 1000000 b")
        self.assertEqual(result["status"],"sequence_mismatch")
        self.assertIsNone(result["boundary_metrics"])
        self.assertEqual(result["sequence_edit_distance"]["edits"],1)

    def test_invalid_intervals(self):
        for value in ("", "0 0 a","-1 20 a","0 600000001 a",
                      "0 20 a\n19 30 b","0 20 a 0.5","0.0 20 a"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                parse_htk(value)

    def test_file_report_no_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            audio=d/"excerpt.wav"
            audio.write_bytes(b"fixture")
            a=d/"ref.lab"
            b=d/"pred.lab"
            a.write_text("0 1000000 a",encoding="utf-8")
            b.write_text("0 1000000 a",encoding="utf-8")
            out=d/"report.json"
            result=benchmark(audio,a,b,out)
            self.assertEqual(result["alignment_calls"],0)
            self.assertFalse(result["audio_duration_verified"])
            self.assertFalse(result["reference_provenance_verified"])
            self.assertTrue(out.is_file())
            with self.assertRaises(ValueError):
                benchmark(audio,a,b,out)
