import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from yue2_music_director import cover_art as ca, native_draft as nd
from yue2_music_director.creative_provider import TextProvider, ROLES, role_schema, NVIDIA_URL, NEMOTRON_VL


class Fake:
    def __init__(self):
        self.calls=[]
    def identity(self):
        return {"model":"fixture"}
    def complete(self,role,prompt,data):
        self.calls.append((role,data))
        return {"concept":"A vacant room","visual_prompt":"A single chair, muted blue light",
                "typography":"Small cream title in upper left","rationale":"Absence as metaphor"}


def make_song(repo,job,continuation=False):
    parent=repo/"results/autonomous"/job
    root=parent/"continuation-1" if continuation else parent
    root.mkdir(parents=True)
    brief={"title":job,"style":"English folk","lyrics":"[Verse]\nPrivate words",
           "language":"en","seed":42,"duration_seconds":90}
    nd.atomic_write(root/"brief.json",brief)
    nd.atomic_write(parent/"creative-result.json",{"composition":{"title":job,"style":brief["style"],
        "concept":"Leaving home","emotional_arc":"Loss to hope"},"lyrics":brief["lyrics"],"review":{"decision":"retain"}})
    production=root/"production"
    report=production/"draft/report.json"
    packet=production/"neutral-listening/review-packet.json"
    report.parent.mkdir(parents=True)
    packet.parent.mkdir()
    nd.atomic_write(report,{"song_id":job,"audio_sha256":"fixture"})
    nd.atomic_write(packet,{"observations":[]})
    nd.atomic_write(root/"result.json",{"schema":"autonomous-result-v1","status":"review_required",
        "song_id":job,"audio_sha256":"fixture","brief_sha256":nd._sha(root/"brief.json"),
        "native_report_sha256":nd._sha(report),"listening_packet_sha256":nd._sha(packet)})
    return parent


class CoverTests(unittest.TestCase):
    def test_single_resume_and_album_no_music_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            one=make_song(repo,"one",True)
            two=make_song(repo,"two")
            before={p:nd._sha(p) for parent in (one,two) for p in parent.rglob("*") if p.is_file()}
            f=Fake()
            self.assertEqual(ca.launch(repo,"one",["one"],provider_factory=lambda:self.fail("provider called")),0)
            for _ in range(2):
                self.assertEqual(ca.launch(repo,"one",["one"],confirm=True,provider_factory=lambda:f),0)
            self.assertEqual(len(f.calls),1)
            self.assertEqual(f.calls[0][0],"cover_art")
            self.assertNotIn("Private words",repr(f.calls[0][1]))
            self.assertEqual(ca.launch(repo,"album",["one","two"],title="New Homes",artist="Artist",
                              confirm=True,provider_factory=lambda:f),0)
            self.assertEqual(len(f.calls),2)
            self.assertEqual([t["title"] for t in f.calls[1][1]["tracks"]],["one","two"])
            self.assertEqual(nd.read(repo/"results/artwork/album/cover-brief.json")["image_generated"],False)
            self.assertIn("1:1",(repo/"results/artwork/one/flow-prompt.txt").read_text())
            for path,sha in before.items():
                self.assertEqual(nd._sha(path),sha)
            with self.assertRaisesRegex(ValueError,"job differs"):
                ca.launch(repo,"album",["two","one"],title="New Homes",confirm=True,provider_factory=lambda:f)
            self.assertEqual(len(f.calls),2)

    def test_incomplete_source_and_tampered_export_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            with self.assertRaises(ValueError):
                ca.launch(repo,"missing",["missing"],confirm=True,provider_factory=lambda:self.fail("provider called"))
            make_song(repo,"one")
            f=Fake()
            ca.launch(repo,"one",["one"],confirm=True,provider_factory=lambda:f)
            (repo/"results/artwork/one/flow-prompt.txt").write_text("changed")
            with self.assertRaisesRegex(ValueError,"prompt differs"):
                ca.launch(repo,"one",["one"],confirm=True,provider_factory=lambda:f)
            self.assertEqual(len(f.calls),1)

    def test_provider_schema_without_changing_existing_identity(self):
        import json
        self.assertNotIn("cover_art",ROLES)
        self.assertEqual(role_schema("cover_art"),ca.SCHEMA)
        provider=TextProvider(NVIDIA_URL,"secret",{r:NEMOTRON_VL for r in ROLES})
        with patch("urllib.request.build_opener") as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value=json.dumps({"choices":[{"finish_reason":"stop","message":{"content":"{}"}}]}).encode()
            provider.complete("cover_art",ca.PROMPT,{"fixture":True})
            req=opener.return_value.open.call_args.args[0]
            body=json.loads(req.data)
            self.assertEqual(body["model"],NEMOTRON_VL)
            self.assertEqual(body["response_format"]["json_schema"]["schema"],ca.SCHEMA)
            self.assertEqual(body["response_format"]["json_schema"]["name"],"cover_art_result")
