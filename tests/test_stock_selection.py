import unittest
from unittest.mock import Mock, patch
from yue2_music_director.stock_selection import select_stock
from yue2_music_director.native_recognition import BUSY_KEYS

class StockSelectionTests(unittest.TestCase):
    def setUp(self):
        self.client=Mock()
        self.tools={"models_own_select":{"properties":{"file":{"type":"string"}}}}
        self.override="custom-Q6_K.gguf"
        self.status={**dict.fromkeys(BUSY_KEYS),"own_model":self.override}
        self.models={"selected_profile_id":"balanced","selected_component_ids":None,
                     "installed_components":["backbone-q6","vae-f32"],"active":None,
                     "own_model":self.override,"engine_ready":True,"selection_matches_engine":True,
                     "ready":True,"preset":None}
        self.own={"selected":self.override,"missing":False,"download":None}
        self.stock={**self.models,"own_model":None}
        self.stock_own={**self.own,"selected":None}

    def replies(self,models):
        def call(name,args):
            if name=="studio_status":
                return self.status
            if name=="models_status":
                return next(models)
            if name=="models_own_select":
                self.assertEqual(args,{"file":""})
                return {}
            raise AssertionError(name)
        self.client.call.side_effect=call

    def test_switch_once_and_wait_for_actual_match(self):
        self.replies(iter([self.models,{**self.stock,"selection_matches_engine":False},self.stock]))
        with patch("yue2_music_director.stock_selection.read_own_model",side_effect=[self.own,self.stock_own,self.stock_own]):
            select_stock(self.client,self.tools,max_waits=2,sleep=lambda _:None)
        self.assertEqual(sum(c.args[0]=="models_own_select" for c in self.client.call.call_args_list),1)

    def test_completed_download_receipt_is_not_active_work(self):
        self.models["active"]={"status":"completed"}
        self.replies(iter([self.models,self.stock]))
        with patch("yue2_music_director.stock_selection.read_own_model",side_effect=[self.own,self.stock_own]):
            select_stock(self.client,self.tools,max_waits=0)
        self.assertEqual(sum(c.args[0]=="models_own_select" for c in self.client.call.call_args_list),1)

    def test_downloading_blocks_before_model_write(self):
        self.models["active"]={"status":"downloading"}
        self.replies(iter([self.models]))
        with patch("yue2_music_director.stock_selection.read_own_model",return_value=self.own):
            with self.assertRaisesRegex(ValueError,"no_download"):
                select_stock(self.client,self.tools)
        self.assertFalse(any(c.args[0]=="models_own_select" for c in self.client.call.call_args_list))

    def test_conflict_blocks_before_write(self):
        self.replies(iter([self.models]))
        with patch("yue2_music_director.stock_selection.read_own_model",return_value=self.stock_own):
            with self.assertRaisesRegex(ValueError,"disagree"):
                select_stock(self.client,self.tools)
        self.assertFalse(any(c.args[0]=="models_own_select" for c in self.client.call.call_args_list))

    def test_already_stock_does_not_write(self):
        self.status["own_model"]=None
        self.replies(iter([self.stock,self.stock]))
        with patch("yue2_music_director.stock_selection.read_own_model",return_value=self.stock_own):
            select_stock(self.client,self.tools)
        self.assertFalse(any(c.args[0]=="models_own_select" for c in self.client.call.call_args_list))

    def test_not_ready_stops_without_repeated_switch(self):
        self.replies(iter([self.models,{**self.stock,"engine_ready":False}]))
        with patch("yue2_music_director.stock_selection.read_own_model",side_effect=[self.own,self.stock_own]):
            with self.assertRaisesRegex(ValueError,"bounded wait"):
                select_stock(self.client,self.tools,max_waits=0)
        self.assertEqual(sum(c.args[0]=="models_own_select" for c in self.client.call.call_args_list),1)
