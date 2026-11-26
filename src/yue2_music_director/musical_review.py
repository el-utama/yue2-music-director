"""Offline generation-first review. Descriptors are not artistic grades or render authorization."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import math

from .music import parse_score, ScoreError, NativeUnsupported, native_section
from .prosody import parse_lyrics

SCHEMA = "native-musical-review-v1"


def _sections(lyrics):
    counts = Counter()
    result = []
    for group in parse_lyrics(lyrics):
        name = native_section(group["name"])
        counts[name] += 1
        # A complete parenthetical direction is not automatically sung text.
        lines = [line for line in group["lines"]
                 if not (line.startswith("(") and line.endswith(")"))]
        result.append((f"{name}#{counts[name]}", bool(lines)))
    return result


def _notes(score, voice):
    """Absolute note spans, retaining tied attacks only once."""
    result = []
    offsets=[Fraction(0)]
    for length in score.bar_lengths:
        offsets.append(offsets[-1]+length)
    for e in sorted((e for e in score.events if e.voice == voice and e.kind == "note"),
                    key=lambda e: (e.bar, e.offset)):
        start = (offsets[e.bar] if score.bar_lengths else e.bar * score.bar_units) + e.offset
        result.append((start, start + e.duration, e.pitch, e.tied))
    merged = []
    pending = False
    for start, end, pitch, tied in result:
        if pending:
            old_start, old_end, old_pitch = merged[-1]
            if old_end != start or old_pitch != pitch:
                raise ScoreError("Noncontiguous tie in review")
            merged[-1] = (old_start, end, pitch)
        else:
            merged.append((start, end, pitch))
        pending = tied
    return merged


def _voice_metrics(notes, start, end, seconds_per_unit):
    clipped = [(max(a,start), min(b,end), p) for a,b,p in notes if a < end and b > start]
    attacks = [(a,p) for a,b,p in notes if start <= a < end]
    pitches = [p for _,_,p in clipped]
    leaps = [abs(b[1]-a[1]) for a,b in zip(attacks, attacks[1:])]
    sounding = sum((b-a for a,b,_ in clipped), Fraction(0))
    cursor = start
    gaps = []
    for a,b,_ in clipped:
        if a > cursor:
            gaps.append(a-cursor)
        cursor = max(cursor,b)
    if end > cursor:
        gaps.append(end-cursor)
    seconds = float((end-start)*seconds_per_unit)
    return {
        "attacks": len(attacks),
        "attacks_per_second": len(attacks)/seconds,
        "sounding_fraction": float(sounding/(end-start)),
        "pitch_min": min(pitches) if pitches else None,
        "pitch_max": max(pitches) if pitches else None,
        "range_semitones": max(pitches)-min(pitches) if pitches else None,
        "adjacent_attack_leap_histogram": dict(sorted(Counter(map(str, leaps)).items())),
        "repeated_attack_fraction": leaps.count(0)/len(leaps) if leaps else None,
        "rest_spans": len(gaps),
        "longest_rest_seconds": float(max(gaps,default=0)*seconds_per_unit),
        "leading_rest_seconds": float((clipped[0][0]-start if clipped else end-start)*seconds_per_unit),
        "trailing_rest_seconds": float((end-clipped[-1][1] if clipped else end-start)*seconds_per_unit),
    }


def _bar_signature(score, bar):
    # Relative note/rest intervals, not spelling or the compression of Z rests.
    events = score.bar_events["Vocal"][bar]
    if not events or all(e.kind != "note" for e in events):
        return ()
    return tuple((e.offset,e.duration,e.pitch,e.tied) for e in events if e.kind == "note")


def validate_constraints(constraints=None, max_seconds=None):
    constraints = {} if constraints is None else constraints
    if not isinstance(constraints,dict) or not set(constraints) <= {
            "key","tempo_bpm","section_order","sung_sections"}:
        raise ValueError("Unknown review constraint")
    for name,c in constraints.items():
        if not isinstance(c,dict) or set(c)!={"mode","value"} or c["mode"] not in ("must","prefer","free"):
            raise ValueError("Invalid constraint: "+name)
        v=c["value"]
        if c["mode"]=="free":
            if v is not None:
                raise ValueError("Free constraint must have null value")
        elif name=="tempo_bpm":
            if type(v) is not int or v<=0:
                raise ValueError("Invalid tempo constraint")
        elif name=="key":
            from .music import key_signature
            if not isinstance(v,str):
                raise ValueError("Invalid key constraint")
            key_signature(v,native=True)
        elif not isinstance(v,list) or not all(isinstance(x,str) and x for x in v):
            raise ValueError("Expected section occurrence list")
    if max_seconds is not None and (type(max_seconds) not in (int,float)
            or not math.isfinite(max_seconds) or max_seconds<=0):
        raise ValueError("Invalid absolute score-clock limit")
    return constraints


def review_score(abc, lyrics, *, constraints=None, max_seconds=None):
    """Versioned local policy, independent of historical inspect_plan.

    constraints is a mapping key/tempo_bpm/section_order/sung_sections to
    {"mode": "must"|"prefer"|"free", "value": ...}. Section values are
    normalized occurrence IDs (e.g. chorus#2), not claims about sung words.
    max_seconds is a hard score-clock limit, not an audio length prediction.
    """
    constraints = validate_constraints(constraints, max_seconds)
    expected = _sections(lyrics)
    hard, soft, unknown = [], [], []
    report = {
        "schema": SCHEMA, "score_sha256": hashlib.sha256(abc.encode()).hexdigest(),
        "lyrics_sha256": hashlib.sha256(lyrics.encode()).hexdigest(),
        "constraints": constraints, "max_seconds": max_seconds,
        "hard_violations": hard, "soft_flags": soft, "unknowns": unknown,
        "native_midi_verified": False, "requires_native_midi": True,
        "render_authorized": False, "naturalness_verified": False,
        "phonetic_alignment_verified": False, "metrics": None,
    }
    try:
        score = parse_score(abc, native=True)
        if score.sections["Vocal"] != score.sections["Ins"]:
            raise ScoreError("Voice section grid mismatch")
        notes = {v:_notes(score,v) for v in ("Vocal","Ins")}
    except NativeUnsupported as exc:
        unknown.append({"code":"unsupported_local_notation","detail":str(exc)})
        if max_seconds is not None or any(c["mode"]=="must" for c in constraints.values()):
            hard.append({"code":"mandatory_constraint_unassessed"})
        report["status"]="unassessable"
        return report
    except (ScoreError, ValueError, KeyError, ZeroDivisionError, OverflowError) as exc:
        hard.append({"code":"local_score_invalid","detail":str(exc)})
        report["status"]="blocked"
        return report
    bpm=int(score.headers["Q"].split("=")[1])
    seconds_per_unit=Fraction(score.headers["L"])*240/bpm
    bar_units=score.bar_units
    count=score.counts["Vocal"]
    offsets=[Fraction(0)]
    for length in score.bar_lengths or (bar_units,)*count:
        offsets.append(offsets[-1]+length)
    total=offsets[-1]
    section_ids=list(dict.fromkeys(score.sections["Vocal"]))
    rows=[]
    ranges={}
    for sec in section_ids:
        bars=[i for i,label in enumerate(score.sections["Vocal"]) if label==sec]
        start,end=offsets[bars[0]],offsets[bars[-1]+1]
        ranges[sec]=bars
        rows.append({"section":sec,"bars":len(bars),"start_seconds":float(start*seconds_per_unit),
                     "duration_seconds":float((end-start)*seconds_per_unit),
                     "vocal":_voice_metrics(notes["Vocal"],start,end,seconds_per_unit),
                     "ins":_voice_metrics(notes["Ins"],start,end,seconds_per_unit),
                     "chord_symbols":list(dict.fromkeys(c for b in bars
                                  for c in score.bar_chords.get(("Vocal",b),[])))})
    sung=[r["section"] for r in rows if r["vocal"]["sounding_fraction"]>0]
    wanted=[s for s,has_words in expected if has_words]
    missing=[s for s in wanted if s not in sung]
    extra=[s for s in sung if s not in wanted]
    if missing or extra or sung!=wanted:
        soft.append({"code":"notated_sung_sequence_differs","missing":missing,"extra":extra,
                     "expected":wanted,"actual":sung})
    expected_order=[s for s,_ in expected]
    if [s for s in section_ids if s in expected_order]!=expected_order:
        soft.append({"code":"section_order_differs","expected":expected_order,"actual":section_ids})
    chorus=[s for s in section_ids if s.startswith("chorus#")]
    comparisons=[]
    for first,second in zip(chorus,chorus[1:]):
        a,b=ranges[first],ranges[second]
        same=sum(_bar_signature(score,x)==_bar_signature(score,y) for x,y in zip(a,b))
        shared=min(len(a),len(b))
        comparisons.append({"first":first,"second":second,"first_bars":len(a),
                            "second_bars":len(b),"shared_bars":shared,
                            "identical_vocal_bars":same,
                            "shared_vocal_bar_identity_fraction":same/shared})
        if len(a)==len(b)==same:
            soft.append({"code":"identical_repeated_chorus","sections":[first,second]})
    actual={"key":score.headers["K"],"tempo_bpm":bpm,"section_order":section_ids,
            "sung_sections":sung}
    for name,c in constraints.items():
        mismatch=c["value"]!=actual[name] or (name=="key" and any(key!=c["value"] for _,key in score.key_changes))
        if c["mode"]!="free" and mismatch:
            (hard if c["mode"]=="must" else soft).append(
                {"code":"constraint_mismatch","field":name,"expected":c["value"],"actual":actual[name]})
    duration=float(total*seconds_per_unit)
    if max_seconds is not None and total*seconds_per_unit>Fraction(str(max_seconds)):
        hard.append({"code":"score_clock_exceeds_cap","actual_seconds":duration})
    report["metrics"]={**actual,"meter":score.headers["M"],"unit":score.headers["L"],
                       "bars":count,"score_seconds":duration,"sections":rows,
                       "vocal":_voice_metrics(notes["Vocal"],0,total,seconds_per_unit),
                       "ins":_voice_metrics(notes["Ins"],0,total,seconds_per_unit),
                       "chorus_comparisons":comparisons}
    if len(set(score.bar_lengths))>1 or score.key_changes:
        report["metrics"]["variable_grid"]={"bar_lengths_note_units":[str(x) for x in score.bar_lengths],
                  "key_changes":[{"seconds":float(at*seconds_per_unit),"key":key} for at,key in score.key_changes]}
    unknown.append({"code":"acoustic_performance_and_lyric_delivery_unverified"})
    report["status"]="blocked" if hard else "artistic_review_required" if soft else "local_review_ready"
    return report
