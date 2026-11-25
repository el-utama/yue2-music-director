import tempfile
import unittest
import wave
from pathlib import Path
from struct import pack
from yue2_music_director.alignment_reference import labels,prepare


class ReferenceTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(labels("0.000000 0.100000 aa\n0.1 0.2 b","seconds"),
                         labels("0 1000000 aa\n1000000 2000000 b","htk"))
        for value in ("0 0 a","0.2 0.1 a","0 0.2 a\n0.1 0.3 b","0 601 a","0 0.12345678 a"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                labels(value,"seconds")

    def test_exact_excerpt_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            audio=d/"source.wav"
            pcm=b"".join(pack("<h",i%1000) for i in range(8000))
            with wave.open(str(audio),"wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(8000)
                f.writeframes(pcm)
            annotation=d/"ref.txt"
            annotation.write_text("0 0.25 sil\n0.25 0.5 aa\n0.5 0.75 b\n0.75 1 sil",encoding="utf-8")
            out=d/"excerpt"
            result=prepare(audio,annotation,"seconds",2,3,out)
            self.assertEqual(result["source_start_frame"],2000)
            self.assertEqual(result["source_end_frame_exclusive"],6000)
            self.assertEqual(result["excerpt_duration_seconds"],0.5)
            with wave.open(str(out/"excerpt.wav"),"rb") as f:
                self.assertEqual(f.readframes(f.getnframes()),pcm[4000:12000])
            self.assertEqual((out/"reference.lab").read_text(),"0 2500000 aa\n2500000 5000000 b\n")
            self.assertEqual(result["alignment_calls"],0)
            self.assertFalse(result["correction_allowed"])
            self.assertTrue((out/"report.json").is_file())
            with self.assertRaises(ValueError):
                prepare(audio,annotation,"seconds",2,3,out)
            annotation.write_text("0 0.2 a\n0.3 0.5 b",encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare(audio,annotation,"seconds",1,2,d/"gap")
            annotation.write_text("0 1.1 a",encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare(audio,annotation,"seconds",1,1,d/"outside")
