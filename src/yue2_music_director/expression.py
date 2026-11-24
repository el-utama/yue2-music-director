"""Offline v0.7 experimental expression planner; no audio or timing control."""
from __future__ import annotations

from collections import Counter
import hashlib
from fractions import Fraction
from .music import (parse_score, chord_tones, key_signature, note_pitch,
                    patch_score, conservative_rejection, ScoreError,
                    repeated_pitch_fraction)
from .prosody import parse_lyrics, alignment, phrase_diagnostics

ELIGIBLE = frozenset(("verse", "pre-chorus", "bridge"))


def _shape(events):
    return tuple((e.voice, e.bar, e.section, e.kind, e.offset, e.duration,
                  e.chord, e.tied) for e in events)


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan(source: str, lyrics: str, max_edits: int = 4,
         protected_bars=()) -> dict:
    """Rank bounded, explainable pitch proposals, not a prosody prediction.

    Only an isolated three-note plateau with contiguous notes within one bar
    is eligible. Longer repeated runs, bar edges, phrase edges, section
    extrema, ties, explicit accidentals and user-protected bars are guarded.
    No requirement to make an edit; repeat contour pairs are not reused.
    """
    if not isinstance(max_edits, int) or not 0 <= max_edits <= 100:
        raise ValueError("max_edits must be 0 to 100")
    score = parse_score(source)
    groups = parse_lyrics(lyrics)
    warnings = alignment(score, groups)
    if any(w.startswith("SECTION MISMATCH") for w in warnings):
        raise ScoreError("; ".join(warnings))
    protected = set(protected_bars)
    if any(not isinstance(b, int) or not 1 <= b <= score.counts["Vocal"]
           for b in protected):
        raise ValueError("protected bars must be valid one-based vocal bars")
    events = [e for e in score.events if e.voice == "Vocal" and e.kind == "note"]
    sections = {}
    for i, sec in enumerate(score.sections["Vocal"]):
        sections.setdefault(sec, []).append(i)
    by_section = {}
    for e in events:
        by_section.setdefault(e.section, []).append(e)
    extrema = {sec: (min(e.pitch for e in notes), max(e.pitch for e in notes))
               for sec, notes in by_section.items()}
    # Match the actual floor-partition used by phrase_diagnostics, not an
    # inverse formula that can disagree for uneven bar/line counts.
    phrases = {}
    for g in groups:
        sec = f"{g['name']}#{g['occurrence']}"
        bars = sections.get(sec, [])
        n = len(g["lines"])
        for j in range(n):
            segment = bars[j * len(bars) // n:(j + 1) * len(bars) // n]
            for bar in segment:
                phrases[bar] = (j + 1, segment[0], segment[-1])
    signature = key_signature(score.headers["K"])
    rejected = Counter()
    options = []
    for i in range(1, len(events) - 1):
        prev, e, nxt = events[i-1:i+2]
        if e.section.split("#")[0] not in ELIGIBLE or e.bar + 1 in protected:
            rejected["protected_section_or_bar"] += 1
            continue
        if not (prev.pitch == e.pitch == nxt.pitch):
            rejected["not_isolated_plateau"] += 1
            continue
        if not (prev.bar == e.bar == nxt.bar and
                prev.offset + prev.duration == e.offset and
                e.offset + e.duration == nxt.offset):
            rejected["bar_edge_or_rest"] += 1
            continue
        if (i >= 2 and events[i-2].section == e.section and
                events[i-2].pitch == e.pitch) or (
                i + 2 < len(events) and events[i+2].section == e.section and
                events[i+2].pitch == e.pitch):
            rejected["long_repetition_preserved"] += 1
            continue
        phrase = phrases.get(e.bar)
        if phrase is None or e.bar in phrase[1:]:
            rejected["approximate_phrase_anchor"] += 1
            continue
        if e.tied or prev.tied or e.accidental or e.pitch in extrema[e.section]:
            rejected["tie_accidental_or_section_extremum"] += 1
            continue
        # Do not touch an accidental-bearing measure: its carry semantics
        # may make a letter replacement sound differently from the plan.
        if any(x.accidental for x in score.bar_events["Vocal"][e.bar]):
            rejected["accidental_in_bar"] += 1
            continue
        tones = chord_tones(e.chord)
        if not tones:
            rejected["unknown_chord_at_onset"] += 1
            continue
        lo, hi = extrema[e.section]
        for letter in "ABCDEFG":
            letter = letter.lower() if e.letter.islower() else letter
            pitch = note_pitch(letter, e.octave, "", signature, {})
            shift = pitch - e.pitch
            if not shift or pitch % 12 not in tones or not lo < pitch < hi:
                continue
            if conservative_rejection(e.pitch, pitch, prev.pitch, nxt.pitch):
                continue
            contour = (pitch - prev.pitch, nxt.pitch - pitch)
            # Lower movement first; shorter events before sustained ones.
            rank = (abs(shift), e.duration, e.bar, e.offset, pitch)
            edit = {"line": e.line, "start": e.start, "end": e.end,
                    "old": e.raw, "new": e.raw.replace(e.letter + e.octave,
                                                       letter + e.octave, 1),
                    "bar": e.bar + 1, "section": e.section,
                    "lyric_line_index": phrase[0], "offset": str(e.offset),
                    "duration": str(e.duration), "chord_at_onset": e.chord,
                    "pitch_before": e.pitch, "pitch_after": pitch,
                    "intervals_before": [0, 0], "intervals_after": list(contour),
                    "reason": "isolated plateau; bounded chord-tone variation",
                    "lyric_alignment": "unverified"}
            options.append((rank, i, contour, edit))
    chosen, used_phrases, contours, selected = [], set(), set(), set()
    for _, i, contour, edit in sorted(options, key=lambda item: item[0]):
        if len(chosen) >= max_edits:
            break
        phrase = (edit["section"], edit["lyric_line_index"])
        if (phrase in used_phrases or contour in contours or i in selected or
                any(abs(edit["bar"] - x["bar"]) <= 1 for x in chosen)):
            rejected["diversity_or_spacing"] += 1
            continue
        chosen.append(edit)
        used_phrases.add(phrase)
        contours.add(contour)
        selected.add(i)
    candidate = patch_score(score, chosen)
    parsed = parse_score(candidate)
    if (score.headers != parsed.headers or score.counts != parsed.counts or
            score.sections != parsed.sections or score.bar_chords != parsed.bar_chords or
            _shape(score.events) != _shape(parsed.events)):
        raise ScoreError("expression changed score structure")
    expected = {(x["line"], x["start"], x["end"]): x for x in chosen}
    seen = 0
    for a, b in zip(score.events, parsed.events):
        edit = expected.get((a.line, a.start, a.end))
        if edit is None:
            if a.pitch != b.pitch or a.raw != b.raw:
                raise ScoreError("unplanned event change")
        else:
            if (a.voice != "Vocal" or a.pitch != edit["pitch_before"] or
                    b.pitch != edit["pitch_after"] or b.raw != edit["new"]):
                raise ScoreError("planned pitch did not round-trip")
            seen += 1
    if seen != len(chosen):
        raise ScoreError("not all planned edits applied")
    return {"abc": candidate, "report": {
        "schema": "expression-preview-v1", "status": "candidate" if chosen else "no_safe_edits",
        "source_sha256": _digest(source), "candidate_sha256": _digest(candidate),
        "max_edits": max_edits, "change_count": len(chosen),
        "protected_bars": sorted(protected), "changes": chosen,
        "eligible_options": len(options), "rejection_counts": dict(rejected),
        "original_repeat_fraction": repeated_pitch_fraction(score),
        "candidate_repeat_fraction": repeated_pitch_fraction(parsed),
        "phrase_diagnostics": phrase_diagnostics(score, groups),
        "audio_jobs_created": 0,
        "warnings": warnings + score.warnings + [
            "Heuristic plateau and phrase guards are not proof of musical intent.",
            "No verified syllable alignment; no rhythm, velocity or audio control.",
            "Candidate quality requires listening; zero edits is valid."]}}
