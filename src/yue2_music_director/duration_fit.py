"""Offline, advisory tempo-only candidate for an otherwise valid over-cap score."""
from fractions import Fraction
import re
from . import native_draft as nd, artist_run as ar
from .music import parse_score

MAX_TEMPO_RATIO = Fraction(11,10)
ENDING_RESERVE_SECONDS = 3


def preview(abc, brief, intent):
    original=ar.evaluate_plan(abc,brief,intent)["score_review"]
    result={"schema":"duration-fit-preview-v1","status":"not_eligible",
            "provider_calls":0,"studio_calls":0,"render_authorized":False,
            "original_score_sha256":nd.digest(abc.encode("utf-8"))}
    def reject(reason):
        return {**result,"reason":reason}
    hard=original["hard_violations"]
    if (original["status"]!="blocked" or len(hard)!=1 or
            hard[0]["code"]!="score_clock_exceeds_cap" or original["soft_flags"]):
        return reject("Requires duration-only rejection with no soft flags")
    tempo=int(original["metrics"]["tempo_bpm"])
    cap=brief["duration_seconds"]
    target=cap-ENDING_RESERVE_SECONDS
    if target<=0:
        return reject("No available duration reserve")
    if intent["constraints"].get("tempo_bpm",{}).get("mode") in ("must","prefer"):
        return reject("Explicit tempo constraint; do not change")
    # Do not contradict literal BPM in the original style or direction.
    if re.search(r"\b\d+(?:\.\d+)?\s*bpm\b|\bbpm\s*[:=]?\s*\d", 
                 brief["style"]+" "+intent["performance"]+" "+intent["concept"],re.I):
        return reject("Explicit BPM text; requires artistic review")
    # Only a single canonical global tempo header is supported; do not edit
    # local tempo changes or other fields. Preserve all original line endings.
    matches=list(re.finditer(r"(?m)^Q:1/4=([1-9][0-9]*)(?=\r?$)",abc))
    if (len(matches)!=1 or int(matches[0].group(1))!=tempo or
            len(re.findall(r"(?m)^\s*Q:|\[Q:",abc))!=1):
        return reject("Unsupported tempo header or tempo changes")
    score=parse_score(abc,native=True)
    units=sum(score.bar_lengths or (score.bar_units,)*score.counts["Vocal"])
    numerator=units*Fraction(score.headers["L"])*240
    required=numerator/Fraction(target)
    new_tempo=-(-required.numerator//required.denominator)
    if new_tempo<=tempo or Fraction(new_tempo,tempo)>MAX_TEMPO_RATIO:
        return reject("Required tempo change exceeds bounded 10 percent increase")
    match=matches[0]
    candidate=abc[:match.start(1)]+str(new_tempo)+abc[match.end(1):]
    a,b=nd.score_signature(abc,native=True),nd.score_signature(candidate,native=True)
    if a[0][:3]!=b[0][:3] or a[1:]!=b[1:]:
        return reject("Non-tempo score identity changed")
    decision=ar.evaluate_plan(candidate,brief,intent)
    if decision["decision"]!="retain":
        return reject("Candidate did not pass full score review")
    review=decision["score_review"]
    if review["metrics"]["score_seconds"]>target:
        return reject("Candidate does not preserve ending reserve")
    return {**result,"status":"candidate_available","original_tempo_bpm":tempo,
            "candidate_tempo_bpm":new_tempo,"original_score_seconds":original["metrics"]["score_seconds"],
            "candidate_score_seconds":review["metrics"]["score_seconds"],"cap_seconds":cap,
            "ending_reserve_seconds":ENDING_RESERVE_SECONDS,
            "candidate_score_sha256":review["score_sha256"],
            "notation_preserved_except_tempo":True,
            "note":"Advisory only: tempo changes pacing; native MIDI, acoustic and artistic acceptance are unverified."}
