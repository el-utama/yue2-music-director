import unittest
from yue2_music_director.midi_events import MIDIEventError,compare_midi_data,parse_midi_data


def vlq(n):
    data=[n&127]
    n>>=7
    while n:
        data.insert(0,(n&127)|128)
        n>>=7
    return bytes(data)


def example(pitch=60,start=0,velocity=80):
    event=(vlq(start)+bytes([0x90,pitch,velocity])
           +vlq(120)+bytes([0x80,pitch,0])
           +b'\x00\xff\x2f\x00')
    header=b'MThd'+(6).to_bytes(4,'big')+b'\x00\x01\x00\x01\x01\xe0'
    return header+b'MTrk'+len(event).to_bytes(4,'big')+event


class MIDIEventTests(unittest.TestCase):
    def test_parse(self):
        d=parse_midi_data(example())
        self.assertEqual(len(d['notes']),1)
        self.assertEqual(d['notes'][0].pitch,60)
        self.assertEqual(d['notes'][0].duration,120)
    def test_pitch_change_only(self):
        result=compare_midi_data(example(),example(pitch=62),allowed_pitch_tracks=[0])
        self.assertEqual(result['pitch_changes'],1)
        self.assertEqual(result['timing_changes'],0)
        self.assertEqual(result['velocity_changes'],0)
    def test_velocity_change_only(self):
        result=compare_midi_data(example(),example(velocity=100))
        self.assertEqual(result['velocity_changes'],1)
    def test_timing_change_only(self):
        result=compare_midi_data(example(),example(start=20))
        self.assertEqual(result['timing_changes'],1)
    def test_protected_track(self):
        with self.assertRaises(MIDIEventError):
            compare_midi_data(example(),example(pitch=62),allowed_pitch_tracks=[1])
    def test_missing_end(self):
        with self.assertRaises(MIDIEventError):
            parse_midi_data(example()[:-4])


if __name__=='__main__':unittest.main()
