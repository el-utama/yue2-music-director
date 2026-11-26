"""One controlled, listener-informed arrangement revision; no baseline replay."""
from __future__ import annotations

from . import listening_director as ld, native_draft as nd

# An assistant-authored artistic decision for the observed demo, not a general
# LLM policy or a claim that the native model can guarantee these changes.
STYLE = (
    "Intimate contemporary folk-soul ballad; close, expressive lead vocal with conversational phrasing, "
    "natural breaths, gentle melodic expression and space between phrases. Acoustic guitar, soft upright "
    "piano, warm bass and organic restrained drums. First verse: exposed fingerpicked guitar, sparse piano "
    "answers only between vocal lines. First chorus: warmer bass movement and a soft brushed pulse, "
    "piano answers the vocal hook. Second verse: vary the guitar picking pattern and let piano take a "
    "different answering motif; reduce percussion briefly rather than looping the same backing. "
    "Bridge: withdraw bass and drums, return to guitar and voice, with a short instrumental breath. "
    "Final chorus: restore the pulse and develop the earlier instrumental motif with subtle harmony, "
    "a warmer rhythmic lift but no belting or forced climax. Unhurried instrumental resolution. "
    "Keep the lead vocal intimate and the instrumentation organic; change roles and texture across sections, "
    "not just volume or number of instruments."
)
FEEDBACK = {"source": "operator_subjective_listening",
            "vocal": "good", "arrangement": "monotonous", "ending": "not_cut_off"}


def revised_brief(brief):
    if brief["style"] == STYLE:
        raise ValueError("Revision must change the conditioning")
    return {**brief, "style": STYLE}


def baseline(repo, brief, intent):
    root = repo / "results/drafts" / ("artist-" + nd.digest(nd._canonical(brief)))
    manifest = {"schema": "artist-run-v1", "brief": brief, "intent": intent,
                "route": "direct_native", "explicit_score_sha256": None}
    if nd.read(root / "manifest.json") != manifest:
        raise ValueError("Baseline manifest differs")
    draft = root / "draft"
    report = nd.read(draft / "report.json")
    row = ld.verify_take(draft, brief, report)
    journal = nd.read(draft / "journal_song.json")
    config = journal.get("reference_configuration")
    if not isinstance(config, dict) or not config or report.get("artistic_intent") != intent:
        raise ValueError("Baseline intent or reference configuration missing")
    if nd.read(draft / "artist-policy.json") != {"intent": intent, "planner_configuration": None}:
        raise ValueError("Baseline artistic policy differs")
    out = root / "neutral-listening"
    packet = nd.read(out / "review-packet.json")
    contract = nd.read(out / "contract.json")
    expected = {"schema": "neutral-listening-v1", "audio_sha256": row["audio_sha256"],
                "ranges": [list(x) for x in ld.ac.excerpt_ranges(row["acoustic"]["duration_seconds"])],
                "prompt": ld.PROMPT, "provider": "Studio-v5.0-MOSS-Q4_K_M/CPU",
                "automatic_acceptance": False}
    if contract != expected or (out / "prompt.txt").read_text(encoding="utf-8") != ld.PROMPT:
        raise ValueError("Baseline listening contract differs")
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
            raise ValueError("Baseline listening receipt differs")
        response = raw.read_text(encoding="utf-8", errors="replace")
        status, checks = ld.parse_observations(response)
        evidence.append({"arm": "baseline", "start_seconds": start, "duration_seconds": duration,
                         "format_status": status, "checks": checks, "raw_response": response})
    if packet != ld.review_packet(brief, intent, row, contract, evidence):
        raise ValueError("Baseline review packet differs")
    return root, row, packet, config, report


def launch_revision(repo, url, *, confirm=False):
    brief, intent = ld.inputs(repo, demo=True)
    candidate = revised_brief(brief)
    # Offline plan remains useful even before the live baseline exists.
    print("One arrangement revision:", brief["title"], flush=True)
    print("Retain original recording, lyrics, seed, vocal direction and duration cap.", flush=True)
    print("Only the style request changes; actual vocal and melody may differ.", flush=True)
    print("Revised style:", candidate["style"], flush=True)
    if not confirm:
        print("Plan only. No Studio calls or inference.", flush=True)
        return 0
    drafts = repo / "results/drafts"
    with ld.lock(drafts / ".active"), ld.lock(repo / "results/.critic-active"):
        root, row, packet, config, original = baseline(repo, brief, intent)
        folder = root / "arrangement-revision-1"
        decision = {"schema": "arrangement-revision-v1", "feedback": FEEDBACK,
                    "decision_author": "assistant", "baseline_audio_sha256": row["audio_sha256"],
                    "baseline_packet_sha256": nd._sha(root / "neutral-listening/review-packet.json"),
                    "baseline_request": nd.request_for(brief), "revision_request": nd.request_for(candidate),
                    "reference_configuration": config, "budget": {"song_jobs": 1, "recognition_calls": 1,
                                                                 "cpu_excerpts": 2},
                    "automatic_winner": False}
        path = folder / "decision.json"
        if folder.exists():
            if nd.read(path) != decision:
                raise ValueError("Retained revision decision differs; no replay")
        else:
            folder.mkdir(parents=True, exist_ok=False)
            nd.atomic_write(path, decision)
        report = nd.execute(candidate, folder / "draft", url, artist=intent,
                            expected_configuration=config)
        revised = ld.verify_take(folder / "draft", candidate, report)
        if (report["song_id"] == original["song_id"] or revised["audio_sha256"] == row["audio_sha256"]
                or nd.read(folder / "draft/journal_song.json").get("reference_configuration") != config):
            raise ValueError("Revision identity or reference configuration differs")
        if nd._sha(ld.Path(row["audio"])) != row["audio_sha256"]:
            raise ValueError("Original audio changed")
        revised_packet = ld.listen(folder, candidate, intent, revised, url)
        comparison = {"schema": "arrangement-comparison-v1", "decision": decision,
                      "baseline": packet, "revision": revised_packet,
                      "listening_verdict": "pending", "automatic_winner": False,
                      "automatic_acceptance": False,
                      "warnings": ["Only style conditioning differs; native melody and vocal performance may change.",
                                   "Model descriptions are advisory; compare actual vocals, arrangement and ending.",
                                   "One pair is not proof of general musical improvement."]}
        nd.atomic_write(folder / "comparison.json", comparison)
        print("Original:", row["audio"], flush=True)
        print("Revision:", revised["audio"], flush=True)
        print("Comparison:", folder / "comparison.json", flush=True)
        print("No automatic winner. Listen to both takes.", flush=True)
    return 0
