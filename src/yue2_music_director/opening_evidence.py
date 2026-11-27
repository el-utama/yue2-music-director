"""Versioned score-clock opening evidence, never acoustic verification."""

# A short pickup or deliberate breath is compatible with direct vocal.
MAX_VOCAL_LEAD_SECONDS = 2.0


def assess(rows, notes, seconds_per_unit):
    """Describe the notation and distinguish uncertainty from absent vocals."""
    first = rows[0] if rows else None
    onset = float(notes["Vocal"][0][0]*seconds_per_unit) if notes["Vocal"] else None
    ins_onset = float(notes["Ins"][0][0]*seconds_per_unit) if notes["Ins"] else None
    intro = first if first and first["section"] == "intro#1" else None
    intro_duration = intro["duration_seconds"] if intro else 0.0
    accompaniment = ("notated_ins_activity" if intro and intro["ins"]["sounding_fraction"] > 0
                     else "unverified" if intro else "not_applicable")
    evidence = {
        "schema": "notated-opening-evidence-v1",
        "first_vocal_onset_seconds": onset,
        "first_ins_onset_seconds": ins_onset,
        "notated_intro_duration_seconds": intro_duration,
        "intro_accompaniment": accompaniment,
        "max_vocal_lead_seconds": MAX_VOCAL_LEAD_SECONDS,
        "acoustic_verified": False,
        "classification": "unassessed",
        "reason": "No assessable opening",
    }
    if onset is None or first is None:
        evidence["reason"] = "No notated vocal attack"
    elif intro:
        if intro["vocal"]["sounding_fraction"] > 0:
            evidence["reason"] = "Vocal activity in instrumental intro"
        elif onset - intro_duration > MAX_VOCAL_LEAD_SECONDS:
            evidence["reason"] = "Vocal entry delayed after intro"
        elif accompaniment == "unverified":
            evidence["reason"] = "Vocal-free intro; backing activity cannot be established from Ins notation"
        else:
            evidence.update(classification="instrumental_intro", reason="Vocal-free intro with notated Ins activity")
    elif first["vocal"]["sounding_fraction"] > 0 and onset <= MAX_VOCAL_LEAD_SECONDS:
        evidence.update(classification="direct_vocal", reason="Early notated vocal attack")
    else:
        evidence["reason"] = "Vocal entry delayed or opening section is vocal-free"
    return evidence
