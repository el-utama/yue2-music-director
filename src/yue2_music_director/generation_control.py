"""Bounded first-generation control study: compare two native score plans, no song_create."""
import argparse
import os
import re
import sys
import time
from fractions import Fraction
from pathlib import Path

from .experiments import _canonical, _sha, _write, reference_configuration
from .mcp import Client, MCPError, configured_endpoint, unpack
from .music import parse_score, ScoreError
from .native_draft import load_brief, request_for, create_journal, read
from .prosody import parse_lyrics

SCHEMA = "generation-control-study-v1"


def plan_requests(brief):
    base = {k: brief[k] for k in ("style", "lyrics")}
    base.update(cot="full", lm_seed=brief["seed"], lm_batch_size=1)
    return {"A": base, "B": {**base, "harmony": {"follow_lyrics": True}}}


def inspect_plan(abc, brief):
    """Structural evidence only; no syllable-to-note or musical-quality claim."""
    groups = parse_lyrics(brief["lyrics"])
    wanted = [f"{g['name']}#{g['occurrence']}" for g in groups if g["lines"]]
    try:
        score = parse_score(abc)
    except (ScoreError, ValueError, KeyError) as exc:
        return {"status": "unsupported_or_invalid_score", "reason": str(exc),
                "eligible_for_render": False}
    actual = list(dict.fromkeys(score.sections["Vocal"]))
    note_counts = {s: 0 for s in actual}
    for e in score.events:
        if e.voice == "Vocal" and e.kind == "note":
            note_counts[e.section] += 1
    # Unrequested purely instrumental sections are legitimate. An unrequested
    # vocal-note section is not; an expected sung section without notes fails.
    sung = [s for s in actual if note_counts[s] > 0]
    # Count by *sung* occurrence so an instrumental bridge/chorus does not
    # shift later lyric matches silently: any extra note-bearing block fails.
    missing = [s for s in wanted if not note_counts.get(s)]
    extra = [s for s in sung if s not in wanted]
    flags = []
    if sung != wanted:
        flags.append("sung_section_sequence_mismatch")
    explicit = [f"{g['name']}#{g['occurrence']}" for g in groups]
    if [s for s in actual if s in explicit] != explicit:
        flags.append("explicit_section_order_mismatch")
    if score.sections["Vocal"] != score.sections["Ins"]:
        flags.append("voice_section_mismatch")
    seconds = None
    try:
        m = re.fullmatch(r"1/4\s*=\s*(\d+)", score.headers["Q"])
        if not m or int(m[1]) <= 0:
            raise ValueError("Unsupported tempo")
        seconds = float(Fraction(score.headers["M"]) * 240 *
                        score.counts["Vocal"] / int(m[1]))
        if seconds > brief["duration_seconds"]:
            flags.append("score_exceeds_requested_duration_cap")
    except (KeyError, ValueError, ZeroDivisionError):
        flags.append("duration_not_assessable")
    if score.warnings:
        flags.append("parser_warnings_require_review")
    return {"status": "review_required" if flags else "structural_pass",
            "eligible_for_render": not flags, "flags": flags, "missing_sung_sections": missing,
            "extra_sung_sections": extra, "expected_sung_sections": wanted,
            "actual_sung_sections": sung, "score_sections": actual,
            "vocal_note_events": note_counts, "score_seconds": seconds,
            "parser_warnings": score.warnings,
            "naturalness_verified": False, "phonetic_alignment_verified": False}


def result_score(result, seed):
    plans = result.get("plans")
    if (result.get("status") != "done" or not isinstance(plans, list)
            or len(plans) != 1 or not isinstance(plans[0], dict)
            or type(plans[0].get("lm_seed")) is not int or plans[0]["lm_seed"] != seed
            or not isinstance(plans[0].get("abc"), str) or not plans[0]["abc"].strip()
            or result.get("abc") != plans[0]["abc"] or result.get("lm_seed") != seed):
        raise ValueError("Score result does not establish one matching native plan and seed")
    return plans[0]["abc"]


def preflight(client, brief, requests):
    tools = {t["name"]: t.get("inputSchema", {}) for t in client.tools()}
    need = {"score_compose", "score_job_get", "studio_status", "song_defaults",
            "studio_capabilities", "models_status", "engine_options_get"}
    if not need <= tools.keys():
        raise ValueError("Required native score or reference tools unavailable")
    schema = tools["score_compose"]
    props = schema.get("properties", {})
    if not set(requests["B"]) <= props.keys() or "follow_lyrics" not in props.get("harmony", {}).get("properties", {}):
        raise ValueError("Installed score_compose does not expose follow_lyrics")
    return reference_configuration(client, unpack(client.call("studio_status", {})),
                                   request_for(brief), unpack(client.call("song_defaults", {})),
                                   unpack(client.call("studio_capabilities", {})))


def run(brief, root, client, *, max_polls=120, sleep=time.sleep):
    requests = plan_requests(brief)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": SCHEMA, "brief_sha256": _sha(_canonical(brief)),
                "requests": requests, "budget": {"score_jobs": 2, "full_song_jobs": 0}}
    path = root / "manifest.json"
    if path.exists():
        if read(path) != manifest:
            raise ValueError("Study identity mismatch")
    else:
        _write(path, manifest)
    reports = {}
    for arm, request in requests.items():
        journal_path = root / f"journal_{arm}.json"
        raw_path = root / f"result_{arm}.json"
        if journal_path.exists():
            journal = read(journal_path)
            if journal.get("request_sha256") != _sha(_canonical(request)) or not journal.get("id"):
                raise ValueError("Uncertain or mismatched score submission; never resubmit")
        else:
            config = preflight(client, brief, requests)
            if arm == "B" and config != read(root / "journal_A.json")["configuration"]:
                raise ValueError("Reference configuration changed between plans")
            journal = {"request_sha256": _sha(_canonical(request)), "configuration": config,
                       "state": "SUBMISSION_ATTEMPTED"}
            create_journal(journal_path, journal)
            print("Submitting score-only arm", arm, flush=True)
            raw = unpack(client.call("score_compose", request))
            _write(root / f"receipt_{arm}.json", raw)
            if (not isinstance(raw, dict) or not isinstance(raw.get("id"), str)
                    or not raw["id"] or raw.get("status") not in ("running", "done")):
                raise ValueError("Ambiguous score receipt; never resubmit")
            journal.update(id=raw["id"], state="SUBMITTED")
            _write(journal_path, journal)
        if raw_path.exists():
            result = read(raw_path)
        else:
            for attempt in range(max_polls + 1):
                result = unpack(client.call("score_job_get", {"job_id": journal["id"]}))
                if not isinstance(result, dict) or result.get("id") != journal["id"]:
                    raise ValueError("Score job identity mismatch")
                if result.get("status") == "done":
                    break
                if result.get("status") != "running" or attempt == max_polls:
                    raise ValueError("Score not completed within budget; retain journal, never resubmit")
                sleep(3)
            result_score(result, brief["seed"])
            _write(raw_path, result)
        if result.get("id") != journal["id"]:
            raise ValueError("Retained score job identity mismatch")
        abc = result_score(result, brief["seed"])
        score_path = root / f"score_{arm}.abc"
        if score_path.exists() and score_path.read_text(encoding="utf-8") != abc:
            raise ValueError("Retained score differs from native result")
        if not score_path.exists():
            score_path.write_text(abc, encoding="utf-8", newline="\n")
        reports[arm] = inspect_plan(abc, brief)
        journal.update(state="COMPLETED", score_sha256=_sha(abc.encode()))
        _write(journal_path, journal)
        print(arm, reports[arm], flush=True)
    report = {"schema": SCHEMA, "arms": reports, "budget": manifest["budget"],
              "automatic_render": False, "naturalness_verified": False,
              "next_action": "review_score_evidence_before_any_full_song"}
    _write(root / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--confirm-plans", action="store_true")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        brief = load_brief(repo / "local/brief.json")
        if not args.confirm_plans:
            print("Plan only: two native score jobs, A default and B follow_lyrics; zero full-song jobs.")
            print("No GPU work authorized. Use --confirm-plans to execute.")
            return 0
        # Shares the draft lock; do not launch other Studio jobs concurrently.
        drafts = repo / "results/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        lock = drafts / ".active"
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        try:
            client = Client(configured_endpoint(args.url), timeout=90).connect()
            root = repo / "results/generation-control" / _sha(_canonical(brief))
            run(brief, root, client)
            print("Report:", root / "report.json")
            print("No full song generated. No naturalness verdict.")
        finally:
            lock.unlink()
        return 0
    except (ValueError, OSError, KeyError, TypeError, MCPError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
