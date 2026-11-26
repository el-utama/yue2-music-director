"""Durable text-only creative stages. No Studio mutation or generation."""
from pathlib import Path
import argparse
import re
import sys

from . import composer, lyricist, creative_reviewer, native_draft as nd
from .creative_provider import TextProvider
from .listening_director import lock
from .multilingual_fidelity import SUPPORTED


def stage(root, role, module, provider, data):
    identity={"role":role,"provider":provider.identity(),"prompt":module.PROMPT,"input":data}
    receipt=root/(role+".json")
    attempt=root/(role+".attempt.json")
    if receipt.exists():
        saved=nd.read(receipt)
        if not attempt.exists() or nd.read(attempt)!=identity or saved.get("identity")!=identity:
            raise ValueError("Retained stage identity differs: "+role)
        return module.validate(saved["result"])
    if attempt.exists():
        raise ValueError("Unresolved stage attempt; no blind retry: "+role)
    nd.create_journal(attempt,identity)
    result=module.validate(provider.complete(role,module.PROMPT,data))
    nd.atomic_write(receipt,{"identity":identity,"result":result})
    return result


def prepare(root, provider, request, language, duration):
    data={"request":request,"language":language,"duration_seconds":duration}
    music=stage(root,"composer",composer,provider,data)
    words=stage(root,"lyricist",lyricist,provider,{**data,"composition":music})
    review=stage(root,"reviewer",creative_reviewer,provider,{**data,"composition":music,
                 "lyrics":words["lyrics"],"diagnostics":lyricist.diagnostics(words["lyrics"],language)})
    return {"composition":music,"lyrics":words["lyrics"],"review":review}


def validate_job(job, request, language, duration):
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",job)
            or job.lower() in {"con","prn","aux","nul"} or re.fullmatch(r"(com|lpt)[1-9]",job.lower())):
        raise ValueError("Invalid job name")
    if not request.strip() or len(request)>4000 or language not in SUPPORTED or not 30<=duration<=208:
        raise ValueError("Invalid creative request, language or duration")


def launch(repo, job, request, language, duration, *, confirm_text=False, provider_factory=TextProvider.from_env):
    validate_job(job, request, language, duration)
    if not confirm_text:
        print("Plan only; no provider or Studio calls.")
        return 0
    provider=provider_factory()
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
