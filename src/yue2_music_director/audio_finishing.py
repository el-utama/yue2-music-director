"""Non-destructive, explicitly confirmed offline finishing of a retained song."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from . import native_draft as nd, listening_director as ld, creative_core as cc
from . import finish_audio as fa
from .retained_source import load

DEFAULT_VARIANT="gain-v1"


def contract_for(source,variant):
    return {"schema":"audio-finishing-contract-v1","policy":fa.POLICY,
            "job":source["job"],"variant":variant,"source_variant":"original",
            "source_audio_sha256":source["result"]["audio_sha256"],
            "source_result_sha256":source["evidence"]["result_sha256"]}


def _sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)


def _read_plan(root,contract):
    plan=nd.read(root/"plan.json")
    if (not isinstance(plan,dict) or plan.get("schema")!="audio-finishing-plan-v1"
            or plan.get("contract")!=contract
            or not isinstance(plan.get("tool_versions"),dict)
            or set(plan["tool_versions"])!={"ffmpeg","ffprobe"}
            or not all(isinstance(v,str) and v for v in plan["tool_versions"].values())):
        raise ValueError("Retained finishing plan identity differs")
    before=plan["source_measurement"]
    fa.validate_measurement(before["acoustic"],before["geometry"])
    if before["acoustic"]["sha256"]!=contract["source_audio_sha256"]:
        raise ValueError("Retained finishing source hash differs")
    gain=fa.plan_gain(before["acoustic"])
    if (plan.get("gain_db")!=gain
            or plan.get("action")!=("no_change" if gain==0 else "attenuate")
            or (plan.get("expected_pcm_sha256") is not None if gain==0
                else not _sha(plan.get("expected_pcm_sha256")))):
        raise ValueError("Retained finishing gain plan differs")
    return plan


def _report(root,plan,after=None,pcm=None):
    gain=plan["gain_db"]
    if gain==0:
        if after is not None or pcm is not None:
            raise ValueError("Unexpected no-change candidate")
    else:
        fa.verify_candidate(plan["source_measurement"],after,gain)
        if pcm!=plan["expected_pcm_sha256"]:
            raise ValueError("Decoded candidate is not the exact planned fixed-gain PCM")
    return {"schema":"audio-finishing-result-v1","contract":plan["contract"],
            "plan_sha256":nd._sha(root/"plan.json"),"gain_db":gain,
            "status":"no_change" if gain==0 else "candidate_verified",
            "source_measurement":plan["source_measurement"],"candidate_measurement":after,
            "candidate_file":None if gain==0 else "candidate.flac",
            "candidate_audio_sha256":None if gain==0 else after["acoustic"]["sha256"],
            "candidate_pcm_sha256":pcm,"timeline_preserved":True,
            "clipping_repaired":False,"artistic_improvement_verified":False,
            "automatic_acceptance":False,"release_approved":False,
            "preferred_variant":"original",
            "studio_jobs":0,"recognition_calls":0,"moss_calls":0,"provider_calls":0,
            "library_mutations":0,"publishing_authorized":False}


def _verify_files(root,source,plan):
    for path in (root,root/"plan.json",root/"report.json",root/"candidate.flac",root/".candidate-incomplete.flac"):
        if path.is_symlink():
            raise ValueError("Unexpected symlink in finishing output")
    if nd._sha(source["audio"])!=plan["contract"]["source_audio_sha256"]:
        raise ValueError("Original source changed; preserve evidence")


def verify(root,source,contract):
    """Verify completed immutable output without rerendering or FFmpeg."""
    plan=_read_plan(root,contract)
    _verify_files(root,source,plan)
    result=nd.read(root/"report.json")
    expected=_report(root,plan,result.get("candidate_measurement"),result.get("candidate_pcm_sha256"))
    if result!=expected:
        raise ValueError("Retained finishing report differs")
    target=root/"candidate.flac"
    names={"plan.json","report.json"}
    if plan["gain_db"]!=0:
        names.add("candidate.flac")
        if (not target.is_file() or target.samefile(source["audio"])
                or nd._sha(target)!=result["candidate_audio_sha256"]):
            raise ValueError("Retained finishing candidate identity differs")
    if {p.name for p in root.iterdir()}!=names:
        raise ValueError("Unexpected retained finishing artifacts")
    return result


def launch(repo,job,*,variant=DEFAULT_VARIANT,confirm=False):
    cc.validate_job(variant,"placeholder","en",195)
    source=load(repo,job)
    contract=contract_for(source,variant)
    base=repo/"results/audio-finishing"
    root=base/job/variant
    print("Original:",source["audio"],flush=True)
    print("SHA-256:",contract["source_audio_sha256"],flush=True)
    print("Finishing output:",root,flush=True)
    if root.exists() and root.is_symlink():
        raise ValueError("Unexpected finishing output symlink")
    if (root/"report.json").exists():
        result=verify(root,source,contract)
        print("Retained result verified:",result["status"],flush=True)
        return 0
    if not confirm:
        if root.exists():
            plan=_read_plan(root,contract)
            _verify_files(root,source,plan)
            print("Incomplete local finishing plan retained; confirmation may verify an existing candidate.",flush=True)
        else:
            estimate=fa.plan_gain(source["report"]["acoustic"])
            print("Estimated fixed gain from retained metrics:",estimate,"dB",flush=True)
        print("Plan only. No output written or new inference. Confirm to measure and finish.",flush=True)
        return 0
    with ld.lock(base/".active",context={"job":job,"root":root.relative_to(repo).as_posix(),"stage":"audio_finishing"}):
        source=load(repo,job)
        if contract_for(source,variant)!=contract:
            raise ValueError("Original retained source changed")
        if (root/"report.json").exists():
            verify(root,source,contract)
            return 0
        ffmpeg,ffprobe,versions=fa.tools()
        if root.exists():
            plan=_read_plan(root,contract)
            if plan["tool_versions"]!=versions:
                raise ValueError("FFmpeg version differs from incomplete plan; use a new explicit variant ID")
        else:
            before=fa.measure(source["audio"],ffmpeg,ffprobe,contract["source_audio_sha256"])
            gain=fa.plan_gain(before["acoustic"])
            expected_pcm=None if gain==0 else fa.pcm_hash(source["audio"],ffmpeg,gain=gain)
            if nd._sha(source["audio"])!=contract["source_audio_sha256"]:
                raise ValueError("Original source changed during gain planning")
            plan={"schema":"audio-finishing-plan-v1","contract":contract,
                  "action":"no_change" if gain==0 else "attenuate","gain_db":gain,
                  "source_measurement":before,"expected_pcm_sha256":expected_pcm,
                  "tool_versions":versions}
            root.mkdir(parents=True,exist_ok=False)
            nd.create_journal(root/"plan.json",plan)
        _verify_files(root,source,plan)
        gain=plan["gain_db"]
        target=root/"candidate.flac"
        partial=root/".candidate-incomplete.flac"
        after=pcm=None
        if gain!=0:
            if target.exists() and partial.exists():
                raise ValueError("Multiple candidate artifacts; preserve and inspect")
            candidate=target if target.exists() else partial
            if not candidate.exists():
                print("Applying fixed attenuation:",gain,"dB",flush=True)
                fa.render(source["audio"],partial,gain,ffmpeg)
            if not candidate.is_file() or candidate.samefile(source["audio"]):
                raise ValueError("Invalid candidate path")
            after=fa.measure(candidate,ffmpeg,ffprobe)
            pcm=fa.pcm_hash(candidate,ffmpeg)
            fa.verify_candidate(plan["source_measurement"],after,gain)
            if pcm!=plan["expected_pcm_sha256"]:
                raise ValueError("Decoded candidate is not the exact planned fixed-gain PCM")
            if nd._sha(candidate)!=after["acoustic"]["sha256"]:
                raise ValueError("Candidate changed during verification")
            _verify_files(root,source,plan)
            if candidate==partial:
                if target.exists():
                    raise ValueError("Candidate destination appeared; do not overwrite")
                partial.rename(target)
        elif target.exists() or partial.exists():
            raise ValueError("Unexpected candidate for no-change plan")
        result=_report(root,plan,after,pcm)
        _verify_files(root,source,plan)
        if target.exists() and nd._sha(target)!=result["candidate_audio_sha256"]:
            raise ValueError("Candidate changed before receipt")
        names={"plan.json"}|({"candidate.flac"} if gain!=0 else set())
        if {p.name for p in root.iterdir()}!=names:
            raise ValueError("Unexpected artifacts in finishing directory")
        nd.atomic_write(root/"report.json",result)
        verify(root,source,contract)
    print("Finishing:",result["status"],flush=True)
    print("Original preserved; no clipping repair or artistic approval claimed.",flush=True)
    print("Report:",root/"report.json",flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--finish",required=True,metavar="JOB")
    p.add_argument("--finish-id",default=DEFAULT_VARIANT)
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        return launch(a.repo.resolve(),a.finish,variant=a.finish_id,confirm=a.confirm_run)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        print("Original and existing local evidence retained; never overwrite a failed candidate.",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
