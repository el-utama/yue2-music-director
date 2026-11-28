"""Offline re-evaluation of a stopped native plan; never submit or rewrite receipts."""
import argparse
import json
from pathlib import Path
import sys
from . import native_draft as nd, artist_run as ar
from .creative_core import validate_job
from .generation_control import result_score
from .music import NOTE, parse_score, patch_score


def preview_intro(abc, brief, intent, original):
    """Assess a narrowly scoped, vocal-free intro candidate in memory."""
    report = {"schema": "intro-rest-preview-v1", "status": "not_eligible",
              "studio_calls": 0, "provider_calls": 0, "render_authorized": False}
    hard = original["hard_violations"]
    soft = original["soft_flags"]
    expected = [{"code": "constraint_mismatch", "field": field,
                 "expected": "instrumental_intro", "actual": "unassessed"}
                for field in ("opening", "opening_timing")]
    if (len(hard) != len(expected) or any(issue not in hard for issue in expected)
            or len(soft) != 1
            or soft[0].get("code") != "notated_sung_sequence_differs"
            or soft[0].get("missing") != [] or soft[0].get("extra") != ["intro#1"]):
        return {**report, "reason": "Requires only a vocal part in a planned instrumental intro"}
    opening = original["metrics"]["opening_evidence"]
    if opening["intro_accompaniment"] != "notated_ins_activity":
        return {**report, "reason": "Intro has no confirmed instrumental notation"}

    score = parse_score(abc, native=True)
    notes = [note for note in score.events
             if note.voice == "Vocal" and note.kind == "note" and note.section == "intro#1"]
    if not notes or notes[-1].tied:
        return {**report, "reason": "Cannot isolate the intro vocal notes from the next section"}
    edits = [{"line": note.line, "start": note.start, "end": note.end, "old": note.raw,
              "new": "z" + (NOTE.fullmatch(note.raw).group("dur") or "")}
             for note in notes]
    candidate = patch_score(score, edits)
    review = ar.evaluate_plan(candidate, brief, intent)
    candidate_review = review["score_review"]
    candidate_metrics = candidate_review["metrics"]
    if (review["decision"] != "retain" or candidate_metrics is None
            or candidate_metrics["score_seconds"] != original["metrics"]["score_seconds"]):
        return {**report, "reason": "Candidate did not pass full score review with unchanged duration",
                "opening_evidence": (candidate_metrics or {}).get("opening_evidence"),
                "hard_violations": candidate_review["hard_violations"],
                "soft_flags": candidate_review["soft_flags"]}
    return {**report, "status": "candidate_available",
            "vocal_notes_replaced_by_rests": len(edits),
            "score_seconds": candidate_metrics["score_seconds"],
            "opening_evidence": candidate_metrics["opening_evidence"]}


def inspect(repo,job,*,fit_duration=False,preview_instrumental_intro=False):
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
        identity=nd.read(root/"job.json")
        return preview(abc,brief,intent,request=identity["request"])
    if preview_instrumental_intro:
        return preview_intro(abc, brief, intent, review["score_review"])
    return {"schema":"retained-plan-recheck-v1","job":job,"previous_status":old["score_review"]["status"],
            "current_decision":review,"song_jobs":0,"provider_calls":0,"inference_calls":0,
            "original_receipts_changed":False,"render_authorized":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--job",required=True)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--preview-intro", action="store_true", help="Assess replacing intro vocal notes with rests; no synthesis")
    mode.add_argument("--fit-duration", action="store_true", help="Read-only bounded tempo candidate; never authorizes synthesis")
    a=p.parse_args()
    try:
        result = inspect(a.repo.resolve(), a.job, fit_duration=a.fit_duration,
                         preview_instrumental_intro=a.preview_intro)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
