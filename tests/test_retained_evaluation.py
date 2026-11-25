import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yue2_music_director import retained_evaluation as re
from yue2_music_director.native_recognition import _sha


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class RetainedEvaluationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.results = self.root/"results"
        self.native = self.results/"run/native"
        self.custom = self.results/"run/custom"
        a = self.custom/"dynamics/candidate.flac"
        b = self.native/"headroom-continuation/candidate.flac"
        for p in (a,b):
            p.parent.mkdir(parents=True)
            p.write_bytes(p.parent.name.encode())
        self.hashes = ["source",_sha(a),_sha(b)]
        screen = {"language":"en","lyrics_sha256":"lyrics","baseline_asr_sha256":"baseline"}
        common = {"source_sha256":"source","run_id":"run","request":{"song_id":"fixture"}}
        write(self.native/"report.json", {**common,"status":"preview_acoustic_blocked"})
        write(self.native/"run_identity.json",common)
        write(self.native/"submission.json",{**common,"state":"SUBMITTING","screening":screen})
        write(b.parent/"plan.json",{**common,"screening":screen})
        write(b.parent/"report.json",{"status":"candidate_nonregression_unverified",
              "after":{"arms":{"A":{"sha256":"source"},"B":{"sha256":self.hashes[2]}}}})
        write(self.custom/"report.json",{"schema":"finish-existing-v1",
              "status":"candidate_nonregression_unverified","language":"en",
              "source_sha256":{"mix":"source","lyrics":"lyrics","baseline_asr":"baseline"},
              "candidate_sha256":self.hashes[1]})
        self.report = {"schema":"audiobox-evaluation-v1","device":"cpu","model_revision":re.MODEL_REVISION,
                       "weights_sha256":re.WEIGHTS_SHA256,"automatic_acceptance":False,
                       "rows":[{"audio_sha256":h,"arm":i,"scores":dict.fromkeys(re.AXES,5.0)}
                               for i,h in enumerate(self.hashes,1)]}

    def test_cached_no_inference_or_studio(self):
        write(self.results/"audiobox-fixture.json",self.report)
        with patch.object(re,"source_audio") as source,patch.object(re,"evaluate") as evaluate:
            self.assertEqual(re.run(self.root,self.root/"missing","unused"),self.report)
            source.assert_not_called()
            evaluate.assert_not_called()

    def test_invalid_candidate_blocks(self):
        (self.custom/"dynamics/candidate.flac").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"found 0"):
            re.discover(self.results)

    def test_wrong_report_not_reused(self):
        self.report["rows"][1]["audio_sha256"]="wrong"
        write(self.results/"audiobox-fixture.json",self.report)
        self.assertIsNone(re.cached(self.results,self.hashes))
