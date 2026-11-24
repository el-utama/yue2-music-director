"""Human-led fidelity gate; no audio inference or score modification."""
from .phrase_rhythm import analyze
from .prosody import estimate_syllables

STATES = {"issue_confirmed", "no_issue_heard", "uncertain"}


def _key(row):
    if (not isinstance(row, dict) or not isinstance(row.get("section"), str)
            or type(row.get("line_index")) is not int):
        raise ValueError("Phrase identifier requires section and integer line_index")
    return row["section"], row["line_index"]


def diagnose(source, lyrics, asr, observations):
    rhythm = analyze(source, lyrics)
    phrases = rhythm["phrases"]
    keys = [_key(p) for p in phrases]
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("Missing or ambiguous reference phrases")
    if not isinstance(asr, dict) or asr.get("schema") != "native-asr-review-v1":
        raise ValueError("Expected native-asr-review-v1")
    rows = asr.get("reference_lines")
    if not isinstance(rows, list) or [_key(r) for r in rows] != keys:
        raise ValueError("ASR reference phrase sequence differs from score analysis")
    if not isinstance(observations, dict):
        raise ValueError("Observations must be a JSON object")
    line_obs, transition_obs = {}, {}
    for field in ("lines", "transitions"):
        if not isinstance(observations.get(field), list):
            raise ValueError("Observations require lines and transitions arrays")
    for row in observations["lines"]:
        key = _key(row)
        state = row.get("status")
        if key not in keys or key in line_obs or state not in STATES:
            raise ValueError("Invalid or duplicate human phrase observation")
        line_obs[key] = state
    adjacent = set(zip(keys, keys[1:]))
    for row in observations["transitions"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid transition observation")
        pair = (_key(row.get("after")), _key(row.get("before")))
        state = row.get("status")
        if pair not in adjacent or pair in transition_obs or state not in STATES:
            raise ValueError("Invalid or duplicate human transition observation")
        transition_obs[pair] = state
    result = []
    for p, row in zip(phrases, rows):
        if row.get("reference_text") != p["lyric"] or row.get("reference_words") != p["reference_words"]:
            raise ValueError("ASR reference text differs from current lyrics")
        counts = {}
        for arm in ("A", "B"):
            edits = row.get(arm)
            count = row.get(arm+"_count")
            if not isinstance(edits, list) or type(count) is not int or count != len(edits):
                raise ValueError("Invalid ASR line counts")
            counts[arm] = count
        syllables = estimate_syllables(p["lyric"])
        result.append({**p, "human_status":line_obs.get(_key(p), "not_reviewed"),
                       "asr_edit_counts":counts, "rough_english_syllables":syllables,
                       "notes_per_estimated_syllable":p["note_events"]/syllables if syllables else None})
    transitions = [{"after":{"section":a[0],"line_index":a[1]},
                    "before":{"section":b[0],"line_index":b[1]},
                    "human_status":state}
                   for (a,b),state in transition_obs.items()]
    confirmed = sum(p["human_status"]=="issue_confirmed" for p in result)
    confirmed_transitions = sum(t["human_status"]=="issue_confirmed" for t in transitions)
    return {"schema":"human-fidelity-audit-v1",
            "gate":"blocked_confirmed_issue" if confirmed or confirmed_transitions else "not_assessed_for_acceptance",
            "confirmed_issue_lines":confirmed, "confirmed_issue_transitions":confirmed_transitions,
            "reviewed_line_observations":len(line_obs), "total_lines":len(phrases),
            "phrases":result, "transitions":transitions, "audio_jobs_created":0,
            "recognition_calls":0, "score_edits":0,
            "warnings":rhythm["warnings"] + [
                "Human observations are phrase-level, not a verified word error rate.",
                "ASR arms A/B are the input report labels, not necessarily original/candidate.",
                "ASR and score source identity beyond matching lyrics must be established by the operator.",
                "Rough English syllable estimates and equal bar partitions do not establish actual phonetic alignment.",
                "No causal attribution, automatic correction, or approval from this report."]}
