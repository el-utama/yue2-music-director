import math
import subprocess
import zlib
import shutil
import struct
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from yue2_music_director.instrument_dynamics import envelope, apply_delta, process, _decode, residual_budget


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
            # Simulate a modest reconstruction residual without altering the source.
            scaled=[root/"scaled_ins.wav",root/"scaled_voice.wav"]
            for source,target in zip(paths[1:],scaled):
                subprocess.run([shutil.which("ffmpeg"),"-nostdin","-v","error","-i",str(source),
                                "-af","volume=0.94","-c:a","pcm_f32le",str(target)],
                               check=True,capture_output=True)
            moderate=process(paths[0],*scaled,root/"moderate")
            self.assertEqual(moderate["status"],"candidate_created")
            self.assertTrue(-30<moderate["reconstruction_residual_db"]<-20)
            self.assertTrue(0.25<moderate["effective_max_attenuation_db"]<2)
            self.assertTrue((root/"moderate/candidate.flac").is_file())
            with self.assertRaises(ValueError):
                process(paths[0],paths[2],paths[1],root/"out")
            # Incorrect mix/stem identity must not produce a candidate.
            bad=root/"bad.wav"
            bad.write_bytes(paths[2].read_bytes())
            blocked=process(paths[0],bad,paths[2],root/"invalid")
            self.assertEqual(blocked["status"],"blocked_reconstruction")
            self.assertFalse((root/"invalid/candidate.flac").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
    def test_flac_with_attached_picture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            # A valid 1x1 RGB PNG without image library dependencies.
            def chunk(kind, data):
                return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data))
            picture=root/"cover.png"
            picture.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,2,0,0,0))
                +chunk(b"IDAT",zlib.compress(b"\x00\x40\x80\xc0"))+chunk(b"IEND",b""))
            wav=root/"input.wav"
            with wave.open(str(wav),"wb") as f:
                f.setparams((1,2,44100,0,"NONE","not compressed"))
                f.writeframes(struct.pack("<h",1000)*44100)
            flac=root/"covered.flac"
            ffmpeg,ffprobe=shutil.which("ffmpeg"),shutil.which("ffprobe")
            subprocess.run([ffmpeg,"-nostdin","-v","error","-i",str(wav),"-i",str(picture),
                            "-map","0:a","-map","1:v","-c:a","flac","-c:v","copy",
                            "-disposition:v:0","attached_pic",str(flac)],check=True,capture_output=True)
            probe=subprocess.run([ffprobe,"-v","error","-show_entries","stream=codec_type",
                                  "-of","csv=p=0",str(flac)],check=True,capture_output=True,text=True)
            self.assertEqual(sorted(probe.stdout.split()),["audio","video"])
            target=root/"decoded.f32"
            self.assertEqual(_decode(flac,target,ffmpeg,ffprobe),(44100,1))
            self.assertEqual(target.stat().st_size,44100*4)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
    def test_roformer_rate_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ffmpeg=shutil.which("ffmpeg")
            rate=48000
            paths=[root/(name+".wav") for name in ("mix","instrumental48","vocals48")]
            buffers=[bytearray() for _ in paths]
            # Non-integer conversion length, stereo, alternating attacks.
            for i in range(rate*5+1):
                phase=(i//480)%25
                amp=0.06 if (i//12000)%3==0 else 0.24
                ins=round(amp*32767*math.sin(i*2*math.pi*220/rate)) if 5<=phase<13 else 0
                vocal=round(0.025*32767*math.sin(i*2*math.pi*440/rate))
                for buf,value in zip(buffers,(ins+vocal,ins,vocal)):
                    buf.extend(struct.pack("<hh",value,value))
            for p,data in zip(paths,buffers):
                with wave.open(str(p),"wb") as f:
                    f.setparams((2,2,rate,0,"NONE","not compressed"))
                    f.writeframes(data)
            stems=[root/"instrumental44.wav",root/"vocals44.wav"]
            for p,q in zip(paths[1:],stems):
                subprocess.run([ffmpeg,"-nostdin","-v","error","-i",str(p),
                                "-ar","44100","-c:a","pcm_f32le",str(q)],check=True,capture_output=True)
            report=process(paths[0],*stems,root/"out")
            self.assertEqual(report["status"],"candidate_created")
            self.assertEqual(report["source_sample_rates_hz"],[48000,44100,44100])
            self.assertEqual(report["sample_rate_hz"],48000)
            self.assertEqual(report["frames"],rate*5+1)
            self.assertTrue(all(s["resampled"] for s in report["stem_alignment"]))
            self.assertLessEqual(report["reconstruction_residual_db"],-30)
            self.assertTrue((root/"out/candidate.flac").is_file())
            shorter=root/"short.wav"
            subprocess.run([ffmpeg,"-nostdin","-v","error","-i",str(stems[0]),
                            "-t","4.9","-c:a","pcm_f32le",str(shorter)],check=True,capture_output=True)
            with self.assertRaisesRegex(ValueError,"Stem duration differs"):
                process(paths[0],shorter,stems[1],root/"bad")
            self.assertFalse((root/"bad").exists())

    def test_adaptive_residual_budget(self):
        self.assertAlmostEqual(residual_budget(-60,2),2)
        budget=residual_budget(-24.57,2)
        self.assertGreater(budget,0.25)
        self.assertLess(budget,2)
        self.assertLessEqual((1-10**(-budget/20))*10**(-24.57/20),0.010000001)
        self.assertEqual(residual_budget(-19.99,2),0)
        self.assertEqual(residual_budget(float("nan"),2),0)
