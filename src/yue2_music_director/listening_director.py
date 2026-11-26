"""Bounded generation-first director with blind, advisory audio observations."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import math
import os
from pathlib import Path
import subprocess
import sys

from . import artist_run, audio_critic as ac, native_draft as nd
from .mcp import Client, MCPError, configured_endpoint
from .studio_idle import assert_idle, wait_for_idle

FIELDS = ("VOCAL", "INSTRUMENTS", "PHRASING", "DYNAMICS", "CHANGES", "TAIL", "LIMITS")
PROMPT = (
    "Describe only the audio excerpt you actually hear, without guessing the song title, "
    "artist, lyrics, intended genre, exact tempo, key, or whether it is human-made. "
    "Do not assume this is the start or end of a complete song. Describe changes within "
    "the supplied excerpt, not imaginary sections. Distinguish audible details from "
    "uncertainty; use unknown where you cannot tell. Do not score quality or diagnose clipping. "
    "Write exactly one short plain text line per field, in FIELD: description format. "
    "No JSON, no bullets.\n"
    "VOCAL: audible voices and delivery\n"
    "INSTRUMENTS: audible instrumental textures\n"
    "PHRASING: audible rhythmic phrasing or space\n"
    "DYNAMICS: audible intensity and contrast\n"
    "CHANGES: audible changes within this excerpt\n"
    "TAIL: what is heard at this excerpt's boundary, not a whole-song verdict\n"
    "LIMITS: ambiguity or limitations"
)


def parse_observations(raw):
    """Partial extraction, no evidence fabrication or semantic validation."""
    found = {}
    duplicates = set()
    for line in raw.splitlines():
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or key not in FIELDS:
            continue
        if key in found:
            duplicates.add(key)
        found[key] = value
    rows = []
    for key in FIELDS:
        value = found.get(key)
        valid = (key not in duplicates and isinstance(value, str) and
                 0 < len(value) <= 1000 and value.lower().rstrip(".") != "unknown")
        rows.append({"field": key, "observation": value if valid else None,
                     "status": "model_reported_unverified" if valid else "unknown"})
    count = sum(row["observation"] is not None for row in rows)
    return ("parsed_unvalidated" if count == len(FIELDS) else
            "partial_unvalidated" if count else "unparseable"), rows


def inputs(repo, demo=False):
    folder = repo / ("examples/listening-director" if demo else "local")
    brief = nd.load_brief(folder / "brief.json")
    path = folder / "intent.json"
    if path.stat().st_size > 100000:
        raise ValueError("Intent exceeds size limit")
    intent = artist_run.validate_intent(nd.read(path))
    if artist_run.route_for(intent) != "direct_native":
        raise ValueError("Listening director requires direct-native intent; use the existing artist runner for score constraints")
    if any(c["mode"] == "must" for c in intent["constraints"].values()):
        raise ValueError("Hard score constraints require reviewed native generation")
    if brief["duration_seconds"] > 208:
        raise ValueError("Listening director cap is 208 seconds (two bounded CPU excerpts)")
    return brief, intent


def verify_take(draft, brief, report):
    journal = nd.read(draft / "journal_song.json")
    request = nd.request_for(brief)
    route=report.get("generation_path")
    if route=="reviewed_native":
        # Preserve raw source identity (read_text normalizes CRLF on Windows).
        abc=(draft.parent/"native-plan.abc").read_bytes().decode("utf-8")
        plan=nd.read(draft.parent/"journal_plan.json")
        decision=nd.read(draft.parent/"plan-decision.json")
        score_sha=nd.digest(abc.encode("utf-8"))
        if plan.get("state")!="COMPLETED" or plan.get("score_sha256")!=score_sha:
            raise ValueError("Retained reviewed score identity mismatch: planner receipt")
        if decision.get("decision")!="retain" or decision.get("score_review",{}).get("score_sha256")!=score_sha:
            raise ValueError("Retained reviewed score identity mismatch: plan decision")
        pre=nd.read(draft/"score-review.json")
        if (report.get("score_review")!=pre or pre.get("score_sha256")!=score_sha
                or pre.get("structural_review")!=decision
                or not isinstance(pre.get("midi"),dict) or not pre["midi"]):
            raise ValueError("Retained reviewed score identity mismatch: pre-render review")
        if report.get("saved_score_verified") is not True or report.get("actual_lyric_conditioning_verified") is not True:
            raise ValueError("Retained reviewed score identity mismatch: conditioning flags")
        saved=(draft/"saved-score.abc").read_bytes().decode("utf-8")
        post=nd.read(draft/"saved-score-review.json")
        if (report.get("saved_score_review")!=post
                or post.get("score_sha256")!=nd.digest(saved.encode("utf-8"))):
            raise ValueError("Retained reviewed score identity mismatch: saved score receipt")
        # Studio may normalize whitespace or notation while importing.
        # Compare musical semantics, not byte equality between two independently
        # hashed artifacts. This includes synchronized meter and key timelines.
        if nd.score_signature(saved,native=True)!=nd.score_signature(abc,native=True):
            raise ValueError("Retained reviewed score identity mismatch: musical semantics")
        request["abc"]=abc
    elif route!="direct_native":
        raise ValueError("Unsupported retained artistic generation route")
    sha = nd.digest(nd._canonical(request))
    if (nd.read(draft / "report.json") != report or
            nd.read(draft / "brief.json") != brief or nd.read(draft / "request.json") != request or
            report.get("schema") != "native-draft-v1" or
            report.get("automatic_acceptance") is not False or
            report.get("brief_sha256") != nd.digest(nd._canonical(brief)) or
            report.get("request_sha256") != sha or journal.get("request_sha256") != sha or
            journal.get("state") != "COMPLETED" or
            any(not isinstance(report.get(k), str) or not report[k] or journal.get(k) != report[k]
                for k in ("job_id", "song_id", "audio_sha256"))):
        raise ValueError("Completed native take identity mismatch")
    audio = Path(report["audio"])
    seconds = report["acoustic"]["duration_seconds"]
    if (not audio.is_absolute() or not audio.is_file() or audio.suffix.lower() != ".flac" or
            nd._sha(audio) != report["audio_sha256"] or
            report["acoustic"]["sha256"] != report["audio_sha256"] or
            type(seconds) not in (int, float) or not math.isfinite(seconds) or not 1 <= seconds <= 210):
        raise ValueError("Audio identity or listening duration mismatch; preserve take")
    return {"arm": "baseline", "audio": str(audio), "audio_sha256": report["audio_sha256"],
            "acoustic": report["acoustic"], "lyric_screen": report["lyric_screen"]}


def freeze(out, row):
    contract = {"schema": "neutral-listening-v1", "audio_sha256": row["audio_sha256"],
                "ranges": [list(x) for x in ac.excerpt_ranges(row["acoustic"]["duration_seconds"])],
                "prompt": PROMPT, "provider": "Studio-v5.0-MOSS-Q4_K_M/CPU",
                "automatic_acceptance": False}
    out.mkdir(parents=True, exist_ok=True)
    prompt = out / "prompt.txt"
    path = out / "contract.json"
    if path.exists():
        if nd.read(path) != contract or prompt.read_text(encoding="utf-8") != PROMPT:
            raise ValueError("Retained listening contract differs")
    else:
        if any(out.iterdir()):
            raise ValueError("Incomplete listening contract; retain and inspect")
        prompt.write_text(PROMPT, encoding="utf-8")
        nd.atomic_write(path, contract)
    return contract


def review_packet(brief, intent, row, contract, evidence):
    """Intent is revealed only in the downstream review packet, not in MOSS prompts."""
    observations = []
    for item in evidence:
        end = item["start_seconds"] + item["duration_seconds"]
        observations.append({**item, "end_seconds": end,
            "contains_recording_end": abs(end - row["acoustic"]["duration_seconds"]) < 0.001})
    return {"schema": "director-review-v1", "brief": brief, "artistic_intent": intent,
            "audio": row["audio"], "audio_sha256": row["audio_sha256"],
            "neutral_contract": contract, "observations": observations,
            "acoustic": row["acoustic"], "lyric_screen": row["lyric_screen"],
            "artistic_acceptance": "unverified", "automatic_acceptance": False,
            "automatic_winner": False, "revision_authorized": False,
            "next_action": "director_compare_intent_and_observations",
            "review_guidance": [
                "Identify concrete audible strengths and issues, cite excerpt and model-reported evidence; unknown when insufficient.",
                "Do not infer whole-song structure from a single excerpt or equate ASR disagreement with pronunciation.",
                "Separate technical headroom from audible artifacts; mono observations cannot judge stereo mix.",
                "Propose a selective revision only with credible evidence and preserve lyrics and strengths; require separate approval.",
                "Retain original recording; no automated quality score or repair."
            ]}


@contextmanager
def lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        yield
    finally:
        path.unlink()


def retained_packet(root, brief, intent, row):
    """Validate completed local listening receipts without invoking Studio or MOSS."""
    out = root / "neutral-listening"
    contract = freeze(out, row)
    runtime = nd.read(out / "runtime.json")
    evidence = []
    for j, (start, duration) in enumerate(contract["ranges"], 1):
        stem = "arm-1-part-" + str(j)
        raw = out / (stem + ".txt")
        receipt = nd.read(out / (stem + ".json"))
        identity = {"audio_sha256": row["audio_sha256"], "start_seconds": start,
                    "duration_seconds": duration, "prompt_sha256": nd._sha(out / "prompt.txt"),
                    "runtime": runtime}
        if receipt.get("identity") != identity or receipt.get("response_sha256") != nd._sha(raw):
            raise ValueError("Retained listening receipt differs")
        response = raw.read_text(encoding="utf-8", errors="replace")
        status, checks = parse_observations(response)
        evidence.append({"arm": row["arm"], "start_seconds": start, "duration_seconds": duration,
                         "format_status": status, "checks": checks, "raw_response": response})
    packet = nd.read(out / "review-packet.json")
    if packet != review_packet(brief, intent, row, contract, evidence):
        raise ValueError("Retained review packet differs")
    return packet


def listen(root, brief, intent, row, url):
    if (root / "neutral-listening/review-packet.json").exists():
        return retained_packet(root, brief, intent, row)
    out = root / "neutral-listening"
    contract = freeze(out, row)
    installed = ac.inventory([row])
    nd.atomic_write(out / "inventory.json", installed)
    client = Client(configured_endpoint(url), timeout=90).connect()
    def barrier():
        wait_for_idle(client, "neutral CPU listening")
        assert_idle(client)
    evidence = ac.evaluate(out, [row], installed, parse=parse_observations,
                           before_excerpt=barrier)
    packet = review_packet(brief, intent, row, contract, evidence)
    nd.atomic_write(out / "review-packet.json", packet)
    print("Local audio:", row["audio"], flush=True)
    print("Director review packet:", out / "review-packet.json", flush=True)
    for item in packet["observations"]:
        print("Excerpt:", item["start_seconds"], "to", item["end_seconds"], flush=True)
        print(item["raw_response"], flush=True)
    return packet


def launch(repo, url, *, demo=False, confirm=False):
    brief, intent = inputs(repo, demo)
    print("Director:", brief["title"], flush=True)
    print("Concept:", intent["concept"], flush=True)
    print("Budget: one native song, one local ASR, two local CPU listening excerpts.", flush=True)
    if not confirm:
        print("Plan only. No inference or Studio calls.", flush=True)
        return 0
    drafts = repo / "results/drafts"
    root = drafts / ("artist-" + nd.digest(nd._canonical(brief)))
    with lock(drafts / ".active"), lock(repo / "results/.critic-active"):
        report = artist_run.run(brief, intent, root, url)
        row = verify_take(root / "draft", brief, report)
        listen(root, brief, intent, row, url)
        print("Retained original; artistic review pending. No automatic revision or finishing.", flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--revise-arrangement", action="store_true", help="One separately approved demo arrangement revision")
    parser.add_argument("--confirm-run", action="store_true",
                        help="Authorize one native song, ASR and two CPU listening excerpts")
    args = parser.parse_args()
    try:
        if args.revise_arrangement:
            if not args.demo:
                raise ValueError("Arrangement revision currently supports the retained demo only")
            from .arrangement_refinement import launch_revision
            return launch_revision(args.repo.resolve(), args.url, confirm=args.confirm_run)
        return launch(args.repo.resolve(), args.url, demo=args.demo, confirm=args.confirm_run)
    except (OSError, ValueError, KeyError, TypeError, MCPError, subprocess.SubprocessError) as exc:
        print("ERROR:", exc, file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
