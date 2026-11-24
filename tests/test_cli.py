import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from yue2_music_director.cli import main


ABC=('X:1\nT:test\nM:2/4\nL:1/16\nK:Bb\n% verse\n'
     'V: Vocal\n"Bb"z2B,F2F2F-|"Bb"F2DD3CC-|"Eb"CB,z6|"Eb"z8|\n'
     'V: Ins\nZ4|\n')
LYRICS='[Verse 1]\nYesterday you left the doorway\n'


class CLITests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.src=self.root/'song.abc'
        self.lyr=self.root/'lyrics.txt'
        self.src.write_text(ABC,encoding='utf-8')
        self.lyr.write_text(LYRICS,encoding='utf-8')

    def capture(self,args):
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf):
            rc=main(args)
        return rc,buf.getvalue()

    def test_audit_with_phrase_diagnostics(self):
        rc,output=self.capture(['audit',str(self.src),'--lyrics',str(self.lyr)])
        self.assertEqual(rc,0,output)
        data=json.loads(output)
        self.assertEqual(data['bars'],{'Vocal':4,'Ins':4})
        self.assertEqual(len(data['phrases']),1)

    def test_humanize_does_not_overwrite_source(self):
        original=self.src.read_bytes()
        out=self.root/'candidate.abc'
        rc,output=self.capture(['humanize',str(self.src),'--lyrics',str(self.lyr),
                                '--out',str(out),'--seed','42'])
        self.assertEqual(rc,0,output)
        self.assertTrue(out.exists())
        self.assertEqual(self.src.read_bytes(),original)

    def test_humanize_refuses_source_overwrite(self):
        rc,_=self.capture(['humanize',str(self.src),'--lyrics',str(self.lyr),
                           '--out',str(self.src)])
        self.assertEqual(rc,2)

    def test_studio_check_requires_url(self):
        import unittest.mock
        with unittest.mock.patch.dict('os.environ',{},clear=True):
            rc,_=self.capture(['studio-check'])
        self.assertEqual(rc,2)


if __name__=='__main__':
    unittest.main()
