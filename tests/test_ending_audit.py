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

    def test_replay_classifier_matches_studio(self):
        from yue2_music_director.native_completion import replay_cut_reason
        self.assertEqual(replay_cut_reason({"truncated":True,"duration":195,"semantic_tokens":",".join(["1"]*4875)}),"length")
        self.assertEqual(replay_cut_reason({"truncated":True,"duration":240,"semantic_tokens":",".join(["1"]*3537)}),"memory")
        self.assertIsNone(replay_cut_reason({"truncated":True}))

    def test_malformed_completion_evidence_blocks_provisional(self):
        from yue2_music_director.native_completion import inspect_completion, blocks_provisional
        song={"id":"s","metadata":{"job_id":"j"}}
        for replay in ({"truncated":"true","semantic_tokens":"1,2"},
                       {"truncated":None,"semantic_tokens":"1,2"},
                       {"truncated":0,"semantic_tokens":"1,2"},
                       {"semantic_tokens":True},{"semantic_tokens":"bad"},
                       {"semantic_tokens":"1,,2"},{"semantic_tokens":"32768"},
                       {"truncated":False,"semantic_tokens":"-1"}):
            with self.subTest(replay=replay):
                result=inspect_completion({**song,"replay_request":replay},"s","j")
                self.assertEqual(result["status"],"unknown")
                self.assertTrue(blocks_provisional(result))
        # Sparse replay without a marker remains compatible with the pinned engine.
        result=inspect_completion({**song,"replay_request":{"semantic_tokens":"0, 32767,12"}},"s","j")
        self.assertEqual(result["status"],"not_flagged")
        self.assertFalse(result["musical_completion_verified"])
        self.assertFalse(blocks_provisional(result))

    def test_invalid_stream_does_not_invent_cut_reason(self):
        from yue2_music_director.native_completion import replay_cut_reason, inspect_completion, blocks_provisional
        for tokens in ("not-a-code","1,,2","32768","9"*5000):
            replay={"truncated":True,"semantic_tokens":tokens}
            self.assertIsNone(replay_cut_reason(replay))
            result=inspect_completion({"id":"s","metadata":{"job_id":"j"},"replay_request":replay},"s","j")
            self.assertEqual(result["status"],"truncated_reason_unknown")
            self.assertTrue(blocks_provisional(result))
        self.assertEqual(replay_cut_reason({"truncated":True,"duration":1e308,"semantic_tokens":"1"}),"memory")
