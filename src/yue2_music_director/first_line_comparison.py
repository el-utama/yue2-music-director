"""One controlled rendition with a two-phrase replacement for Verse 1's first line."""
import argparse
import json
from pathlib import Path
import re
import sys

from . import artist_run, listening_director as ld, native_draft as nd, retained_source
from .mcp import MCPError, configured_endpoint
from .prosody import SECTION, parse_lyrics


def revised_lyrics(lyrics, phrases):
    if (len(phrases) != 2 or any(not phrase.strip() or len(phrase) > 200
            or phrase != phrase.strip() or len(phrase.splitlines()) != 1
            or "[" in phrase or "]" in phrase for phrase in phrases)):
        raise ValueError("Supply two plain, nonempty lyric phrases")
    first = next((section for section in parse_lyrics(lyrics) if section["lines"]), None)
    if first is None or first["name"] != "verse" or first["occurrence"] != 1:
        raise ValueError("The first sung section must be Verse 1")
    lines = lyrics.splitlines(keepends=True)
    index = next(i for i, line in enumerate(lines) if line.strip() and not SECTION.fullmatch(line.strip()))
    original = lines[index].rstrip("\r\n")
    if original.strip() != first["lines"][0]:
        raise ValueError("Could not locate the exact first line of Verse 1")
    newline = lines[index][len(original):]
    lines[index] = (newline or "\n").join(phrases) + newline
    return "".join(lines)


def prepare(repo, job, phrases):
    source = retained_source.load(repo, job)
    intent = source["intent"]
    if source["report"].get("generation_path") != "reviewed_native":
        raise ValueError("Comparison requires a completed reviewed-native take")
    parent = source["root"] / "production"
    draft = parent / "draft"
    original = nd.read(draft / "request.json")
    abc = original["abc"]
    brief = {**source["brief"], "lyrics": revised_lyrics(source["brief"]["lyrics"], phrases)}
    if {**nd.request_for(brief), "abc": abc} != {**original, "lyrics": brief["lyrics"]}:
        raise ValueError("Current native request differs outside lyrics")
    configuration = nd.read(parent / "journal_plan.json")["configuration"]
    if (not configuration or nd.read(draft / "journal_song.json")["reference_configuration"] != configuration
            or nd.read(draft / "artist-policy.json") != {"intent": intent, "planner_configuration": configuration}):
        raise ValueError("Retained planner and synthesis configurations differ")
    decision = artist_run.evaluate_plan(abc, brief, intent)
    if decision["decision"] != "retain":
        raise ValueError("First-line comparison did not pass score review")
    contract = {"schema": "first-line-comparison-v1", "source": source["evidence"],
                "audio_sha256": source["row"]["audio_sha256"], "brief": brief,
                "intent": intent, "score_review": decision, "configuration": configuration}
    return source, abc, contract


def launch(repo, job, phrases, url, *, confirm=False, approve_audio_sha=None):
    if approve_audio_sha is not None and (not confirm or not re.fullmatch(r"[0-9a-f]{64}", approve_audio_sha)):
        raise ValueError("Audio approval requires confirmation and a full lowercase SHA-256")
    source, abc, contract = prepare(repo, job, phrases)
    if not confirm:
        print(json.dumps({"status": "preview_ready", "replacement": phrases,
                          "score_seconds": contract["score_review"]["score_review"]["metrics"]["score_seconds"],
                          "song_jobs": 0, "provider_calls": 0}, ensure_ascii=True, indent=2))
        return 0
    url = configured_endpoint(url)
    if source["identity"]["studio_url"] != url:
        raise ValueError("Studio endpoint differs from the retained take")
    root = source["root"] / "first-line-comparison"
    context = {"job": job, "root": root.relative_to(repo).as_posix(), "stage": "first_line_comparison"}
    with ld.lock(repo / "results/drafts/.active", context=context), ld.lock(repo / "results/.critic-active", context=context):
        if prepare(repo, job, phrases)[2] != contract:
            raise ValueError("Source changed after review")
        path = root / "comparison.json"
        if root.exists():
            if nd.read(path) != contract:
                raise ValueError("Retained comparison differs. Resume with the same phrases")
        else:
            if approve_audio_sha is not None:
                raise ValueError("Audio approval requires a completed comparison song")
            root.mkdir()
            nd.create_journal(path, contract)
        print("First-line comparison:", root, flush=True)
        print("Budget: one native song and one local lyric recognition.", flush=True)
        report = nd.execute(contract["brief"], root / "draft", url, abc=abc, artist=contract["intent"],
                            expected_configuration=contract["configuration"], approve_audio_sha=approve_audio_sha)
        if (report["song_id"] == source["report"]["song_id"]
                or nd._sha(source["audio"]) != contract["audio_sha256"]):
            raise ValueError("Source audio or song identity differs")
        seconds = report["acoustic"]["duration_seconds"]
        print(json.dumps({"status": "review_required", "audio": report["audio"], "duration_seconds": seconds,
                          "duration_pass": 0 < seconds <= contract["brief"]["duration_seconds"]}, indent=2))
        return 0 if 0 < seconds <= contract["brief"]["duration_seconds"] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--compare-first-line", metavar="JOB", required=True)
    parser.add_argument("phrases", nargs=2)
    parser.add_argument("--confirm-run", action="store_true")
    parser.add_argument("--approve-audio-sha")
    args = parser.parse_args()
    try:
        return launch(args.repo.resolve(), args.compare_first_line, args.phrases, args.url,
                      confirm=args.confirm_run, approve_audio_sha=args.approve_audio_sha)
    except (ValueError, OSError, KeyError, TypeError, MCPError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
