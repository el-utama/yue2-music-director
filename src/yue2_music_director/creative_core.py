"""Durable text-only creative stages. No Studio mutation or generation."""
from pathlib import Path
import argparse
import re
import time
import sys

from . import composer, lyricist, creative_reviewer, native_draft as nd
from .creative_provider import TextProvider
from .listening_director import lock
from .multilingual_fidelity import SUPPORTED


def stage(root, role, module, provider, data, *, retry=False):
    identity={"role":role,"provider":provider.identity(),"prompt":module.PROMPT,"input":data}
    receipt=root/(role+".json")
    attempt=root/(role+".attempt.json")
    if receipt.exists():
        saved=nd.read(receipt)
        if not attempt.exists() or nd.read(attempt)!=identity or saved.get("identity")!=identity:
            raise ValueError("Retained stage identity differs: "+role)
        value=module.validate(saved["result"])
        print(role.capitalize()+": retained",flush=True)
        return value
    recovery=root/(role+".retry-1.attempt.json")
    if attempt.exists():
        if nd.read(attempt)!=identity:
            raise ValueError("Original stage identity differs: "+role)
        if not retry:
            raise ValueError("Unresolved stage attempt; explicit one-time text retry required: "+role)
        if recovery.exists():
            raise ValueError("Text retry already attempted; retain evidence: "+role)
        nd.create_journal(recovery,identity)
    else:
        if retry or recovery.exists():
            raise ValueError("No original unresolved stage to retry: "+role)
        nd.create_journal(attempt,identity)
    print(role.capitalize()+": requesting text",flush=True)
    started=time.monotonic()
    result=module.validate(provider.complete(role,module.PROMPT,data))
    nd.atomic_write(receipt,{"identity":identity,"result":result})
    print(role.capitalize()+": complete ("+str(round(time.monotonic()-started,1))+" s)",flush=True)
    return result


def prepare(root, provider, request, language, duration, *, retry_role=None, duration_guidance=False, direction_guidance=False):
    data={"request":request,"language":language,"duration_seconds":duration}
    if duration_guidance:
        # Advisory target only; the actual native score clock is screened before rendering.
        reserve=min(15,max(3,round(duration*0.08)))
        data["duration_plan"]={"hard_cap_seconds":duration,"target_score_seconds":duration-reserve,
              "ending_reserve_seconds":reserve,
              "guidance":"Plan a compact complete song, with a resolved final sung phrase and short instrumental tail inside the target. Allow room for introductions, instrumental breaks, breathing and sustained notes. Avoid redundant verses, long repeated choruses or extended outros. Lyricist should adapt line and section count to pacing; reviewer should stop implausibly long plans. Do not treat duration as an exact target or omit necessary closure."}
    if direction_guidance:
        from . import creative_direction as cd
        data["direction_guidance"]=cd.GUIDANCE
    music=stage(root,"composer",composer,provider,data,retry=retry_role=="composer")
    if direction_guidance:
        cd.parse_direction(music)
    words=stage(root,"lyricist",lyricist,provider,{**data,"composition":music},retry=retry_role=="lyricist")
    if direction_guidance:
        cd.validate_opening(music,words["lyrics"])
    review=stage(root,"reviewer",creative_reviewer,provider,{**data,"composition":music,
                 "lyrics":words["lyrics"],"diagnostics":lyricist.diagnostics(words["lyrics"],language)},retry=retry_role=="reviewer")
    return {"composition":music,"lyrics":words["lyrics"],"review":review}


def validate_job(job, request, language, duration):
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",job)
            or job.lower() in {"con","prn","aux","nul"} or re.fullmatch(r"(com|lpt)[1-9]",job.lower())):
        raise ValueError("Invalid job name")
    if not request.strip() or len(request)>4000 or language not in SUPPORTED or not 30<=duration<=208:
        raise ValueError("Invalid creative request, language or duration")


def launch(repo, job, request, language, duration, *, confirm_text=False, provider_factory=None):
    validate_job(job, request, language, duration)
    if not confirm_text:
        print("Plan only; no provider or Studio calls.")
        return 0
    provider=provider_factory() if provider_factory else TextProvider.for_repo(repo)
    jobs=repo/"results/creative"
    root=jobs/job
    with lock(jobs/".active"):
        identity={"schema":"creative-job-v1","request":request,"language":language,
                  "duration_seconds":duration,"provider":provider.identity()}
        manifest=root/"job.json"
        if root.exists():
            if nd.read(manifest)!=identity:
                raise ValueError("Retained job differs")
        else:
            root.mkdir(parents=True,exist_ok=False)
            nd.atomic_write(manifest,identity)
        result=prepare(root,provider,request,language,duration)
        nd.atomic_write(root/"creative-result.json",result)
        print("Creative result:",root/"creative-result.json")
        print("Editorial decision:",result["review"]["decision"])
        print("No Studio inference. Musical quality and originality not verified.")
        return 0 if result["review"]["decision"]=="retain" else 2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--job",required=True)
    p.add_argument("--request",required=True)
    p.add_argument("--language",default="en")
    p.add_argument("--duration",type=int,default=195)
    p.add_argument("--confirm-text",action="store_true")
    a=p.parse_args()
    try:
        return launch(a.repo.resolve(),a.job,a.request,a.language,a.duration,confirm_text=a.confirm_text)
    except (OSError,ValueError,KeyError,TypeError) as e:
        print("ERROR:",e,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
