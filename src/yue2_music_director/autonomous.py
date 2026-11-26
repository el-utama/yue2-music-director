"""One confirmed natural-language job; bounded text and native stages."""
from pathlib import Path
import argparse
import subprocess
import sys
import uuid

from . import creative_core as cc, director_decision as dd, listening_director as ld
from . import native_draft as nd, artist_run
from .creative_provider import TextProvider
from .mcp import MCPError, configured_endpoint
from .prosody import parse_lyrics


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
    intent=artist_run.validate_intent({"schema":"artist-intent-v1","route":"auto",
          "concept":music["concept"],"emotional_arc":music["emotional_arc"],"performance":music["performance"],
          "section_purposes":purposes,"constraints":{},"retain_soft_flags":{},"follow_lyrics":False,
          "budget":{"score_jobs":0,"song_jobs":1,"recognition_calls":1}})
    return brief,intent


def launch(repo, job, request, language, duration, url, *, confirm=False,
           provider_factory=TextProvider.from_env):
    cc.validate_job(job,request,language,duration)
    url=configured_endpoint(url)
    print("Job:",job,flush=True)
    print("Budget: four text stages, one native song, one explicit ASR, two CPU excerpts.",flush=True)
    if not confirm:
        print("Plan only; zero provider or Studio calls.",flush=True)
        return 0
    provider=provider_factory()
    jobs=repo/"results/autonomous"
    root=jobs/job
    with ld.lock(jobs/".active"):
        identity={"schema":"autonomous-job-v1","job":job,"request":request,"language":language,
                  "duration_seconds":duration,"provider":provider.identity(),"studio_url":url}
        if root.exists():
            if nd.read(root/"job.json")!=identity:
                raise ValueError("Retained job identity differs")
        else:
            root.mkdir(parents=True,exist_ok=False)
            nd.atomic_write(root/"job.json",identity)
        print("Creative stages",flush=True)
        result=cc.prepare(root,provider,request,language,duration)
        freeze(root/"creative-result.json",result)
        if result["review"]["decision"]!="retain":
            print("Editorial stop. No native generation:",root/"creative-result.json",flush=True)
            return 2
        brief,intent=make_inputs(result,identity)
        freeze(root/"brief.json",brief)
        freeze(root/"intent.json",intent)
        brief=nd.load_brief(root/"brief.json")
        production=root/"production"
        # Same shared guards used by existing launchers. Native runner owns its
        # existing attempt and receipt semantics, not a second submission path.
        with ld.lock(repo/"results/drafts/.active"), ld.lock(repo/"results/.critic-active"):
            print("Native production",flush=True)
            report=artist_run.run(brief,intent,production,url)
            row=ld.verify_take(production/"draft",brief,report)
            if report.get("artistic_intent")!=intent:
                raise ValueError("Native artistic intent mismatch")
            print("Retained audio:",row["audio"],flush=True)
            print("Neutral audio evaluation",flush=True)
            packet=ld.listen(production,brief,intent,row,url)
        print("Director judgment",flush=True)
        decision=cc.stage(root,"director",dd,provider,dd.context(request,brief,intent,report,packet))
        technical=report["headroom_pass"] and report["duration_cap_screen_pass"]
        status=("provisional" if technical and decision["decision"]=="retain_provisional"
                else "review_required")
        final={"schema":"autonomous-result-v1","status":status,"song_id":report["song_id"],
               "audio":row["audio"],"audio_sha256":row["audio_sha256"],"director":decision,
               "automatic_acceptance":False,"human_listening_verdict":"pending",
               "brief_sha256":nd._sha(root/"brief.json"),
               "native_report_sha256":nd._sha(production/"draft/report.json"),
               "listening_packet_sha256":nd._sha(production/"neutral-listening/review-packet.json"),
               "revision_authorized":False}
        freeze(root/"result.json",final)
        print("Status:",status,flush=True)
        print("Director:",decision["rationale"],flush=True)
        print("Result:",root/"result.json",flush=True)
        print("No automatic acceptance, finishing or additional generation.",flush=True)
        return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--url",required=True)
    p.add_argument("--job")
    p.add_argument("--request")
    p.add_argument("--language",choices=sorted(cc.SUPPORTED))
    p.add_argument("--duration",type=int)
    p.add_argument("--confirm-run",action="store_true",
                   help="Authorize four external text stages and one local song, ASR and two CPU excerpts")
    a=p.parse_args()
    try:
        repo=a.repo.resolve()
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
            request=a.request if a.request is not None else input("Song idea: ")
            language=a.language or "en"
            duration=a.duration if a.duration is not None else 195
        return launch(repo,job,request,language,duration,a.url,confirm=a.confirm_run)
    except (OSError,ValueError,KeyError,TypeError,MCPError,subprocess.SubprocessError,EOFError) as e:
        print("ERROR:",e,file=sys.stderr,flush=True)
        print("Preserve job and receipts. Resume only the same job; no blind retry.",file=sys.stderr,flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
