import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from yue2_music_director import ending_audit as ea


class EndingAuditTests(unittest.TestCase):
    def test_live_regression_near_cap(self):
        result=ea.cap_screen(195,194.998667)
        self.assertTrue(result["near_or_over_cap"])
        self.assertEqual(result["remaining_seconds"],0.001333)
        self.assertFalse(ea.cap_screen(195,188.478667)["near_or_over_cap"])

    def test_invalid_duration(self):
        for cap,actual in ((195,float("nan")),(0,1),(195,-1),(True,1)):
            with self.assertRaises(ValueError):
                ea.cap_screen(cap,actual)

    def test_invalid_job_no_file_read(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ea.nd,"read") as read:
            with self.assertRaises(ValueError):
                ea.inspect(Path(tmp),"../private","unused")
            read.assert_not_called()

    def test_retained_identity_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ea.nd,"read",side_effect=[{"job":"different"},{},{},{}]), patch.object(ea.nd,"load_brief",return_value={}), patch.object(ea.ld,"verify_take",return_value={}), patch.object(ea.ld,"retained_packet") as packet:
            with self.assertRaises(ValueError):
                ea.inspect(Path(tmp),"one","unused")
            packet.assert_not_called()

class NativeCompletionTests(unittest.TestCase):
    def test_native_length_and_memory_block_provisional(self):
        from yue2_music_director.native_completion import inspect_completion, blocks_provisional
        for reason in ("length","memory"):
            value=inspect_completion({"id":"s","metadata":{"job_id":"j"},"cut_short":reason,
                                      "replay_request":{"truncated":True}},"s","j")
            self.assertEqual(value["cut_short"],reason)
            self.assertTrue(blocks_provisional(value))

    def test_missing_metadata_not_proof_of_completion(self):
        from yue2_music_director.native_completion import inspect_completion, blocks_provisional
        song={"id":"s","metadata":{"job_id":"j"}}
        self.assertTrue(blocks_provisional(inspect_completion(song,"s","j")))
        self.assertFalse(blocks_provisional(inspect_completion({**song,"replay_request":{"truncated":False}},"s","j")))
        self.assertTrue(blocks_provisional(inspect_completion({**song,"replay_request":{"truncated":True}},"s","j")))
        with self.assertRaises(ValueError):
            inspect_completion(song,"other","j")
