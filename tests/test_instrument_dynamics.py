import math
import shutil
import struct
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from yue2_music_director.instrument_dynamics import envelope, apply_delta, process


class DynamicsTests(unittest.TestCase):
    def test_envelope(self):
        energies = [1e-8]*500
        for n,i in enumerate(range(10,450,25)):
            energies[i:i+8] = [0.04 if n%3 else 0.004]*8
        gains,onsets,edited=envelope(energies)
        self.assertGreaterEqual(len(onsets),8)
        self.assertGreater(len(edited),0)
        self.assertTrue(all(-2<=g<=0 for g in gains))
        self.assertEqual(envelope([0.01]*500)[2],[])

    def test_delta_preserves_original_when_inactive(self):
        mix=array("f",[0.1,-0.2,0.3,-0.4])
        stem=array("f",[0.05,-0.1,0.1,-0.2])
        self.assertEqual(apply_delta(mix,stem,0,0,2),mix)
        out=apply_delta(mix,stem,-2,-2,2)
        for x,y,z in zip(mix,stem,out):
            self.assertAlmostEqual(z,x+(10**(-2/20)-1)*y,places=6)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
    def test_offline_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            paths=[root/(name+".wav") for name in ("mix","instrumental","vocals")]
            buffers=[bytearray() for _ in paths]
            rate=44100
            for i in range(rate*5):
                block=i//(rate//100)
                phase=block%25
                amp=0.06 if (block//25)%3==0 else 0.24
                ins=round(amp*32767*math.sin(i*2*math.pi*220/rate)) if 5<=phase<13 else 0
                vocal=round(0.025*32767*math.sin(i*2*math.pi*440/rate))
                for buf,value in zip(buffers,(ins+vocal,ins,vocal)):
                    buf.extend(struct.pack("<h",value))
            for p,data in zip(paths,buffers):
                with wave.open(str(p),"wb") as f:
                    f.setparams((1,2,rate,0,"NONE","not compressed"))
                    f.writeframes(data)
            report=process(*paths,root/"out")
            self.assertEqual(report["status"],"candidate_created")
            self.assertTrue((root/"out/candidate.flac").is_file())
            self.assertGreater(report["attacks_edited"],0)
            self.assertLess(report["reconstruction_residual_db"],-30)
            self.assertEqual(report["audio_jobs_created"],0)
            self.assertFalse(report["naturalness_verified"])
            with self.assertRaises(ValueError):
                process(paths[0],paths[2],paths[1],root/"out")
            # Incorrect mix/stem identity must not produce a candidate.
            bad=root/"bad.wav"
            bad.write_bytes(paths[2].read_bytes())
            with self.assertRaisesRegex(ValueError,"reconstruct"):
                process(paths[0],bad,paths[2],root/"invalid")
            self.assertFalse((root/"invalid").exists())
