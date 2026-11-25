import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
from yue2_music_director import native_draft as nd, outro_inspection as oi

class OutroInspectionTests(unittest.TestCase):
    def test_retained_job_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)
            brief={"title":"Test","style":"Folk","lyrics":"[Verse]\nOne two\n[Outro]\nThree four","language":"en","seed":42,"duration_seconds":90}
            nd.atomic_write(repo/"local/brief.json",brief)
            root=repo/"results/drafts"/oi._sha(oi._canonical(brief))
            nd.atomic_write(root/"journal_song.json",{"state":"SUBMITTED","job_id":"job","brief_sha256":oi._sha(oi._canonical(brief)),"request_sha256":oi._sha(oi._canonical(nd.request_for(brief)))})
            with patch.object(oi,"Client") as factory,patch.object(oi,"native_song_read",return_value={"id":"song","metadata":{"job_id":"job","seed":42,"lm_seed":42},"generation_settings":{"abc":"X:1\n% verse\nV: Vocal\nC4|\n% outro\nV: Vocal\nZ1|"},"replay_request":{"semantic_tokens":"1,2"}}):
                client=factory.return_value.connect.return_value
                client.call.return_value={"id":"job","status":"completed","seed":42,"lm_seed":42,"adapters":None,"songs":[{"id":"song"}]}
                output=StringIO()
                with redirect_stdout(output):
                    oi.inspect(repo,"http://127.0.0.1:8791/mcp")
                client.call.assert_called_once_with("song_job_get",{"job_id":"job","response_format":"concise"})
                self.assertIn("Saved outro section present: True",output.getvalue())
                self.assertIn("Three four",output.getvalue())
                self.assertIn("New song jobs: 0",output.getvalue())
