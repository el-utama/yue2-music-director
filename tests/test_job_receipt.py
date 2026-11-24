import json
import unittest
from yue2_music_director.job_receipt import extract_song_job_id, AmbiguousJobReceipt


class ReceiptTests(unittest.TestCase):
    def test_actual_structured_response(self):
        job = {'id': 'job-123', 'status': 'queued', 'phase': 'generating', 'tracks_asked': 1}
        self.assertEqual(extract_song_job_id({'structuredContent': job, 'content': [{'type': 'text', 'text': json.dumps(job)}]}), 'job-123')

    def test_conflict_fails_closed(self):
        with self.assertRaises(AmbiguousJobReceipt):
            extract_song_job_id({'structuredContent': {'id':'a', 'status':'queued', 'phase':'x'}, 'content':[{'type':'text','text':json.dumps({'id':'b','status':'queued','phase':'x'})}]})

    def test_library_id_is_not_a_job(self):
        self.assertIsNone(extract_song_job_id({'structuredContent': {'id': 'song-123', 'title': 'Song'}}))

    def test_explicit_job_id(self):
        self.assertEqual(extract_song_job_id({'job_id': 'j-9'}), 'j-9')

    def test_unknown_response_is_not_success(self):
        self.assertIsNone(extract_song_job_id({'content': [{'type':'text','text':'not json'}]}))


if __name__ == '__main__':
    unittest.main()
