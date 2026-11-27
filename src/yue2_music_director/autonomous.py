"""One confirmed natural-language job; bounded text and native stages."""
from pathlib import Path
import argparse
import subprocess
import sys
import uuid

from . import creative_core as cc, director_decision as dd, listening_director as ld
from . import native_draft as nd, artist_run
from .creative_provider import TextProvider, ROLES
from .mcp import MCPError, configured_endpoint
from .prosody import parse_lyrics
from . import creative_direction as cd

LEGACY_POLICY="reviewed-score-v1"
POLICY=cd.POLICY
DIRECTION_POLICIES=(cd.PREVIOUS_POLICY,POLICY)
POLICIES=(LEGACY_POLICY,*DIRECTION_POLICIES)


def freeze(path, value):
    if path.exists():
        if nd.read(path)!=value:
            raise ValueError("Retained contract differs: "+path.name)
    else:
        nd.atomic_write(path,value)


def make_inputs(result, identity):
    music=result["composition"]
    brief={"title":music["title"],"style":music["style"],"lyrics":result["lyrics"],
           "language":identity["language"],"duration_seconds":identity["duration_seconds"],
           "seed":int(nd.digest(nd._canonical(identity))[:8],16) % (2**31)}
    purposes={f"{g['name']}#{g['occurrence']}":"Native musical development within the creative brief."
              for g in parse_lyrics(brief["lyrics"])}
    constraints={}
    if identity.get("production_policy") in DIRECTION_POLICIES:
        opening=cd.validate_opening(music,brief["lyrics"])["opening"]
        constraints["opening"]={"mode":"must","value":opening}
        if identity["production_policy"]==POLICY:
            constraints["opening_timing"]={"mode":"must","value":opening}
    intent=artist_run.validate_intent({"schema":"artist-intent-v1","route":"reviewed_native",
          "concept":music["concept"],"emotional_arc":music["emotional_arc"],"performance":music["performance"],
          "section_purposes":purposes,"constraints":constraints,"retain_soft_flags":{},"follow_lyrics":True,
          "budget":{"score_jobs":1,"song_jobs":1,"recognition_calls":1}})
    return brief,intent


def launch(repo, job, request, language, duration, url, *, confirm=False,
           provider_factory=None, retry_role=None):
    cc.validate_job(job,request,language,duration)
    url=configured_endpoint(url)
    print("Job:",job,flush=True)
    print("Budget: up to four text stages, one native composition plan, one native song, one explicit ASR, two CPU excerpts.",flush=True)
    if retry_role is not None and (retry_role not in ROLES or not confirm):
        raise ValueError("Retry requires a valid text role and explicit confirmation")
    if not confirm:
        print("Plan only; zero provider or Studio calls.",flush=True)
        return 0
    provider=provider_factory() if provider_factory else TextProvider.for_repo(repo)
    jobs=repo/"results/autonomous"
    root=jobs/job
    with ld.lock(jobs/".active"):
        identity={"schema":"autonomous-job-v1","job":job,"request":request,"language":language,
                  "duration_seconds":duration,"provider":provider.identity(),"studio_url":url,"production_policy":POLICY}
        if retry_role is not None:
            if (not (root/(retry_role+".attempt.json")).is_file()
                    or (root/(retry_role+".json")).exists()
                    or (root/(retry_role+".retry-1.attempt.json")).exists()):
                raise ValueError("Only one explicit retry of an existing unresolved text stage is permitted")
        if root.exists():
            previous=nd.read(root/"job.json")
            if previous.get("production_policy") not in POLICIES:
                raise ValueError("Legacy job retained unchanged; use --inspect-ending, not a new production route on this job")
            identity["production_policy"]=previous["production_policy"]
            if previous!=identity:
                raise ValueError("Retained job identity differs")
        else:
            root.mkdir(parents=True,exist_ok=False)
            nd.atomic_write(root/"job.json",identity)
        if (root/"plan-stop.json").exists():
            raise ValueError("Stopped plan retained; use --review-plan or explicit --continue-plan")
        print("Creative stages",flush=True)
        result=cc.prepare(root,provider,request,language,duration,retry_role=retry_role,duration_guidance=True,
                          direction_guidance=identity["production_policy"] in DIRECTION_POLICIES,
                          timing_guidance=identity["production_policy"]==POLICY)
        freeze(root/"creative-result.json",result)
        if result["review"]["decision"]!="retain":
            print("Editorial stop. No native generation:",root/"creative-result.json",flush=True)
            return 2
        brief,intent=make_inputs(result,identity)
        freeze(root/"brief.json",brief)
        freeze(root/"intent.json",intent)
        brief=nd.load_brief(root/"brief.json")
        return produce(repo,root,request,brief,intent,url,provider,retry_role=retry_role)


def produce(repo,root,request,brief,intent,url,provider,*,retry_role=None):
    production=root/"production"
    # Same shared guards used by existing launchers. Native runner owns its
    # existing attempt and receipt semantics, not a second submission path.
    with ld.lock(repo/"results/drafts/.active"), ld.lock(repo/"results/.critic-active"):
        print("Native production",flush=True)
        report=artist_run.run(brief,intent,production,url)
        if report["status"]=="artistic_plan_stopped":
            stopped={"schema":"autonomous-plan-stop-v1","status":"plan_review_required",
                     "decision":report["decision"],"automatic_acceptance":False,
                     "song_jobs":0,"recognition_calls":0,"revision_authorized":False}
            freeze(root/"plan-stop.json",stopped)
            print("Plan blocked before song synthesis; see",root/"plan-stop.json",flush=True)
            print("No song, ASR, MOSS or Director calls; no automatic retry.",flush=True)
            return 2
        row=ld.verify_take(production/"draft",brief,report)
        if report.get("artistic_intent")!=intent:
            raise ValueError("Native artistic intent mismatch")
        print("Retained audio:",row["audio"],flush=True)
        print("Neutral audio evaluation",flush=True)
        packet=ld.listen(production,brief,intent,row,url)
    print("Director judgment",flush=True)
    decision=cc.stage(root,"director",dd,provider,dd.context(request,brief,intent,report,packet),retry=retry_role=="director")
    technical=report["headroom_pass"] and report["duration_cap_screen_pass"]
    if "native_completion" in report:
        from .native_completion import blocks_provisional
        technical=technical and not blocks_provisional(report["native_completion"])
    status=("provisional" if technical and decision["decision"]=="retain_provisional"
            else "review_required")
    final={"schema":"autonomous-result-v1","status":status,"song_id":report["song_id"],
           "audio":row["audio"],"audio_sha256":row["audio_sha256"],"director":decision,
           "automatic_acceptance":False,"human_listening_verdict":"pending",
           "brief_sha256":nd._sha(root/"brief.json"),
           "native_report_sha256":nd._sha(production/"draft/report.json"),
           "listening_packet_sha256":nd._sha(production/"neutral-listening/review-packet.json"),
           "revision_authorized":False}
    if "native_completion" in report:
        final["native_completion"]=report["native_completion"]
    freeze(root/"result.json",final)
    print("Status:",status,flush=True)
    print("Director:",decision["rationale"],flush=True)
    print("Result:",root/"result.json",flush=True)
    print("No automatic acceptance, finishing or additional generation.",flush=True)
    return 0


def continue_plan(repo,job,url,*,confirm=False,provider_factory=None):
    """One distinct continuation of a retained parser-blocked plan, no new score."""
    from .retained_plan_review import inspect
    cc.validate_job(job,"placeholder","en",195)
    url=configured_endpoint(url)
    jobs=repo/"results/autonomous"
    parent=jobs/job
    if not confirm:
        print("Continuation plan only; zero provider or Studio calls.",flush=True)
        return 0
    with ld.lock(jobs/".active"):
        identity=nd.read(parent/"job.json")
        if (identity.get("job")!=job or identity.get("production_policy") not in POLICIES
                or identity.get("studio_url")!=url):
            raise ValueError("Retained job or Studio endpoint differs")
        cc.validate_job(job,identity["request"],identity["language"],identity["duration_seconds"])
        review=inspect(repo,job)
        old=nd.read(parent/"production/plan-decision.json")
        if (review["previous_status"]!="unassessable"
                or not any(x.get("code")=="unsupported_local_notation" for x in old["score_review"]["unknowns"])
                or review["current_decision"]["decision"]!="retain"):
            raise ValueError("Only a formerly unsupported plan now retained by review may continue")
        provider=provider_factory() if provider_factory else TextProvider.for_repo(repo)
        if provider.identity()!=identity["provider"]:
            raise ValueError("Retained provider identity differs")
        for role in ("composer","lyricist","reviewer"):
            if not (parent/(role+".json")).is_file() or not (parent/(role+".attempt.json")).is_file():
                raise ValueError("Retained creative receipt missing")
        result=cc.prepare(parent,provider,identity["request"],identity["language"],
                          identity["duration_seconds"],duration_guidance=True,
                          direction_guidance=identity["production_policy"] in DIRECTION_POLICIES,
                          timing_guidance=identity["production_policy"]==POLICY)
        if nd.read(parent/"creative-result.json")!=result or result["review"]["decision"]!="retain":
            raise ValueError("Retained creative result differs")
        brief,intent=make_inputs(result,identity)
        if nd.load_brief(parent/"brief.json")!=brief or nd.read(parent/"intent.json")!=intent:
            raise ValueError("Retained creative brief or intent differs")
        source=parent/"production"
        manifest={"schema":"artist-run-v1","brief":brief,"intent":intent,"route":"reviewed_native",
                  "explicit_score_sha256":None}
        if nd.read(source/"manifest.json")!=manifest:
            raise ValueError("Retained production manifest differs")
        files=("manifest.json","journal_plan.json","plan-result.json","plan-receipt.json","native-plan.abc")
        contract={"schema":"retained-plan-continuation-v1","parent_job":job,
                  "original_job_sha256":nd._sha(parent/"job.json"),
                  "original_stop_sha256":nd._sha(parent/"plan-stop.json"),
                  "original_plan_decision_sha256":nd._sha(source/"plan-decision.json"),
                  "source_files":{name:nd._sha(source/name) for name in files},
                  "review":review["current_decision"],
                  "budget":{"new_score_jobs":0,"song_jobs":1,"recognition_calls":1,"cpu_excerpts":2,"director_calls":1}}
        root=parent/"continuation-1"
        production=root/"production"
        if root.exists():
            if nd.read(root/"continuation.json")!=contract:
                raise ValueError("Retained continuation identity differs")
            if (not production.is_dir() or any(not (production/name).is_file() for name in files)
                    or not (root/"brief.json").is_file() or not (root/"intent.json").is_file()):
                raise ValueError("Incomplete continuation initialization; preserve evidence")
            for name in files:
                if nd._sha(production/name)!=contract["source_files"][name]:
                    raise ValueError("Retained continuation source differs: "+name)
        else:
            root.mkdir(exist_ok=False)
            nd.atomic_write(root/"continuation.json",contract)
            production.mkdir()
            for name in files:
                with (production/name).open("xb") as stream:
                    stream.write((source/name).read_bytes())
                if nd._sha(production/name)!=contract["source_files"][name]:
                    raise ValueError("Source changed during continuation initialization")
            nd.atomic_write(root/"brief.json",brief)
            nd.atomic_write(root/"intent.json",intent)
        freeze(root/"brief.json",brief)
        freeze(root/"intent.json",intent)
        print("Continuation:",root,flush=True)
        print("Budget: zero new composition plans, one native song, one ASR, two CPU excerpts, one Director.",flush=True)
        return produce(repo,root,identity["request"],brief,intent,url,provider)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--url",required=True)
    p.add_argument("--job")
    p.add_argument("--continue-plan",metavar="JOB",help="Explicit continuation of a rechecked parser-blocked plan")
    p.add_argument("--request")
    p.add_argument("--language",choices=sorted(cc.SUPPORTED))
    p.add_argument("--duration",type=int)
    p.add_argument("--confirm-run",action="store_true",
                   help="Authorize up to four external text stages, one native score plan, one local song, ASR and two CPU excerpts")
    p.add_argument("--retry-text",choices=ROLES,help="One explicitly authorized retry of the named unresolved text stage")
    a=p.parse_args()
    try:
        repo=a.repo.resolve()
        if a.continue_plan is not None:
            if any(x is not None for x in (a.job,a.request,a.language,a.duration,a.retry_text)):
                raise ValueError("Continuation does not allow job, brief or retry overrides")
            return continue_plan(repo,a.continue_plan,a.url,confirm=a.confirm_run)
        if a.retry_text and not a.job:
            raise ValueError("Text recovery requires the existing --job ID")
        job=a.job or ("song-"+uuid.uuid4().hex[:12])
        # Validate path component before reading an existing job.
        cc.validate_job(job,"placeholder","en",195)
        saved=repo/"results/autonomous"/job/"job.json"
        if saved.is_file():
            previous=nd.read(saved)
            request=a.request if a.request is not None else previous["request"]
            language=a.language if a.language is not None else previous["language"]
            duration=a.duration if a.duration is not None else previous["duration_seconds"]
        else:
            if a.request is None:
                print("Song idea:",flush=True)
                request=input()
            else:
                request=a.request
            language=a.language or "en"
            duration=a.duration if a.duration is not None else 195
        return launch(repo,job,request,language,duration,a.url,confirm=a.confirm_run,retry_role=a.retry_text)
    except (OSError,ValueError,KeyError,TypeError,MCPError,subprocess.SubprocessError,EOFError) as e:
        print("ERROR:",e,file=sys.stderr,flush=True)
        print("Preserve job and receipts. Resume only the same job; no blind retry.",file=sys.stderr,flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
