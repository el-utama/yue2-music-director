import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yue2_music_director import audio_critic as ac
from yue2_music_director import native_draft as nd


def model_answer():
    return [{"id": key, "status": "uncertain", "evidence": "Not established"}
            for key, _ in ac.RUBRIC]


class CriticContractTests(unittest.TestCase):
    def test_strict_parser_coverage(self):
        rows = model_answer()
        status, parsed = ac.parse_response(json.dumps(rows[::-1]))
        self.assertEqual(status, "parsed_unvalidated")
        self.assertEqual(parsed, rows)
        for raw in ("not JSON", json.dumps(rows[:-1]), json.dumps(rows[:-1]+[rows[0]]),
                    json.dumps([{**rows[0], "status":"pass"}, *rows[1:]]),
                    json.dumps([{**rows[0], "evidence":""}, *rows[1:]])):
            status, parsed = ac.parse_response(raw)
            self.assertEqual(status, "unparseable")
            self.assertEqual(len(parsed),len(ac.RUBRIC))
            self.assertTrue(all(r["status"]=="uncertain" and r["evidence"] is None for r in parsed))

    def test_inventory_uses_only_managed_studio_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp).resolve()
            media=data/"media"
            media.mkdir()
            rows=[{"audio":str(media/"a.flac")},{"audio":str(media/"b.flac")}]
            self.assertFalse(ac.inventory(rows)["ready"])
            engine=data/"hotstep"/ac.TOOLS_FOLDER
            models=data/"training/models/moss"
            engine.mkdir(parents=True)
            models.mkdir(parents=True)
            for name in ("ace-caption.exe","ggml.dll","ggml-base.dll"):
                (engine/name).write_bytes(b"fixture")
            with patch.object(ac,"MODEL_FILES",(("tower.gguf",7),("lm.gguf",7))):
                for name,size in ac.MODEL_FILES:
                    (models/name).write_bytes(b"fixture")
                inventory=ac.inventory(rows)
                self.assertTrue(inventory["ready"])
                self.assertEqual(inventory["captioner"],str(engine/"ace-caption.exe"))
                (models/"lm.gguf").write_bytes(b"bad")
                self.assertFalse(ac.inventory(rows)["ready"])

    def test_excerpts_cover_duration_without_exceeding_cpu_limit(self):
        for seconds in (1,198.3,200.2,210):
            (a,d),(b,e)=ac.excerpt_ranges(seconds)
            self.assertEqual(a,0)
            self.assertEqual(b,d)
            self.assertAlmostEqual(b+e,seconds)
            self.assertLessEqual(max(d,e),120)
        with self.assertRaises(ValueError):
            ac.excerpt_ranges(211)

    def test_offline_calibration_plan_uses_no_evaluation_or_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp).resolve()
            rows=[{"arm":"reviewed"},{"arm":"direct"}]
            installed={"ready":False,"files":[]}
            with patch.object(ac,"retained_pair",return_value=rows), \
                 patch.object(ac,"inventory",return_value=installed), \
                 patch.object(ac,"evaluate") as evaluate, \
                 patch.object(ac.subprocess,"run") as run, \
                 patch("sys.argv",["critic","--repo",str(repo)]):
                self.assertEqual(ac.main(),0)
                self.assertEqual(ac.main(),0)
                self.assertTrue((repo/"results/critic-calibration/inventory.json").exists())
                self.assertFalse((repo/"results/critic-calibration/report.json").exists())
                evaluate.assert_not_called()
                run.assert_not_called()

class PairTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve()
        source = Path(__file__).resolve().parents[1]/"examples/artist-demo/brief.json"
        brief = nd.load_brief(source)
        folder = self.repo/"examples/artist-demo"
        folder.mkdir(parents=True)
        nd.atomic_write(folder/"brief.json",brief)
        root = self.repo/"results/drafts"/("artist-"+nd.digest(nd._canonical(brief)))
        self.root = root
        self.comparison = root/"direct-native-comparison"
        reviewed = root/"oom-recovery-1"/"draft"
        direct = self.comparison/"draft"
        reviewed.mkdir(parents=True)
        direct.mkdir(parents=True)
        abc = "fixture native ABC"
        (root/"native-plan.abc").write_bytes(abc.encode("utf-8"))
        config = {"profile":"balanced"}
        joined = {"schema":"matched-native-result-v1","automatic_winner":False,
                  "saved_score_identity":"identical","comparison":{"reference_configuration":config}}
        for name,route,draft in (("reviewed","reviewed_native",reviewed),("direct","direct_native",direct)):
            audio = self.repo/(name+".flac")
            audio.write_bytes(name.encode("ascii"))
            sha = nd._sha(audio)
            request = nd.request_for(brief)
            if name=="reviewed":
                request["abc"] = abc
            report = {"generation_path":route,"brief_sha256":nd.digest(nd._canonical(brief)),
                      "request_sha256":nd.digest(nd._canonical(request)),
                      "job_id":name+"-job","song_id":name+"-song",
                      "audio":str(audio),"audio_sha256":sha,"automatic_acceptance":False,
                      "acoustic":{"duration_seconds":100,"sha256":sha},"lyric_screen":{}}
            journal = {"state":"COMPLETED","request_sha256":report["request_sha256"],
                       "job_id":report["job_id"],"song_id":report["song_id"],
                       "reference_configuration":config,"audio_sha256":sha}
            for filename,data in (("report.json",report),("journal_song.json",journal),
                                  ("request.json",request),("brief.json",brief)):
                nd.atomic_write(draft/filename,data)
            joined[name] = report
        nd.atomic_write(self.comparison/"comparison-result.json",joined)

    def test_pair_is_read_only_and_changed_audio_rejected(self):
        rows = ac.retained_pair(self.repo)
        self.assertEqual([row["arm"] for row in rows],["reviewed","direct"])
        (self.repo/"direct.flac").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"FLAC identity"):
            ac.retained_pair(self.repo)

    def test_changed_configuration_rejected(self):
        path = self.comparison/"draft"/"journal_song.json"
        journal = nd.read(path)
        journal["reference_configuration"] = {"profile":"other"}
        nd.atomic_write(path,journal)
        with self.assertRaisesRegex(ValueError,"arm identity"):
            ac.retained_pair(self.repo)
