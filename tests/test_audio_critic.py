import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

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

    def test_download_identity_and_no_network_on_cached_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"file"
            path.write_bytes(b"fixture")
            asset = ("file","https://example.invalid/file",7,nd._sha(path))
            with patch.object(ac.subprocess,"run") as run:
                ac.download(path.parent,asset)
                path.write_bytes(b"altered")
                with self.assertRaisesRegex(ValueError,"changed pinned asset"):
                    ac.download(path.parent,asset)
                run.assert_not_called()

    def test_archive_extract_whitelist(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/"fixture.zip"
            with zipfile.ZipFile(archive,"w") as z:
                for name in ("ace-caption.exe","ggml.dll","ggml-base.dll","ggml-cpu-avx2.dll","ace-server.exe"):
                    z.writestr("dist/engine/"+name,b"fixture")
                z.writestr("dist/ui/index.html",b"fixture")
            self.assertEqual({name for _,name in ac.archive_members(archive)},
                             {"ace-caption.exe","ggml.dll","ggml-base.dll","ggml-cpu-avx2.dll"})
            with zipfile.ZipFile(archive,"a") as z:
                z.writestr("another/ace-caption.exe",b"fixture")
            with self.assertRaisesRegex(ValueError,"exactly one"):
                ac.archive_members(archive)

    def test_offline_calibration_plan_uses_no_evaluation_or_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            with patch.object(ac,"retained_pair",return_value=[{"arm":"reviewed"},{"arm":"direct"}]), \
                 patch.object(ac,"setup") as setup,patch.object(ac,"evaluate") as evaluate, \
                 patch("sys.argv",["critic","--repo",str(repo)]):
                self.assertEqual(ac.main(),0)
                self.assertEqual(ac.main(),0)
                self.assertTrue((repo/"results/critic-calibration/prompt.txt").exists())
                self.assertFalse((repo/"results/critic-calibration/report.json").exists())
                setup.assert_not_called()
                evaluate.assert_not_called()


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
