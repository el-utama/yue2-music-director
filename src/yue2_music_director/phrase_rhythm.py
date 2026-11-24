"""Read-only phrase rhythm diagnostics; no score edits or audio inference."""
from __future__ import annotations
from fractions import Fraction
import math
from .music import parse_score, section_sequence, ScoreError
from .prosody import parse_lyrics, alignment
from .lyric_fidelity import _tokens, compare_lyrics


def analyze(source: str, lyrics: str, timings=None) -> dict:
    score = parse_score(source)
    groups = parse_lyrics(lyrics)
    warnings = alignment(score, groups)
    if section_sequence(score) != [g["name"] for g in groups]:
        raise ScoreError("Cannot allocate phrases with mismatched sections")
    unit = Fraction(score.headers["L"]) * 4
    sections = {}
    for i, sec in enumerate(score.sections["Vocal"]):
        sections.setdefault(sec, []).append(i)
    phrases = []
    for g in groups:
        sec = f"{g['name']}#{g['occurrence']}"
        bars = sections.get(sec, [])
        n = len(g["lines"])
        for j, line in enumerate(g["lines"]):
            selected = bars[j*len(bars)//n:(j+1)*len(bars)//n]
            notes = [e for b in selected for e in score.bar_events["Vocal"][b]
                     if e.kind == "note"]
            span = len(selected) * score.bar_units * unit
            sounding = sum((e.duration * unit for e in notes), Fraction(0))
            words = len(_tokens(line))
            flags = []
            if not selected:
                flags.append("no_allocated_bars")
            if not sounding:
                flags.append("no_notated_vocal_sound")
            if words and len(notes) < words:
                flags.append("fewer_note_events_than_words")
            phrases.append({"section": sec, "line_index": j+1,
                            "lyric": line, "reference_words": words,
                            "bar_start": selected[0]+1 if selected else None,
                            "bar_end": selected[-1]+1 if selected else None,
                            "allocated_quarter_notes": float(span),
                            "sounding_quarter_notes": float(sounding),
                            "non_sounding_quarter_notes": float(span-sounding),
                            "note_events": len(notes),
                            "words_per_sounding_quarter": float(words/sounding) if sounding else None,
                            "review_flags": flags})
    pairs = []
    if timings is not None:
        if not isinstance(timings, list) or not timings:
            raise ValueError("timings must be a nonempty JSON array")
        index = {(p["section"], p["line_index"]): (i, p)
                 for i,p in enumerate(phrases)}
        seen = set()
        last_end = {"A": 0.0, "B": 0.0}
        ordered = []
        for item in timings:
            if not isinstance(item, dict) or type(item.get("line_index")) is not int or not isinstance(item.get("section"), str):
                raise ValueError("Each timing row requires section and integer line_index")
            key = (item["section"], item["line_index"])
            if key not in index or key in seen:
                raise ValueError("Unknown or duplicate phrase timing key")
            seen.add(key)
            ordered.append((index[key][0], item, index[key][1]))
        for _, item, phrase in sorted(ordered, key=lambda x: x[0]):
            result = {"section": phrase["section"], "line_index": phrase["line_index"]}
            for arm in ("A", "B"):
                t = item.get(arm)
                if not isinstance(t, dict):
                    raise ValueError("Both A and B timing objects are required")
                start, end = t.get("start"), t.get("end")
                if any(type(v) not in (int, float) or not math.isfinite(v)
                       for v in (start,end)):
                    raise ValueError("Timing boundaries must be finite numbers in seconds")
                if start < last_end[arm] or end <= start:
                    raise ValueError("Intervals must be nonnegative, nonoverlapping and increasing in lyric order")
                last_end[arm] = end
                seconds = end-start
                arm_result = {"start": start, "end": end, "duration_seconds": seconds,
                              "reference_words_per_second": phrase["reference_words"]/seconds}
                if "transcript" in t:
                    if not isinstance(t["transcript"], str):
                        raise ValueError("Transcript must be text")
                    observed = len(_tokens(t["transcript"]))
                    arm_result["observed_words"] = observed
                    arm_result["observed_words_per_second"] = observed/seconds
                    if phrase["reference_words"]:
                        if observed:
                            arm_result["lyric_fidelity"] = compare_lyrics(
                                "[Verse]\n"+phrase["lyric"],t["transcript"])
                        else:
                            arm_result["lyric_fidelity"] = {
                                "reference_words": phrase["reference_words"],
                                "transcript_words": 0, "insertions": 0,
                                "deletions": phrase["reference_words"],
                                "substitutions": 0, "word_error_rate": 1.0}
                result[arm] = arm_result
            result["duration_ratio_B_over_A"] = (
                result["B"]["duration_seconds"]/result["A"]["duration_seconds"])
            pairs.append(result)
    return {"schema": "phrase-rhythm-v1", "phrases": phrases,
            "phrase_count": len(phrases),
            "paired_timing_count": len(pairs), "paired_timings": pairs,
            "audio_jobs_created": 0,
            "warnings": warnings + [
                "Equal bar partition is approximate, not actual lyric alignment.",
                "Quarter-note units describe score duration, not audio seconds.",
                "Word density is a review cue, not syllable stress or a rush threshold.",
                "Audio timings and transcripts, if supplied, are human annotations; no audio is analyzed.",
                "Compare identical intended phrases, including missing or extra words; rates include pauses inside annotated intervals."]}
