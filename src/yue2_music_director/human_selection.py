"""Offline paired preference review, not a final fidelity certificate."""
from collections import Counter

CHOICES = {"baseline", "candidate", "tie", "uncertain", "not_reviewed"}


def _direction(a, b):
    return "baseline" if a < b else "candidate" if b < a else "tie"


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError("Expected nonnegative integer ASR edit count")
    return value


def compare(asr, human):
    if not isinstance(asr, dict) or asr.get("schema") != "native-asr-review-v1":
        raise ValueError("Expected native-asr-review-v1")
    if not isinstance(human, dict):
        raise ValueError("Expected human preference object")
    labels = [human.get(k) for k in ("baseline", "candidate")]
    if any(not isinstance(x, str) or not x.strip() for x in labels) or labels[0] == labels[1]:
        raise ValueError("Distinct baseline and candidate labels required")
    arms = asr.get("arms")
    if not isinstance(arms, dict) or set(arms) != {"A", "B"}:
        raise ValueError("ASR A/B arms required")
    totals = {}
    for arm in ("A", "B"):
        m = arms[arm]
        if not isinstance(m, dict):
            raise ValueError("Invalid ASR metrics")
        totals[arm] = sum(_count(m.get(k)) for k in ("insertions", "deletions", "substitutions"))
    words = _count(arms["A"].get("reference_words"))
    if not words or words != _count(arms["B"].get("reference_words")):
        raise ValueError("ASR reference word counts differ or are empty")
    rows = {}
    for row in asr.get("reference_lines", []):
        key = (row["section"], row["line_index"])
        if key in rows:
            raise ValueError("Duplicate ASR line identifier")
        rows[key] = {a:_count(row.get(a+"_count")) for a in ("A","B")}
    preferences = human.get("preferences")
    if not isinstance(preferences, list) or not preferences:
        raise ValueError("Human preferences required")
    result, seen, used_lines = [], set(), set()
    for item in preferences:
        if not isinstance(item, dict):
            raise ValueError("Invalid preference")
        name, choice = item.get("criterion"), item.get("preference")
        if not isinstance(name,str) or not name.strip() or name in seen or not isinstance(choice,str) or choice not in CHOICES:
            raise ValueError("Invalid or duplicate preference criterion")
        seen.add(name)
        counts = None
        if name == "overall_lyrics":
            counts = totals
        if "line" in item:
            line = item["line"]
            if (name in ("overall_lyrics","overall_music") or not isinstance(line,dict)
                    or not isinstance(line.get("section"),str)
                    or type(line.get("line_index")) is not int):
                raise ValueError("Invalid line preference")
            key = (line["section"], line["line_index"])
            if key not in rows or key in used_lines:
                raise ValueError("Unknown or duplicate ASR line")
            used_lines.add(key)
            counts = rows[key]
        direction = _direction(counts["A"],counts["B"]) if counts is not None else None
        relation = ("not_comparable" if direction is None or choice in ("uncertain","not_reviewed")
                    else "agreement" if direction == choice else "disagreement")
        result.append({**item,"asr_edit_counts":counts,"asr_direction":direction,
                       "comparison":relation})
    if not {"overall_lyrics","overall_music"} <= seen:
        raise ValueError("Overall lyrics and music preferences are required")
    by_name = {r["criterion"]:r["preference"] for r in result}
    overall = by_name["overall_music"]
    selected = overall if overall in ("baseline","candidate") and by_name["overall_lyrics"] == overall else None
    return {"schema":"human-selection-v1","baseline":labels[0],"candidate":labels[1],
            "human_preference_counts":{k:sum(r["preference"]==k for r in result) for k in sorted(CHOICES)},
            "asr_comparison_counts":dict(Counter(r["comparison"] for r in result)),
            "asr_edit_totals":totals,"reference_words":words,"preferences":result,
            "provisional_preferred":human[selected] if selected else None,
            "selection_status":"human_preferred_provisional" if selected else "human_decision_required",
            "absolute_fidelity_status":"not_established_by_relative_review",
            "automatic_acceptance":False,"automatic_regeneration":False,
            "audio_jobs_created":0,"recognition_calls":0,"score_edits":0,
            "warnings":["ASR A maps to baseline and ASR B to candidate; operator must verify identity.",
                        "A lower ASR edit count is not verified sung word accuracy.",
                        "Criteria overlap and are not independent votes; selection requires agreement of explicit overall lyric and music preferences.",
                        "Relative preference cannot pass an absolute fidelity gate or clear existing confirmed issues.",
                        "No audio analyzed; this report records supplied human observations."]}
