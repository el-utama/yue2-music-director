import unittest
from unittest.mock import Mock

from yue2_music_director.native_recognition import BUSY_KEYS
from yue2_music_director.studio_idle import wait_for_idle, assert_idle


class IdleBarrierTests(unittest.TestCase):
    def setUp(self):
        self.now=0
        self.idle=dict.fromkeys(BUSY_KEYS)
        self.busy={**self.idle,"covers_and_karaoke":[{"state":"running"}]}
        self.client=Mock()

    def clock(self):
        return self.now

    def sleep(self,seconds):
        self.now+=seconds

    def test_late_karaoke_resets_idle_window(self):
        samples=iter([self.idle,self.busy,self.idle,self.idle,self.idle])
        def call(name,args):
            if name=="studio_status":
                return next(samples)
            self.assertEqual(name,"studio_wait")
            self.assertEqual(args["until"],"idle")
            return {"done":True}
        self.client.call.side_effect=call
        result=wait_for_idle(self.client,"ASR",clock=self.clock,sleep=self.sleep)
        self.assertEqual(result,self.idle)
        self.assertEqual(self.now,20)
        self.assertEqual([x.args[0] for x in self.client.call.call_args_list],
                         ["studio_status","studio_status","studio_wait",
                          "studio_status","studio_status","studio_status"])

    def test_native_done_does_not_override_busy(self):
        self.client.call.side_effect=lambda name,args: self.busy if name=="studio_status" else {"done":True}
        with self.assertRaisesRegex(ValueError,"no next operation submitted"):
            wait_for_idle(self.client,"synthesis",max_seconds=12,clock=self.clock,sleep=self.sleep)
        self.assertEqual(self.now,12)
        self.assertTrue(all(c.args[0] in ("studio_wait","studio_status") for c in self.client.call.call_args_list))

    def test_unknown_schema_fails_closed(self):
        self.client.call.return_value={}
        with self.assertRaisesRegex(ValueError,"busy-state schema"):
            wait_for_idle(self.client,"synthesis",clock=self.clock,sleep=self.sleep)

    def test_final_check_detects_new_activity(self):
        self.client.call.return_value=self.busy
        with self.assertRaisesRegex(ValueError,"became busy"):
            assert_idle(self.client)
        self.client.call.assert_called_once_with("studio_status",{})
