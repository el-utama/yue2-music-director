"""Inspect local owned mutexes and explicitly recover only verified stale markers."""
import argparse
import json
from pathlib import Path, PurePosixPath
import sys

from . import operation_lock as ol

LOCKS={"autonomous":"results/autonomous/.active","drafts":"results/drafts/.active",
       "critic":"results/.critic-active","creative":"results/creative/.active",
       "artwork":"results/artwork/.active","exports":"results/exports/.active",
       "feedback":"results/feedback/.active","finishing":"results/audio-finishing/.active",
       "release-assembly":"results/release-assembly/.active"}


def journals(repo,owner):
    context=owner.get("context")
    relative=context.get("root") if isinstance(context,dict) else None
    if not isinstance(relative,str) or "\\" in relative or ":" in relative:
        return {"status":"unknown_context","entries":[]}
    parts=PurePosixPath(relative).parts
    if len(parts)<2 or parts[0]!="results" or any(p in (".","..") for p in parts):
        return {"status":"unknown_context","entries":[]}
    root=repo.joinpath(*parts).resolve()
    if not root.is_relative_to((repo/"results").resolve()):
        return {"status":"unknown_context","entries":[]}
    if not root.exists():
        return {"status":"no_artifacts","entries":[]}
    if not root.is_dir():
        return {"status":"unverified_journals","entries":[]}
    entries=[]
    for path in root.rglob("*.json"):
        if not (path.name.startswith("journal_") or path.name.endswith(".attempt.json")
                or path.name in ("result.json","plan-stop.json","plan.json","report.json","receipt.json","submission.json")):
            continue
        if len(entries)>=200 or path.is_symlink() or path.stat().st_size>2_000_000:
            return {"status":"unverified_journals","entries":entries}
        try:
            value=json.loads(path.read_bytes())
            if not isinstance(value,dict):
                raise ValueError("Not an object")
        except (OSError,ValueError,UnicodeError):
            return {"status":"unverified_journals","entries":entries}
        state=value.get("state",value.get("status","present"))
        if not isinstance(state,str) or len(state)>80:
            state="present"
        entries.append({"path":path.relative_to(repo).as_posix(),"state":state})
    return {"status":"inspected","entries":sorted(entries,key=lambda e:e["path"])}


def inspect(repo,name):
    if name not in LOCKS:
        raise ValueError("Unknown local lock")
    result=ol.inspect(repo/LOCKS[name])
    result["lock"]=name
    result["journals"]=journals(repo,result["owner"]) if "owner" in result else {"status":"unknown_context","entries":[]}
    result["journal_replay_authorized"]=False
    return result


def recover(repo,name,expected_sha,*,confirm=False):
    before=inspect(repo,name)
    if (before.get("status")!="stale_owner" or before.get("marker_sha256")!=expected_sha
            or before["journals"]["status"] not in ("inspected","no_artifacts")):
        raise ValueError("Exact stale process and known journal context required")
    if not confirm:
        raise ValueError("Explicit lock recovery confirmation required")
    return ol.recover(repo/LOCKS[name],expected_sha,repo/"results/lock-recovery"/name,
                      confirm=True,journal_summary=before["journals"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect-lock",choices=LOCKS)
    group.add_argument("--recover-lock",choices=LOCKS)
    p.add_argument("--expected-sha")
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    repo=a.repo.resolve()
    try:
        name=a.inspect_lock or a.recover_lock
        print(json.dumps(inspect(repo,name),indent=2,ensure_ascii=False),flush=True)
        if a.recover_lock:
            if not a.confirm_run or not a.expected_sha:
                raise ValueError("Recovery requires inspected SHA and --confirm-run")
            print("This only archives and removes the verified stale mutex. Native/provider journals remain authoritative.")
            if input("Type RECOVER after checking the displayed journal states: ").strip()!="RECOVER":
                raise ValueError("No recovery authorized")
            receipt=recover(repo,name,a.expected_sha,confirm=True)
            print("Recovery receipt:",receipt)
            print("No journal replay, Studio cancellation or new submission authorized.")
        return 0
    except (OSError,ValueError,KeyError,TypeError,EOFError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
