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


class MusicProvider:
    def __init__(self,job):
        self.job=job
    def identity(self):
        return {"model":"fixture"}
    def complete(self,role,prompt,data):
        result={"composer":{"title":self.job,"style":"English folk","concept":"Leaving home",
                            "emotional_arc":"Loss to hope","performance":"Soft acoustic voice"},
                "lyricist":{"lyrics":"[Verse]\nPrivate words"},
                "reviewer":{"decision":"retain","rationale":"Fixture"},
                "director":{"decision":"retain_provisional","rationale":"Fixture",
                            "suggested_next_step":"Listen"}}[role]
        if role=="composer" and "typed_requirements" in data:
            result["style"]="English folk, female vocals"
            result["direction"]={"opening":"direct_vocal","vocal":"female","narrator":"first person",
                                 "section_plan":[{"section":"verse#1","purpose":"Introduce the departure"}]}
        return result


def make_song(repo,job,continuation=False,typed_spec=None):
    from yue2_music_director import autonomous as au, creative_core as cc, listening_director as ld
    from yue2_music_director import artist_run as ar, director_decision as dd
    from test_creative_direction import HEADER, VERSE
    parent=repo/"results/autonomous"/job
    parent.mkdir(parents=True)
    provider=MusicProvider(job)
    identity={"schema":"autonomous-job-v1","job":job,"request":"Original synthetic fixture",
              "language":"en","duration_seconds":90,"provider":provider.identity(),
              "studio_url":"http://127.0.0.1:8791/mcp","production_policy":au.LEGACY_POLICY}
    if typed_spec is not None:
        identity["creative_spec"]=au.tc.validate_spec(typed_spec)
        identity["production_policy"]=au.tc.POLICY
    nd.atomic_write(parent/"job.json",identity)
    creative=cc.prepare(parent,provider,identity["request"],"en",90,duration_guidance=True,
                        typed_spec=identity.get("creative_spec"))
    nd.atomic_write(parent/"creative-result.json",creative)
    brief,intent=au.make_inputs(creative,identity)
    nd.atomic_write(parent/"brief.json",brief)
    nd.atomic_write(parent/"intent.json",intent)
    root=parent/"continuation-1" if continuation else parent
    production=root/"production"
    draft=production/"draft"
    draft.mkdir(parents=True)
    nd.atomic_write(root/"brief.json",brief)
    nd.atomic_write(root/"intent.json",intent)
    abc=(HEADER+VERSE).replace("\n","\r\n")
    score_sha=nd.digest(abc.encode("utf-8"))
    (production/"native-plan.abc").write_bytes(abc.encode("utf-8"))
    decision=ar.evaluate_plan(abc,brief,intent)
    assert decision["decision"]=="retain",decision
    nd.atomic_write(production/"plan-decision.json",decision)
    nd.atomic_write(production/"manifest.json",{"schema":"artist-run-v1","brief":brief,"intent":intent,
                    "route":"reviewed_native","explicit_score_sha256":None})
    nd.atomic_write(production/"journal_plan.json",{"state":"COMPLETED","score_sha256":score_sha})
    nd.atomic_write(production/"plan-result.json",{"id":"plan"})
    nd.atomic_write(production/"plan-receipt.json",{"id":"plan"})
    if continuation:
        old=parent/"production"
        old.mkdir()
        files=("manifest.json","journal_plan.json","plan-result.json","plan-receipt.json","native-plan.abc")
        for name in files:
            (old/name).write_bytes((production/name).read_bytes())
        nd.atomic_write(old/"plan-decision.json",{"decision":"stop"})
        nd.atomic_write(parent/"plan-stop.json",{"status":"plan_review_required"})
        nd.atomic_write(root/"continuation.json",{"schema":"retained-plan-continuation-v1","parent_job":job,
            "original_job_sha256":nd._sha(parent/"job.json"),"original_stop_sha256":nd._sha(parent/"plan-stop.json"),
            "original_plan_decision_sha256":nd._sha(old/"plan-decision.json"),
            "source_files":{name:nd._sha(old/name) for name in files},"review":decision})
    audio=parent/"fixture.flac"
    audio.write_bytes(b"synthetic retained audio")
    sha=nd._sha(audio)
    request={**nd.request_for(brief),"abc":abc}
    request_sha=nd.digest(nd._canonical(request))
    nd.atomic_write(draft/"brief.json",brief)
    nd.atomic_write(draft/"request.json",request)
    nd.atomic_write(draft/"journal_song.json",{"state":"COMPLETED","job_id":"native-"+job,"song_id":job,
                    "audio_sha256":sha,"request_sha256":request_sha})
    pre={"score_sha256":score_sha,"structural_review":decision,"midi":{"verified":True}}
    nd.atomic_write(draft/"score-review.json",pre)
    (draft/"saved-score.abc").write_bytes(abc.encode("utf-8"))
    post=decision["score_review"]
    nd.atomic_write(draft/"saved-score-review.json",post)
    acoustic={"sha256":sha,"duration_seconds":2,"integrated_lufs":-17,
              "true_peak_dbtp":-0.2,"loudness_range_lu":0}
    report={"schema":"native-draft-v1","song_id":job,"job_id":"native-"+job,"audio":str(audio),
            "audio_sha256":sha,"generation_path":"reviewed_native","artistic_intent":intent,
            "automatic_acceptance":False,"brief_sha256":nd.digest(nd._canonical(brief)),
            "request_sha256":request_sha,"acoustic":acoustic,"score_review":pre,"saved_score_review":post,
            "saved_score_verified":True,"actual_lyric_conditioning_verified":True,
            "headroom_pass":False,"duration_cap_screen_pass":True,
            "lyric_screen":{"primary_metric":"wer","wer":{"disagreement_rate":0}}}
    nd.atomic_write(draft/"report.json",report)
    row=ld.verify_take(draft,brief,report)
    out=production/"neutral-listening"
    contract=ld.freeze(out,row)
    runtime={"fixture":"hash"}
    nd.atomic_write(out/"runtime.json",runtime)
    evidence=[]
    for j,(start,duration) in enumerate(contract["ranges"],1):
        stem="arm-1-part-"+str(j)
        raw=out/(stem+".txt")
        response="VOCAL: soft"
        raw.write_text(response,encoding="utf-8")
        receipt={"audio_sha256":sha,"start_seconds":start,"duration_seconds":duration,
                 "prompt_sha256":nd._sha(out/"prompt.txt"),"runtime":runtime}
        nd.atomic_write(out/(stem+".json"),{"identity":receipt,"response_sha256":nd._sha(raw)})
        status,checks=ld.parse_observations(response)
        evidence.append({"arm":"baseline","start_seconds":start,"duration_seconds":duration,
                         "format_status":status,"checks":checks,"raw_response":response})
    packet=ld.review_packet(brief,intent,row,contract,evidence)
    nd.atomic_write(out/"review-packet.json",packet)
    director=cc.stage(root,"director",dd,provider,dd.context(identity["request"],brief,intent,report,packet))
    nd.atomic_write(root/"result.json",{"schema":"autonomous-result-v1","status":"review_required",
        "song_id":job,"audio":str(audio),"audio_sha256":sha,"brief_sha256":nd._sha(root/"brief.json"),
        "native_report_sha256":nd._sha(draft/"report.json"),"listening_packet_sha256":nd._sha(out/"review-packet.json"),
        "director":director,"automatic_acceptance":False,"revision_authorized":False,
        "human_listening_verdict":"pending"})
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

    def test_explicit_ep_distinct_from_album(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            make_song(repo,"one")
            make_song(repo,"two")
            provider=Fake()
            self.assertEqual(ca.launch(repo,"ep",["one","two"],title="EP",kind="ep",confirm=True,
                                       provider_factory=lambda:provider),0)
            self.assertEqual(provider.calls[0][1]["release_type"],"ep")
            self.assertEqual(nd.read(repo/"results/artwork/ep/cover-brief.json")["release_type"],"ep")
            with self.assertRaisesRegex(ValueError,"job differs"):
                ca.launch(repo,"ep",["one","two"],title="EP",kind="album",confirm=True,
                          provider_factory=lambda:provider)
            self.assertEqual(len(provider.calls),1)
