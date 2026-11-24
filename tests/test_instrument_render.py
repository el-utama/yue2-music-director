import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import wave
import struct
from yue2_music_director.instrument_render import accompaniment, measure
from yue2_music_director.instrument_velocity import humanize
from yue2_music_director.midi_events import parse_midi_data
from test_instrument_velocity import fixture


class InstrumentRenderTests(unittest.TestCase):
    def test_accompaniment_only(self):
        a=accompaniment(fixture())
        parsed=parse_midi_data(a)
        self.assertEqual(parsed["tracks"],2)
        self.assertEqual(len(parsed["notes"]),8)
        self.assertEqual(parsed["track_names"][1],["Ins"])
        self.assertTrue(all(n.channel==1 for n in parsed["notes"]))

    def test_synthetic_acoustic_difference(self):
        source=fixture()
        a=accompaniment(source)
        b=accompaniment(humanize(source)[0])
        with TemporaryDirectory() as d:
            def write(path,levels):
                with wave.open(str(path),"wb") as f:
                    f.setparams((2,2,44100,0,"NONE","not compressed"))
                    for value in levels:
                        f.writeframes(struct.pack("<hh",value,value)*11025)
            x,y=Path(d)/"a.wav",Path(d)/"b.wav"
            write(x,[1000]*8)
            write(y,[1000,700]*4)
            m=measure(x,y,a,b)
            self.assertEqual(m["onsets_measured"],8)
            self.assertTrue(m["sample_difference"])
            self.assertGreater(m["paired_gain_delta_sd_db"],1)
            self.assertEqual(m["onset_rms_sd_db"]["control"],0)
            self.assertEqual(m["clipped_samples"],{"control":0,"candidate":0})
            self.assertFalse(measure(x,x,a,b)["sample_difference"])
