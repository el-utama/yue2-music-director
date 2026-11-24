"""Velocity-only MIDI export humanizer, not YuE2 audio conditioning."""
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from bisect import bisect_right
from .midi_events import parse_midi_data, compare_midi_data, MIDIEventError

ROLES = {"ins", "instrument", "chords"}


def humanize(data: bytes, strength: int = 12):
    if type(strength) is not int or not 1 <= strength <= 24:
        raise ValueError("strength must be an integer from 1 to 24")
    source = parse_midi_data(data)
    names = source["track_names"]
    tracks = {i for i,n in names.items()
              if len(n)==1 and n[0].strip().casefold() in ROLES}
    if not tracks:
        raise MIDIEventError("No unambiguous named Ins/Instrument/Chords track")
    signatures = sorted(set(source["signatures"]))
    if not signatures or signatures[0][0] != 0:
        raise MIDIEventError("Explicit time signature at tick zero required")
    if len({t for t,_,_ in signatures}) != len(signatures):
        raise MIDIEventError("Conflicting time signatures")
    if any(not 1<=n<=32 or not 0<=d<=5 for _,n,d in signatures):
        raise MIDIEventError("Unsupported meter")
    starts = [t for t,_,_ in signatures]
    by_track = defaultdict(list)
    for note in source["notes"]:
        by_track[note.track].append(note)
    modified = bytearray(data)
    skipped = []
    allowed_offsets = set()
    for track in sorted(tracks):
        notes = by_track[track]
        if not notes or len({n.velocity for n in notes}) != 1 or any(n.channel==9 for n in notes):
            skipped.append(track)
            continue
        for note in notes:
            origin,numerator,power = signatures[bisect_right(starts,note.start)-1]
            beat = Fraction(source["division"]*4, 2**power)
            bar,phase = divmod(Fraction(note.start-origin),beat*numerator)
            pulse = phase/beat
            # Accentuate the downbeat and secondary accents; chord tones at the
            # same onset share the same adjustment. Four-bar contour is a
            # generic musical heuristic, not an inferred phrase boundary.
            accent = 0 if pulse==0 else 0.25 if pulse.denominator==1 and (
                (numerator==4 and pulse==2) or (numerator in (6,9,12) and pulse%3==0)
            ) else 0.55 if pulse.denominator==1 else 0.85
            contour = (0.15,0.25,0.0,0.35)[int(bar)%4]
            new = max(1,min(127,note.velocity-round(strength*(accent+contour))))
            off = source["note_on_offsets"][note.order]
            if data[off] != note.velocity:
                raise MIDIEventError("Note-on byte mismatch")
            modified[off]=new
            allowed_offsets.add(off)
    candidate = bytes(modified)
    report = compare_midi_data(data,candidate)
    if report["pitch_changes"] or report["timing_changes"] or not set(report["changed_tracks"])<=tracks:
        raise MIDIEventError("Unexpected non-velocity or protected-track change")
    if len(candidate)!=len(data) or any(a!=b and i not in allowed_offsets
                                       for i,(a,b) in enumerate(zip(data,candidate))):
        raise MIDIEventError("Unexpected MIDI byte change")
    return candidate, {**report,"schema":"instrument-velocity-v1",
                       "strength":strength,"skipped_tracks":skipped,
                       "target_tracks":sorted(tracks),"audio_jobs_created":0,
                       "scope":"DAW MIDI export only",
                       "warnings":["No YuE2 ABC or audio changes; render with a velocity-sensitive instrument.",
                                   "Only constant-velocity named accompaniment tracks are edited.",
                                   "Meter accents and four-bar contour are heuristics, not actual performance analysis."]}


def write(source: Path, out: Path, strength: int = 12):
    candidate, report = humanize(source.read_bytes(),strength)
    if not report["velocity_changes"]:
        raise MIDIEventError("No eligible velocity changes; output not created")
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("xb") as f:
        f.write(candidate)
    return report
