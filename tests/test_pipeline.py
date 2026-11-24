import json
import tempfile
import unittest
from pathlib import Path
from yue2_music_director.pipeline import run

ABC=('X:1\nT:Demo\nM:2/4\nL:1/16\nK:Bb\n'
     '% verse\nV: Vocal\n"Bb"z2B,F2F2F-|"Bb"F2DD3CC-|"Eb"CB,z6|"Eb"z8|\n'
     'V: Ins\nZ4|\n'
     '% chorus\nV: Vocal\n"Bb"z2BBBd2d-|"F"dccc2B2B-|"Eb"Bz6z|"Eb"z8|\n'
     'V: Ins\nZ4|\n')
LYRICS='[Verse 1]\nYou are leaving\nNo one to stay\n[Chorus]\nI will let go\nI am still here\n'


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.score=root/'song.abc'
        self.lyrics=root/'lyrics.txt'
        self.style=root/'style.txt'
        self.out=root/'results'
        self.score.write_text(ABC)
        self.lyrics.write_text(LYRICS)
        self.style.write_text('Indie Folk 74 BPM')

    def test_offline_run_prepares_a_b_without_audio(self):
        before=self.score.read_bytes()
        output=run(self.score,self.lyrics,self.out,style=self.style,seed=42)
        self.assertGreater(output['pitch_changes'],0)
        self.assertEqual(output['audio_jobs_created'],0)
        self.assertTrue((self.out/'ab'/'manifest.json').is_file())
        self.assertTrue((self.out/'candidate_pitch.abc').is_file())
        self.assertEqual(self.score.read_bytes(),before)

    def test_refuse_overwrite(self):
        run(self.score,self.lyrics,self.out,style=self.style)
        with self.assertRaises(ValueError):
            run(self.score,self.lyrics,self.out,style=self.style)

    def test_mismatch_stops_before_writing(self):
        self.lyrics.write_text('[Bridge]\nWrong section\n')
        with self.assertRaises(ValueError):
            run(self.score,self.lyrics,self.out)
        self.assertFalse(self.out.exists())

    def test_report_has_caveats(self):
        run(self.score,self.lyrics,self.out)
        data=json.loads((self.out/'score_report.json').read_text())
        self.assertTrue(data['warnings'])
        self.assertIn('humanization',data)
        self.assertEqual(len(data['sections']),2)


if __name__=='__main__':
    unittest.main()
