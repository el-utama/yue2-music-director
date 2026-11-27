"""Private append-only listening evidence and explicit release approval.

Never modifies a historical result or treats model judgments as human approval.
Approvals are scoped to an exact audio variant hash and release ID; no publishing.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

from . import native_draft as nd, listening_director as ld, creative_core as cc
from .retained_source import load
from .audio_variant import select

DIMENSIONS=("lyrics","vocals","melody","arrangement","ending")
RATINGS=("good","needs_work","not_assessed")


def identity(source):
    return {"job":source["job"],"variant":"original",
            "result_sha256":source["evidence"]["result_sha256"],
            "audio_sha256":source["result"]["audio_sha256"]}


def _valid_identity(key):
    if not isinstance(key,dict):
        return False
    fields={"job","variant","result_sha256","audio_sha256"}
    if key.get("variant")!="original":
        fields.add("finishing_report_sha256")
    if set(key)!=fields or any(not isinstance(v,str) or not v for v in key.values()):
        return False
    cc.validate_job(key["job"],"placeholder","en",195)
    cc.validate_job(key["variant"],"placeholder","en",195)
    if key["variant"]!="original":
        if key["variant"].casefold()=="original":
            return False
        if any(len(key[k])!=64 or any(c not in "0123456789abcdef" for c in key[k])
               for k in ("result_sha256","audio_sha256","finishing_report_sha256")):
            return False
    return True


def _text(value,limit):
    return isinstance(value,str) and len(value)<=limit


def validate_payload(payload):
    if not isinstance(payload,dict):
        raise ValueError("Feedback payload must be an object")
    kind=payload.get("kind")
    if kind=="listening":
        if set(payload)!={"kind","ratings","observations","confirmed_preferences","inferred_preferences"}:
            raise ValueError("Invalid listening feedback fields")
        ratings=payload["ratings"]
        if (not isinstance(ratings,dict) or set(ratings)!=set(DIMENSIONS)
                or any(v not in RATINGS for v in ratings.values())
                or all(v=="not_assessed" for v in ratings.values())
                or not _text(payload["observations"],4000)):
            raise ValueError("Provide at least one explicitly assessed listening dimension")
        for k in ("confirmed_preferences","inferred_preferences"):
            values=payload[k]
            if (not isinstance(values,list) or len(values)>20
                    or any(not _text(v,500) or not v.strip() for v in values)):
                raise ValueError("Invalid preference notes")
    elif kind=="release_approval":
        if (set(payload)!={"kind","release","decision","note"}
                or payload["decision"] not in ("approve","revoke") or not _text(payload["note"],2000)):
            raise ValueError("Invalid explicit release decision")
        cc.validate_job(payload["release"],"placeholder","en",195)
    else:
        raise ValueError("Unknown feedback record kind")
    return payload


def history(directory):
    directory=Path(directory)
    if not directory.exists():
        return []
    entries=sorted(directory.iterdir())
    records=[]
    previous=None
    for index,path in enumerate(entries,1):
        if path.name!=f"{index:06d}.json" or not path.is_file():
            raise ValueError("Feedback ledger contains unexpected entries; preserve evidence")
        record=nd.read(path)
        if (not isinstance(record,dict) or record.get("schema") not in ("human-feedback-v1","human-feedback-v2")
                or record.get("sequence")!=index or record.get("previous_sha256")!=previous
                or record.get("recorded_by")!="human_operator"
                or not _valid_identity(record.get("source"))
                or record["schema"]!=("human-feedback-v1" if record["source"]["variant"]=="original" else "human-feedback-v2")
                or record["source"]["job"]!=directory.name
                or not _text(record.get("recorded_utc"),64)):
            raise ValueError("Feedback ledger identity differs")
        validate_payload(record["payload"])
        records.append(record)
        previous=nd._sha(path)
    return records


def status(repo,source,variant="original"):
    directory=repo/"results/feedback"/source["job"]
    records=history(directory)
    key=select(repo,source,variant)["identity"]
    matching=[r for r in records if r["source"]==key]
    approvals={}
    for r in matching:
        payload=r["payload"]
        if payload["kind"]=="release_approval":
            approvals[payload["release"]]=payload["decision"]=="approve"
    return {"schema":"human-feedback-status-v1","source":key,
            "listening":[r for r in matching if r["payload"]["kind"]=="listening"],
            "release_approvals":approvals,"other_source_records":len(records)-len(matching),
            "automatic_acceptance":False,"publishing_authorized":False}


def approval_receipt(repo,key,release):
    """Latest explicit decision; revocation is never overridden by old approval."""
    directory=repo/"results/feedback"/key["job"]
    records=history(directory)
    for record in reversed(records):
        p=record["payload"]
        if record["source"]==key and p["kind"]=="release_approval" and p["release"]==release:
            if p["decision"]!="approve":
                return None
            return {"sequence":record["sequence"],
                    "receipt_sha256":nd._sha(directory/f'{record["sequence"]:06d}.json')}
    return None


def append(repo,job,expected,payload):
    validate_payload(payload)
    source=load(repo,job)
    if not _valid_identity(expected) or expected["job"]!=job:
        raise ValueError("Invalid feedback source identity")
    variant=expected["variant"]
    try:
        selection=select(repo,source,variant)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise ValueError("Feedback source changed or unavailable; do not transfer human approval") from exc
    if selection["identity"]!=expected:
        raise ValueError("Feedback source changed; do not transfer human approval")
    base=repo/"results/feedback"
    directory=base/job
    with ld.lock(base/".active",context={"job":job,"root":directory.relative_to(repo).as_posix(),"stage":"human_feedback"}):
        # Recheck under the ledger lock before creating an exclusive receipt.
        source=load(repo,job)
        selection=select(repo,source,variant)
        if selection["identity"]!=expected or nd._sha(selection["audio"])!=expected["audio_sha256"]:
            raise ValueError("Feedback source changed; do not transfer human approval")
        records=history(directory)
        if payload["kind"]=="release_approval" and payload["decision"]=="approve":
            if not any(r["source"]==expected and r["payload"]["kind"]=="listening" for r in records):
                raise ValueError("Explicit listening feedback for this exact audio is required before release approval")
        directory.mkdir(parents=True,exist_ok=True)
        index=len(records)+1
        record={"schema":"human-feedback-v1" if variant=="original" else "human-feedback-v2","sequence":index,"source":expected,
                "recorded_utc":datetime.now(timezone.utc).isoformat(),
                "recorded_by":"human_operator","previous_sha256":nd._sha(directory/f"{index-1:06d}.json") if records else None,
                "payload":payload}
        nd.create_journal(directory/f"{index:06d}.json",record)
        if history(directory)[-1]!=record:
            raise ValueError("Feedback receipt verification failed; retain evidence")
    return record


def _interactive():
    ratings={}
    for field in DIMENSIONS:
        answer=input(f"{field} (good/needs_work/not_assessed): ").strip().lower()
        if answer not in RATINGS:
            raise ValueError("Choose one of the displayed ratings")
        ratings[field]=answer
    return {"kind":"listening","ratings":ratings,
            "observations":input("Confirmed listening observations (optional): "),
            "confirmed_preferences":[],"inferred_preferences":[]}


def launch(repo,job,*,confirm=False,record=None,approve=None,revoke=None,variant="original"):
    source=load(repo,job)
    selection=select(repo,source,variant)
    key=selection["identity"]
    print("Variant:",variant,flush=True)
    print("Audio:",selection["audio"],flush=True)
    print("SHA-256:",key["audio_sha256"],flush=True)
    if sum(x is not None for x in (record,approve,revoke))>1:
        raise ValueError("Choose only one feedback or approval operation")
    if not confirm:
        if any(x is not None for x in (record,approve,revoke)):
            raise ValueError("Writing feedback requires --confirm-run")
        print(json.dumps(status(repo,source,variant),indent=2,ensure_ascii=False))
        return 0
    if record is not None:
        if Path(record).stat().st_size>32000:
            raise ValueError("Feedback input exceeds size limit")
        supplied=nd.read(Path(record))
        if not isinstance(supplied,dict) or supplied.get("source")!=key or set(supplied)!={"source","payload"}:
            raise ValueError("Imported feedback must explicitly identify the exact retained source")
        payload=validate_payload(supplied["payload"])
        if payload["kind"]!="listening":
            raise ValueError("Release approval requires the separate interactive approval command")
    elif approve is not None or revoke is not None:
        release=approve if approve is not None else revoke
        cc.validate_job(release,"placeholder","en",195)
        action="approve" if approve is not None else "revoke"
        print("Release:",release,"Decision:",action,"for the displayed exact audio variant only.")
        if input("Type "+action.upper()+" to record this human decision: ").strip()!=action.upper():
            raise ValueError("No approval decision recorded")
        payload={"kind":"release_approval","release":release,"decision":action,"note":""}
    else:
        payload=_interactive()
    saved=append(repo,job,key,payload)
    print("Human receipt:",saved["sequence"],"; original result and audio unchanged.")
    print("No automatic acceptance, publishing or inference.")
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--feedback",required=True,metavar="JOB")
    p.add_argument("--confirm-run",action="store_true")
    p.add_argument("--record",type=Path)
    p.add_argument("--variant",default="original",help="Exact verified finishing ID or original")
    p.add_argument("--approve-release")
    p.add_argument("--revoke-release")
    a=p.parse_args()
    try:
        return launch(a.repo.resolve(),a.feedback,confirm=a.confirm_run,record=a.record,
                      approve=a.approve_release,revoke=a.revoke_release,variant=a.variant)
    except (OSError,ValueError,KeyError,TypeError,EOFError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
