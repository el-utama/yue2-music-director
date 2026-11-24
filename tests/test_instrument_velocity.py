import unittest
from yue2_music_director.instrument_velocity import humanize
from yue2_music_director.midi_events import parse_midi_data


def track(payload):
    return b"MTrk"+len(payload).to_bytes(4,"big")+payload


def fixture():
    header=bytes.fromhex("4d54686400000006000100030060")
    meter=track(bytes.fromhex("00ff58040402180800ff2f00"))
    def voice(name, channel, velocities):
        result=bytes([0,255,3,len(name)])+name
        for velocity in velocities:
            result+=bytes([0,0x90+channel,60,velocity,48,0x80+channel,60,0])
        return track(result+bytes.fromhex("00ff2f00"))
    return header+meter+voice(b"Vocal",0,[100]*8)+voice(b"Ins",1,[90]*8)


class InstrumentVelocityTests(unittest.TestCase):
    def test_protected_vocal_and_note_structure(self):
        source=fixture()
        output,report=humanize(source)
        self.assertEqual(report["pitch_changes"],0)
        self.assertEqual(report["timing_changes"],0)
        self.assertEqual(report["changed_tracks"],[2])
        self.assertGreater(report["velocity_changes"],0)
        before=parse_midi_data(source)
        after=parse_midi_data(output)
        self.assertEqual([n for n in before["notes"] if n.track==1],
                         [n for n in after["notes"] if n.track==1])
        self.assertGreater(len({n.velocity for n in after["notes"] if n.track==2}),1)
        self.assertEqual(output,humanize(source)[0])
        offsets=set(before["note_on_offsets"][n.order] for n in before["notes"] if n.track==2)
        self.assertTrue(all(i in offsets for i,(a,b) in enumerate(zip(source,output)) if a!=b))

    def test_invalid_strength(self):
        for value in (0,25,True):
            with self.assertRaises(ValueError):
                humanize(fixture(),value)
