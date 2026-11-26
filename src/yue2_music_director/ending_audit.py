"""Inspect completed autonomous job artifacts and read-only Studio metadata; zero inference or mutation."""
import argparse
import json
import math
from pathlib import Path
import sys

from . import native_draft as nd, listening_director as ld
from .creative_core import validate_job
from .prosody import parse_lyrics
from .musical_review import review_score
from .native_completion import inspect_completion
from .temporal_evidence import native_song_read
from .mcp import MCPError


def cap_screen(cap, measured):
    if (type(cap) not in (int,float) or type(measured) not in (int,float)
            or not math.isfinite(cap) or not math.isfinite(measured) or cap<=0 or measured<=0):
        raise ValueError("Invalid duration evidence")
    return {"cap_seconds":cap,"measured_seconds":measured,
            "remaining_seconds":round(cap-measured,6),
            "near_or_over_cap":measured>=cap-1.0,
            "threshold_seconds":1.0,
            "note":"Conservative review flag only; not proof of truncation."}


def inspect(repo, job, url):
    validate_job(job,"placeholder","en",195)
    root=repo/"results/autonomous"/job
    identity=nd.read(root/"job.json")
    final=nd.read(root/"result.json")
    brief=nd.load_brief(root/"brief.json")
    intent=nd.read(root/"intent.json")
    production=root/"production"
    draft=production/"draft"
    report=nd.read(draft/"report.json")
    row=ld.verify_take(draft,brief,report)
    if (identity.get("job")!=job or identity.get("duration_seconds")!=brief["duration_seconds"]
            or identity.get("language")!=brief["language"] or report.get("artistic_intent")!=intent
            or final.get("schema")!="autonomous-result-v1"
            or final.get("audio")!=row["audio"] or final.get("audio_sha256")!=row["audio_sha256"]
            or final.get("song_id")!=report["song_id"]
            or final.get("brief_sha256")!=nd._sha(root/"brief.json")
            or final.get("native_report_sha256")!=nd._sha(draft/"report.json")):
        raise ValueError("Retained autonomous job identity differs")
    packet=ld.retained_packet(production,brief,intent,row)
    if final.get("listening_packet_sha256")!=nd._sha(production/"neutral-listening/review-packet.json"):
        raise ValueError("Listening packet digest differs")
    native=inspect_completion(native_song_read(url,report["song_id"]),report["song_id"],report["job_id"])
    duration=cap_screen(brief["duration_seconds"],report["acoustic"]["duration_seconds"])
    groups=parse_lyrics(brief["lyrics"])
    last=next(g for g in reversed(groups) if g["lines"])
    score_path=draft/"saved-score.abc"
    score_info={"status":"unavailable"}
    if score_path.exists():
        saved=score_path.read_text(encoding="utf-8")
        review=review_score(saved,brief["lyrics"],constraints=intent["constraints"],max_seconds=brief["duration_seconds"])
        if review!=report.get("saved_score_review"):
            raise ValueError("Saved score review differs from retained native report")
        metrics=review.get("metrics")
        score_info={"status":review["status"],"hard_violations":review["hard_violations"],
                    "soft_flags":review["soft_flags"]}
        if metrics:
            score_info["score_seconds"]=metrics["score_seconds"]
            score_info["tempo_bpm"]=metrics["tempo_bpm"]
            score_info["section_order"]=metrics["section_order"]
            score_info["last_sections"]=[{k:s[k] for k in ("section","start_seconds","duration_seconds","bars")}
                                         | {"vocal_sounding_fraction":s["vocal"]["sounding_fraction"]}
                                         for s in metrics["sections"][-3:]]
    screen=report["lyric_screen"]
    primary=screen["primary_metric"]
    return {"schema":"ending-audit-v1","job":job,"duration":duration,"native_completion":native,
            "lyric_structure":{"sections":len(groups),"sung_lines":sum(len(g["lines"]) for g in groups),
                              "last_sung_section":last["name"],"last_section_lines":len(last["lines"])},
            "score":score_info,"lyric_screen":{"metric":primary,"disagreement_rate":screen[primary]["disagreement_rate"]},
            "listening_excerpts":len(packet["observations"]),
            "interpretation_limits":["Score clock is not acoustic alignment.",
              "ASR disagreement is not verified lyric omission or pronunciation.",
              "Mono MOSS cannot assess stereo image; excerpt boundary is not proof of song truncation."],
            "audio_changed":False,"inference_calls":0,"automatic_repair_authorized":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--job",required=True)
    p.add_argument("--url",required=True)
    a=p.parse_args()
    try:
        print(json.dumps(inspect(a.repo.resolve(),a.job,a.url),indent=2,ensure_ascii=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,StopIteration,MCPError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
