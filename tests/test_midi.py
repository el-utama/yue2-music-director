import base64
import unittest
from yue2_music_director.midi import midi_header,extract_midi

SMF=(b'MThd'+(6).to_bytes(4,'big')+(1).to_bytes(2,'big')+(1).to_bytes(2,'big')
     +(480).to_bytes(2,'big')+b'MTrk'+(4).to_bytes(4,'big')+bytes([0,255,47,0]))


class MidiTests(unittest.TestCase):
    def test_valid_header(self):
        self.assertEqual(midi_header(SMF)['tracks'],1)
    def test_mcp_structured(self):
        self.assertEqual(extract_midi({'structuredContent':{'data':base64.b64encode(SMF).decode()}}),SMF)
    def test_mcp_text(self):
        import json
        result={'content':[{'type':'text','text':json.dumps({'midi_base64':base64.b64encode(SMF).decode()})}]}
        self.assertEqual(extract_midi(result),SMF)
    def test_reject_text(self):
        with self.assertRaises(ValueError):extract_midi({'content':[{'type':'text','text':'failed'}]})
    def test_truncated(self):
        with self.assertRaises(ValueError):midi_header(SMF[:-1])


if __name__=='__main__':unittest.main()
