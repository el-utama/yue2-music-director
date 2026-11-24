import json
import tempfile
import unittest
from pathlib import Path
from yue2_music_director.experiments import prepare, submit, reconcile, status

ABC='X:1\nT:test\nM:2/4\nL:1/16\nK:Bb\n% verse\nV: Vocal\n"Bb"z2B,F2F2F-|"Bb"F2DD3CC-|"Eb"CB,z6|"Eb"z8|\nV: Ins\nZ4|\n'
LYRICS='[Verse 1]\nYou left me waiting\n'


class FakeClient:
    submitted=0
    def __init__(self,url): self.url=url
    def connect(self): return self
    def tools(self):
        names=('song_create','song_defaults','studio_status','studio_capabilities')
        req=('music_source','style','lyrics','abc','abc_continue','lyric_timing',
             'seed','lm_seed','lm_batch_size','synth_batch_size')
        return [{'name':n,'inputSchema':{'properties':{k:{} for k in req}}} if n=='song_create' else {'name':n} for n in names]
    def call(self,name,args):
        if name=='song_create':
            FakeClient.submitted+=1
            return {'structuredContent':{'id':'job-1','status':'queued','phase':'music','tracks_asked':1}}
        return {'structuredContent': {'ready':True}}


class ExperimentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d=Path(self.tmp.name)
        self.root=d/'experiment'
        self.a=d/'A.abc';self.b=d/'B.abc';self.lyr=d/'lyrics.txt';self.style=d/'style.txt'
        self.a.write_text(ABC);self.b.write_text(ABC.replace('B,F2F2F-','B,E2F2F-'))
        self.lyr.write_text(LYRICS);self.style.write_text('Indie Folk 74 BPM')
        FakeClient.submitted=0

    def test_prepare_offline(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        self.assertEqual(FakeClient.submitted,0)
        self.assertTrue((self.root/'manifest.json').exists())

    def test_refuse_duplicate(self):
        prepare(self.a,self.b,self.lyr,self.style,self.root)
        r=submit(self.root,'A','http://localhost:8791/mcp',True,client_factory=FakeClient)
        self.assertEqual(r['job_id'],'job-1')
        self.assertEqual(FakeClient.submitted,1)
        with self.assertRaises(ValueError):
            submit(self.root,'A','http://localhost:8791/mcp',True,client_factory=FakeClient)
        self.assertEqual(FakeClient.submitted,1)

    def test_reject_candidate_chorus_mutation(self):
        changed=ABC.replace('"Bb"z2BBBd2d-','"Bb"z2BABd2d-')
        self.assertNotEqual(changed,ABC)
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


if __name__=='__main__':
    unittest.main()
