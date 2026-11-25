import json
import tempfile
import unittest
from unittest.mock import patch
from email.message import Message
from pathlib import Path
from yue2_music_director.experiments import prepare, submit, reconcile, status, confirm_stock_backbone

ABC='X:1\nT:test\nM:2/4\nL:1/16\nK:Bb\n% verse\nV: Vocal\n"Bb"z2B,F2F2F-|"Bb"F2DD3CC-|"Eb"CB,z6|"Eb"z8|\nV: Ins\nZ4|\n'
LYRICS='[Verse 1]\nYou left me waiting\n'


class FakeClient:
    submitted=0
    own_model=None
    profile='balanced'
    cache_q8=True
    max_seq=8192
    def __init__(self,url): self.url=url
    def connect(self): return self
    def tools(self):
        names=('song_create','song_defaults','studio_status','studio_capabilities','models_status','engine_options_get')
        req=('music_source','style','lyrics','abc','abc_continue','lyric_timing',
             'seed','lm_seed','lm_batch_size','synth_batch_size','adapters','companion_scale')
        return [{'name':n,'inputSchema':{'properties':{k:{} for k in req}}} if n=='song_create' else {'name':n} for n in names]
    def call(self,name,args):
        if name=='song_create':
            FakeClient.submitted+=1
            return {'structuredContent':{'id':'job-1','status':'queued','phase':'music','tracks_asked':1}}
        effective={'flash_attention':True,'max_seq':FakeClient.max_seq,'max_seq_reason':'full','nar_chunk_seconds':None}
        if name=='studio_status':
            from yue2_music_director.native_recognition import BUSY_KEYS
            return {'structuredContent':{**dict.fromkeys(BUSY_KEYS), 'own_model':FakeClient.own_model,'engine':effective}}
        if name=='models_status':
            return {'structuredContent':{'ready':True,'engine_ready':True,'selected_profile_id':FakeClient.profile,
                'selected_component_ids':None,'active':None,'preset':None,'engine_id':'yue2-cpp',
                'installed_components':['backbone-q6','vae-f32']}}
        if name=='engine_options_get':
            return {'structuredContent':{'options':{'backend':'cuda','kv_cache':'q8','extra_args':''},
                 'in_effect':effective,'kv_cache_now':{'q8':FakeClient.cache_q8}}}
        return {'structuredContent': {'ready':True}}


class ExperimentsTests(unittest.TestCase):
    def setUp(self):
        opener=patch("yue2_music_director.experiments.build_opener")
        self.opener=opener.start()
        self.addCleanup(opener.stop)
        self.response=self.opener.return_value.open.return_value.__enter__.return_value
        headers=Message()
        headers["Content-Type"]="application/json"
        self.response.headers=headers
        self.response.read.return_value=b'{"selected":null,"missing":false,"download":null}'
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d=Path(self.tmp.name)
        self.root=d/'experiment'
        self.a=d/'A.abc';self.b=d/'B.abc';self.lyr=d/'lyrics.txt';self.style=d/'style.txt'
        self.a.write_text(ABC);self.b.write_text(ABC.replace('B,F2F2F-','B,E2F2F-'))
        self.lyr.write_text(LYRICS);self.style.write_text('Indie Folk 74 BPM')
        FakeClient.submitted=0
        FakeClient.own_model=None
        FakeClient.profile='balanced'
        FakeClient.cache_q8=True
        FakeClient.max_seq=8192

    def test_prepare_offline(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        self.assertEqual(FakeClient.submitted,0)
        self.assertTrue((self.root/'manifest.json').exists())
        request=json.loads((self.root/'A_song_create.json').read_text())
        self.assertEqual(request['adapters'],[])
        self.assertEqual(request['companion_scale'],0)

    def test_refuse_duplicate(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        r=submit(self.root,'A','http://localhost:8791/mcp',True,client_factory=FakeClient)
        self.assertEqual(r['job_id'],'job-1')
        self.assertEqual(FakeClient.submitted,1)
        with self.assertRaises(ValueError):
            submit(self.root,'A','http://localhost:8791/mcp',True,client_factory=FakeClient)
        self.assertEqual(FakeClient.submitted,1)

    def test_reject_candidate_chorus_mutation(self):
        extended=ABC+'% chorus\nV: Vocal\n"Bb"B8|\nV: Ins\nZ|\n'
        self.a.write_text(extended)
        self.lyr.write_text(LYRICS+'[Chorus]\nI will keep my promise\n')
        changed=extended.replace('"Bb"B8|','"Bb"D8|')
        self.assertNotEqual(changed,extended)
        self.b.write_text(changed)
        with self.assertRaises(ValueError):
            prepare(self.a,self.b,self.lyr,self.style,self.root)

    def test_reject_candidate_instrument_mutation(self):
        changed=ABC.replace('V: Ins\nZ4|','V: Ins\nF8|Z3|')
        self.assertNotEqual(changed,ABC)
        self.b.write_text(changed)
        with self.assertRaises(ValueError):
            prepare(self.a,self.b,self.lyr,self.style,self.root)

    def test_recover_and_status_offline(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        submit(self.root,'A','http://localhost:8791/mcp',True,client_factory=FakeClient)
        reconcile(self.root,'A',confirm_complete=True)
        self.assertEqual(status(self.root,'A')['verification'],'user')

    def test_B_must_wait(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        with self.assertRaises((ValueError,FileNotFoundError)):
            submit(self.root,'B','http://localhost:8791/mcp',True,True,client_factory=FakeClient)


    def test_wrong_backbone_or_cache_blocks_before_submission(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        for field,value in [('own_model','community.gguf'),('profile','quality-q8'),('cache_q8',False)]:
            original=getattr(FakeClient,field)
            setattr(FakeClient,field,value)
            try:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    submit(self.root,'A','http://localhost:8791/mcp',True,client_factory=FakeClient)
                self.assertFalse((self.root/'journal_A.json').exists())
            finally:
                setattr(FakeClient,field,original)
        self.assertEqual(FakeClient.submitted,0)

    def test_reference_drift_blocks_second_arm(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        submit(self.root,'A','http://localhost:8791/mcp',True,client_factory=FakeClient)
        reconcile(self.root,'A',confirm_complete=True)
        FakeClient.max_seq=4096
        with self.assertRaises(ValueError):
            submit(self.root,'B','http://localhost:8791/mcp',True,True,client_factory=FakeClient)
        self.assertEqual(FakeClient.submitted,1)
        self.assertFalse((self.root/'journal_B.json').exists())


    def test_missing_summary_uses_native_authoritative_selection(self):
        client=FakeClient("http://127.0.0.1:8791/mcp")
        self.assertEqual(confirm_stock_backbone(client,{}),"native_selection")
        request=self.opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url,"http://127.0.0.1:8791/setup/own-model")
        self.assertEqual(request.get_method(),"GET")

    def test_native_override_or_unknown_never_passes(self):
        client=FakeClient("http://127.0.0.1:8791/mcp")
        for payload in (b'{"selected":"custom.gguf","missing":false,"download":null}',
                        b'{"missing":false,"download":null}',
                        b'{"selected":null,"missing":false,"download":{}}'):
            self.response.read.return_value=payload
            with self.assertRaises(ValueError):
                confirm_stock_backbone(client,{"own_model":None})
        with self.assertRaises(ValueError):
            confirm_stock_backbone(client,{"own_model":"custom.gguf"})
        with self.assertRaises(ValueError):
            confirm_stock_backbone(FakeClient("http://example.com/mcp"),{})


    def test_nonnull_summary_still_reads_native_selection(self):
        client=FakeClient("http://127.0.0.1:8791/mcp")
        with self.assertRaisesRegex(ValueError,"conflicts with native null"):
            confirm_stock_backbone(client,{"own_model":"custom.gguf"})
        self.opener.return_value.open.assert_called_once()
        self.response.read.return_value=b'{"selected":"custom.gguf","missing":false,"download":null}'
        with self.assertRaisesRegex(ValueError,"Native endpoint reports"):
            confirm_stock_backbone(client,{"own_model":"custom.gguf"})

    def test_models_status_conflict_is_not_ignored(self):
        client=FakeClient("http://127.0.0.1:8791/mcp")
        with self.assertRaisesRegex(ValueError,"Models status conflicts"):
            confirm_stock_backbone(client,{"own_model":None},{"own_model":"custom.gguf"})


if __name__=='__main__':
    unittest.main()
