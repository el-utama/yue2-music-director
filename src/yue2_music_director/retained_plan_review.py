"""Offline re-evaluation of a stopped native plan; never submit or rewrite receipts."""
import argparse
import json
from pathlib import Path
import sys
from . import native_draft as nd, artist_run as ar
from .creative_core import validate_job
from .generation_control import result_score


def inspect(repo,job,*,fit_duration=False):
    validate_job(job,"placeholder","en",195)
    root=repo/"results/autonomous"/job
    brief=nd.load_brief(root/"brief.json")
    intent=nd.read(root/"intent.json")
    production=root/"production"
    old=nd.read(production/"plan-decision.json")
    stop=nd.read(root/"plan-stop.json")
    journal=nd.read(production/"journal_plan.json")
    raw=nd.read(production/"plan-result.json")
    abc=result_score(raw,brief["seed"])
    digest=nd.digest(abc.encode("utf-8"))
    if (stop.get("decision")!=old or old.get("decision")!="stop"
            or stop.get("song_jobs")!=0 or (production/"draft").exists()
            or (root/"result.json").exists() or journal.get("state")!="COMPLETED"
            or raw.get("id")!=journal.get("id") or journal.get("score_sha256")!=digest
            or journal.get("request_sha256")!=nd.digest(nd._canonical(ar.plan_request(brief,intent)))
            or old.get("score_review",{}).get("score_sha256")!=digest
            or (production/"native-plan.abc").read_bytes()!=abc.encode("utf-8")):
        raise ValueError("Retained stopped plan identity mismatch")
    review=ar.evaluate_plan(abc,brief,intent)
    if fit_duration:
        from .duration_fit import preview
        return preview(abc,brief,intent)
    return {"schema":"retained-plan-recheck-v1","job":job,"previous_status":old["score_review"]["status"],
            "current_decision":review,"song_jobs":0,"provider_calls":0,"inference_calls":0,
            "original_receipts_changed":False,"render_authorized":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--job",required=True)
    p.add_argument("--fit-duration", action="store_true", help="Read-only bounded tempo candidate; never authorizes synthesis")
    a=p.parse_args()
    try:
        print(json.dumps(inspect(a.repo.resolve(),a.job,fit_duration=a.fit_duration),indent=2,ensure_ascii=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
