"""Generation-first artistic routing on top of the existing native draft runner."""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from . import native_draft as nd
from .experiments import _canonical, _sha as digest
from .mcp import Client, configured_endpoint, unpack
from .generation_control import result_score
from .musical_review import review_score, validate_constraints

SCHEMA="artist-intent-v1"
ALLOWED_FLAGS={"section_order_differs","notated_sung_sequence_differs",
               "identical_repeated_chorus","constraint_mismatch"}


def validate_intent(intent):
    keys={"schema","route","concept","emotional_arc","performance","section_purposes",
          "constraints","retain_soft_flags","follow_lyrics","budget"}
    if not isinstance(intent,dict) or set(intent)!=keys or intent["schema"]!=SCHEMA:
        raise ValueError("Invalid artistic intent schema")
    if intent["route"] not in ("auto","reviewed_native","explicit_score"):
        raise ValueError("Unknown artistic route")
    for name in ("concept","emotional_arc","performance"):
        if not isinstance(intent[name],str) or not intent[name].strip() or len(intent[name])>2000:
            raise ValueError("Invalid artistic "+name)
    purposes=intent["section_purposes"]
    if not isinstance(purposes,dict) or not purposes or any(
            not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip()
            or len(v)>1000 for k,v in purposes.items()):
        raise ValueError("Invalid section purposes")
    if not isinstance(intent["constraints"],dict):
        raise ValueError("Constraints must be an object")
    validate_constraints(intent["constraints"])
    flags=intent["retain_soft_flags"]
    if not isinstance(flags,dict) or not set(flags)<=ALLOWED_FLAGS or any(
            not isinstance(v,str) or not v.strip() or len(v)>1000 for v in flags.values()):
        raise ValueError("Soft flag retention requires a named rationale")
    if type(intent["follow_lyrics"]) is not bool:
        raise ValueError("Invalid follow_lyrics setting")
    budget=intent["budget"]
    if (not isinstance(budget,dict) or set(budget)!={"score_jobs","song_jobs","recognition_calls"}
            or any(type(v) is not int for v in budget.values())
            or budget["score_jobs"] not in (0,1) or budget["song_jobs"]!=1
            or budget["recognition_calls"]!=1):
        raise ValueError("Budget must authorize at most one plan, one song and one recognition")
    route=route_for(intent)
    if budget["score_jobs"]!=(1 if route=="reviewed_native" else 0):
        raise ValueError("Budget does not match route")
    if intent["follow_lyrics"] and route!="reviewed_native":
        raise ValueError("Section steering requires reviewed native route")
    return intent


def route_for(intent):
    if intent["route"]!="auto":
        return intent["route"]
    # Hard score requirements and requested steering need a pre-synthesis plan.
    if intent["follow_lyrics"] or any(c["mode"]=="must" for c in intent["constraints"].values()):
        return "reviewed_native"
    return "direct_native"


def evaluate_plan(abc,brief,intent):
    validate_intent(intent)
    report=review_score(abc,brief["lyrics"],constraints=intent["constraints"],
                        max_seconds=brief["duration_seconds"])
    decisions=[]
    for flag in report["soft_flags"]:
        reason=intent["retain_soft_flags"].get(flag["code"])
        decisions.append({"flag":flag,"decision":"retain" if reason else "stop",
                          "rationale":reason or "No predeclared musical justification"})
    retain=(report["status"] in ("local_review_ready","artistic_review_required")
            and not report["hard_violations"] and all(d["decision"]=="retain" for d in decisions))
    return {"schema":"artist-plan-decision-v1","decision":"retain" if retain else "stop",
            "score_review":report,"soft_decisions":decisions,
            "rationale":"Retain native composition unchanged; live MIDI required" if retain
                        else "Unresolved score evidence or artistic review flag; no synthesis",
            "automatic_acceptance":False}


def plan_request(brief,intent):
    request={"style":brief["style"],"lyrics":brief["lyrics"],"cot":"full",
             "lm_seed":brief["seed"],"lm_batch_size":1}
    if intent["follow_lyrics"]:
        request["harmony"]={"follow_lyrics":True}
    return request


def _preflight(client,brief,request):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("FFmpeg and ffprobe required before planning")
    tools={t["name"]:t.get("inputSchema",{}) for t in client.tools()}
    need={"score_compose","score_job_get","score_to_midi","song_create","song_job_get",
          "studio_wait","library_song_files","studio_status","song_defaults",
          "studio_capabilities","models_status","engine_options_get"}
    if not need<=tools.keys():
        raise ValueError("Required native artistic workflow tools missing")
    for name,payload in (("score_compose",request),("song_create",{**nd.request_for(brief),"abc":""}),
                         ("score_job_get",{"job_id":""}),("score_to_midi",{"abc":""})):
        schema=tools[name]
        if not set(payload)<=set(schema.get("properties",{})) or not set(schema.get("required",[]))<=set(payload):
            raise ValueError("Native tool schema mismatch: "+name)
    if "harmony" in request and "follow_lyrics" not in tools["score_compose"]["properties"]["harmony"].get("properties",{}):
        raise ValueError("Native section steering unavailable")
    nd.recognition_preflight(client)
    return nd.reference_configuration(client,unpack(client.call("studio_status",{})),
        nd.request_for(brief),unpack(client.call("song_defaults",{})),
        unpack(client.call("studio_capabilities",{})))


def native_plan(brief,intent,root,url,*,max_polls=120,sleep=time.sleep):
    request=plan_request(brief,intent)
    sha=digest(_canonical(request))
    path=root/"journal_plan.json"
    raw_path=root/"plan-result.json"
    if path.exists():
        journal=nd.read(path)
        if (journal.get("request_sha256")!=sha or journal.get("state") not in ("SUBMITTED","COMPLETED")
                or not isinstance(journal.get("id"),str) or not journal["id"]
                or not isinstance(journal.get("configuration"),dict)):
            raise ValueError("Uncertain or mismatched native planning job; never resubmit")
    else:
        if raw_path.exists() or (root/"native-plan.abc").exists() or (root/"plan-receipt.json").exists():
            raise ValueError("Retained plan artifacts lack a journal")
        client=Client(configured_endpoint(url),timeout=90).connect()
        config=_preflight(client,brief,request)
        journal={"state":"SUBMISSION_ATTEMPTED","request_sha256":sha,"configuration":config}
        nd.create_journal(path,journal)
        print("Submitting one native composition plan...",flush=True)
        response=unpack(client.call("score_compose",request))
        nd.atomic_write(root/"plan-receipt.json",response)
        if (not isinstance(response,dict) or not isinstance(response.get("id"),str)
                or not response["id"] or response.get("status") not in ("running","done")):
            raise ValueError("Ambiguous planning receipt; never resubmit")
        journal.update(state="SUBMITTED",id=response["id"])
        nd.atomic_write(path,journal)
    if raw_path.exists():
        result=nd.read(raw_path)
    else:
        if journal["state"]=="COMPLETED":
            raise ValueError("Completed plan result missing; never resubmit")
        client=Client(configured_endpoint(url),timeout=90).connect()
        for attempt in range(max_polls+1):
            result=unpack(client.call("score_job_get",{"job_id":journal["id"]}))
            if not isinstance(result,dict) or result.get("id")!=journal["id"]:
                raise ValueError("Planning job identity mismatch")
            if result.get("status")=="done":
                break
            if result.get("status")!="running" or attempt==max_polls:
                raise ValueError("Plan not complete in bounded polling; resume known job only")
            sleep(3)
        result_score(result,brief["seed"])
        nd.atomic_write(raw_path,result)
    if result.get("id")!=journal["id"]:
        raise ValueError("Retained native plan identity mismatch")
    abc=result_score(result,brief["seed"])
    score_sha=digest(abc.encode("utf-8"))
    if journal["state"]=="COMPLETED" and journal.get("score_sha256")!=score_sha:
        raise ValueError("Retained plan hash differs")
    score_path=root/"native-plan.abc"
    if score_path.exists():
        if score_path.read_bytes()!=abc.encode("utf-8"):
            raise ValueError("Retained native plan file differs")
    else:
        with score_path.open("xb") as stream:
            stream.write(abc.encode("utf-8"))
    journal.update(state="COMPLETED",score_sha256=score_sha)
    nd.atomic_write(path,journal)
    return abc,journal["configuration"]


def run(brief,intent,root,url,*,explicit_abc=None):
    validate_intent(intent)
    route=route_for(intent)
    if (route=="explicit_score")!=(explicit_abc is not None):
        raise ValueError("Explicit route requires a supplied score; other routes must not supply one")
    manifest={"schema":"artist-run-v1","brief":brief,"intent":intent,"route":route,
              "explicit_score_sha256":digest(explicit_abc.encode("utf-8")) if explicit_abc is not None else None}
    manifest_path=root/"manifest.json"
    if root.exists():
        if nd.read(manifest_path)!=manifest:
            raise ValueError("Retained artistic run differs; do not change route or replay")
    else:
        root.mkdir(parents=True,exist_ok=False)
        nd.atomic_write(manifest_path,manifest)
    abc=explicit_abc
    config=None
    if route=="reviewed_native":
        abc,config=native_plan(brief,intent,root,url)
    if abc is not None:
        decision=evaluate_plan(abc,brief,intent)
        decision_path=root/"plan-decision.json"
        if decision_path.exists():
            if nd.read(decision_path)!=decision:
                raise ValueError("Retained review decision differs")
        else:
            nd.atomic_write(decision_path,decision)
        print("Musical plan:",decision["decision"],flush=True)
        if decision["decision"]!="retain":
            print("Review:",decision_path,flush=True)
            return {"status":"artistic_plan_stopped","decision":decision,
                    "automatic_acceptance":False}
    return nd.execute(brief,root/"draft",url,abc=abc,artist=intent,expected_configuration=config)


def recover_oom(brief,intent,root,url):
    """One separately authorized synthesis of the identical failed demo request."""
    validate_intent(intent)
    manifest={"schema":"artist-run-v1","brief":brief,"intent":intent,
              "route":"reviewed_native","explicit_score_sha256":None}
    if nd.read(root/"manifest.json")!=manifest or route_for(intent)!="reviewed_native":
        raise ValueError("Recovery requires the original reviewed-native demo")
    # All evidence must already exist. Do not call native_plan: it can submit.
    plan=nd.read(root/"journal_plan.json")
    result=nd.read(root/"plan-result.json")
    if (plan.get("state")!="COMPLETED" or not isinstance(plan.get("id"),str)
            or not plan["id"] or result.get("id")!=plan["id"]
            or plan.get("request_sha256")!=digest(_canonical(plan_request(brief,intent)))
            or not isinstance(plan.get("configuration"),dict)):
        raise ValueError("Retained completed plan identity differs")
    abc=result_score(result,brief["seed"])
    if (plan.get("score_sha256")!=digest(abc.encode("utf-8"))
            or (root/"native-plan.abc").read_bytes()!=abc.encode("utf-8")):
        raise ValueError("Retained plan hash differs")
    decision=evaluate_plan(abc,brief,intent)
    if decision["decision"]!="retain" or nd.read(root/"plan-decision.json")!=decision:
        raise ValueError("Retained review does not authorize this composition")
    original=root/"draft"
    request={**nd.request_for(brief),"abc":abc}
    journal=nd.read(original/"journal_song.json")
    if ((original/"report.json").exists() or (original/"recognition").exists()
            or journal.get("state")!="SUBMITTED"
            or not isinstance(journal.get("job_id"),str) or not journal["job_id"]
            or journal.get("brief_sha256")!=digest(_canonical(brief))
            or journal.get("request_sha256")!=digest(_canonical(request))
            or nd.read(original/"brief.json")!=brief
            or nd.read(original/"request.json")!=request
            or journal.get("reference_configuration")!=plan["configuration"]
            or nd.read(original/"artist-policy.json")!={"intent":intent,"planner_configuration":plan["configuration"]}):
        raise ValueError("Original failed draft identity differs")
    recovery=root/"oom-recovery-1"
    identity={"schema":"artist-oom-recovery-v1","original_job_id":journal["job_id"],
              "original_request_sha256":journal["request_sha256"],
              "plan_id":plan["id"],"score_sha256":plan["score_sha256"],
              "budget":{"score_jobs":0,"song_jobs":1,"recognition_calls":1}}
    record=recovery/"recovery.json"
    evidence=recovery/"original-failure.json"
    if recovery.exists():
        if nd.read(record)!=identity:
            raise ValueError("Retained OOM recovery identity differs")
        failed=nd.read(evidence)
    else:
        client=Client(configured_endpoint(url),timeout=90).connect()
        failed=nd.read_job(client,journal["job_id"])
    message=failed.get("message")
    if (failed.get("id")!=journal["job_id"] or failed.get("status")!="failed"
            or failed.get("songs")!=[] or not isinstance(message,str)
            or "ran out of memory while the engine was loading the models" not in message.lower()):
        raise ValueError("Original job is not a verified terminal model-loading OOM with no songs")
    if not recovery.exists():
        recovery.mkdir(parents=True,exist_ok=False)
        nd.atomic_write(record,identity)
        nd.atomic_write(evidence,failed)
    print("Recovery: retained native composition; zero new score jobs.",flush=True)
    print("Original terminal job:",journal["job_id"],flush=True)
    # execute checks the live stock reference against the original planning
    # configuration, uses native MIDI, and journals before any new song POST.
    return nd.execute(brief,recovery/"draft",url,abc=abc,artist=intent,
                      expected_configuration=plan["configuration"])


def launch(repo,url,*,confirm=False,demo=False,recover=False):
    if recover and (not demo or not confirm):
        raise ValueError("OOM recovery requires the artist demo and explicit confirmation")
    folder=repo/("examples/artist-demo" if demo else "local")
    brief=nd.load_brief(folder/"brief.json")
    path=folder/"intent.json"
    if path.stat().st_size>100_000:
        raise ValueError("Intent exceeds size limit")
    intent=validate_intent(nd.read(path))
    route=route_for(intent)
    abc=None
    if route=="explicit_score":
        path=folder/"score.abc"
        if path.stat().st_size>800_000:
            raise ValueError("Explicit score exceeds size limit")
        abc=path.read_text(encoding="utf-8-sig")
    print("Artist:",brief["title"],"| route:",route,flush=True)
    print("Budget:",{"score_jobs":0,"song_jobs":1,"recognition_calls":1} if recover else intent["budget"],flush=True)
    if not confirm:
        if abc is not None:
            print("Offline plan decision:",evaluate_plan(abc,brief,intent)["decision"],flush=True)
        print("Plan only. No Studio calls or GPU work.",flush=True)
        return 0
    drafts=repo/"results/drafts"
    drafts.mkdir(parents=True,exist_ok=True)
    lock=drafts/".active"
    fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    os.close(fd)
    root=drafts/("artist-"+digest(_canonical(brief)))
    try:
        report=recover_oom(brief,intent,root,url) if recover else run(brief,intent,root,url,explicit_abc=abc)
    finally:
        lock.unlink()
    print("Artist result:",report["status"],flush=True)
    if recover:
        root=root/"oom-recovery-1"
    print("Run folder:",root,flush=True)
    if report["status"]=="artistic_plan_stopped":
        print("No full song authorized by review. Retained plan; no automatic retry.",flush=True)
        return 2
    metric=report["lyric_screen"]["primary_metric"]
    print("True peak:",report["acoustic"]["true_peak_dbtp"],"dBTP")
    print(metric,"disagreement:",report["lyric_screen"][metric]["disagreement_rate"])
    print("Local audio:",report["audio"])
    print("Report:",root/"draft/report.json")
    print("Automatic acceptance: false")
    return 0
