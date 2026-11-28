"""Bounded duration fit; explicit artistic approval is required before synthesis."""
from fractions import Fraction
import re
from . import native_draft as nd, artist_run as ar
from .music import parse_score

MAX_TEMPO_RATIO = Fraction(11,10)
ENDING_RESERVE_SECONDS = 3
FIT_SCHEMA="retained-duration-continuation-v1"
# Only simple integer BPM descriptions are eligible for a deterministic edit.
BPM=re.compile(r"(?<![\d.])(?:(?P<left>\d{1,3})(?P<suffix>\s*bpm\b)|(?P<prefix>\bbpm\s*[:=]?\s*)(?P<right>\d{1,3})(?![\d.]))",re.I)


def revised_inputs(brief,intent,new_tempo):
    if intent.get("schema")!="artist-intent-v1":
        raise ValueError("Typed musical requirements are outside this recovery")
    b,i=dict(brief),dict(intent)
    fields=[(b,"style","style"),(i,"concept","concept"),(i,"performance","performance"),
            (i,"emotional_arc","emotional_arc")]
    evidence={}
    for owner,key,label in fields:
        value=owner[key]
        if not re.search(r"\bbpm\b",value,re.I):
            # A numeric tempo expressed without BPM is not a simple BPM edit.
            if re.search(r"\btempo\s*[:=]?\s*\d|\d\s*beats per minute",value,re.I):
                raise ValueError("Unsupported textual tempo expression")
            continue
        hits=list(BPM.finditer(value))
        if (len(hits)!=len(re.findall(r"\bbpm\b",value,re.I)) or
                re.search(r"\d\s*(?:[-–—/]|to)\s*\d|\d+\.\d+",value,re.I)):
            raise ValueError("Ambiguous BPM text; requires separate artistic revision")
        values=[int(h.group("left") or h.group("right")) for h in hits]
        if any(v<20 or v>300 for v in values):
            raise ValueError("Unsupported BPM value")
        evidence[label]=values
        owner[key]=BPM.sub(lambda h: str(new_tempo)+h.group("suffix") if h.group("left")
                           else h.group("prefix")+str(new_tempo),value)
    if len({v for values in evidence.values() for v in values})>1:
        raise ValueError("Conflicting BPM values; requires separate artistic revision")
    if any(re.search(r"\bbpm\b|\btempo\s*[:=]?\s*\d",v,re.I)
           for v in i["section_purposes"].values()):
        raise ValueError("Section-specific tempo text is outside this recovery")
    ar.validate_intent(i)
    return b,i,evidence


def replace_tempo(abc,tempo,new_tempo):
    matches=list(re.finditer(r"(?m)^Q:1/4=([1-9][0-9]*)(?=\r?$)",abc))
    if (len(matches)!=1 or int(matches[0].group(1))!=tempo or
            len(re.findall(r"(?m)^\s*Q:|\[Q:",abc))!=1):
        raise ValueError("Unsupported tempo header or tempo changes")
    match=matches[0]
    return abc[:match.start(1)]+str(new_tempo)+abc[match.end(1):]


def propose(abc,brief,intent,*,request=None):
    original=ar.evaluate_plan(abc,brief,intent)["score_review"]
    result={"schema":"duration-fit-preview-v2","status":"not_eligible",
            "provider_calls":0,"studio_calls":0,"render_authorized":False,
            "original_score_sha256":nd.digest(abc.encode("utf-8"))}
    def reject(reason):
        return {**result,"reason":reason},None
    hard=original["hard_violations"]
    if (original["status"]!="blocked" or len(hard)!=1 or
            hard[0]["code"]!="score_clock_exceeds_cap" or original["soft_flags"]):
        return reject("Requires duration-only rejection with no soft flags")
    tempo=int(original["metrics"]["tempo_bpm"])
    cap=brief["duration_seconds"]
    target=cap-ENDING_RESERVE_SECONDS
    result.update(original_tempo_bpm=tempo,original_score_seconds=original["metrics"]["score_seconds"],
                  cap_seconds=cap,ending_reserve_seconds=ENDING_RESERVE_SECONDS)
    if target<=0:
        return reject("No available duration reserve")
    if intent["constraints"].get("tempo_bpm",{}).get("mode") in ("must","prefer"):
        return reject("Explicit tempo constraint; do not change")
    # Natural-language detection is deliberately conservative, not a guarantee
    # of all possible user constraints. The operator must approve the exact BPM.
    if request is not None and re.search(r"\bbpm\b|\btempo\b|\bketukan\b|\bbeats per minute\b",request,re.I):
        return reject("Original request mentions tempo; requires separate artistic revision")
    score=parse_score(abc,native=True)
    units=sum(score.bar_lengths or (score.bar_units,)*score.counts["Vocal"])
    numerator=units*Fraction(score.headers["L"])*240
    required=numerator/Fraction(target)
    new_tempo=-(-required.numerator//required.denominator)
    if new_tempo<=tempo or Fraction(new_tempo,tempo)>MAX_TEMPO_RATIO:
        return reject("Required tempo change exceeds bounded 10 percent increase")
    try:
        candidate=replace_tempo(abc,tempo,new_tempo)
        b,i,evidence=revised_inputs(brief,intent,new_tempo)
    except ValueError as exc:
        return reject(str(exc))
    a,c=nd.score_signature(abc,native=True),nd.score_signature(candidate,native=True)
    if a[0][:3]!=c[0][:3] or a[1:]!=c[1:]:
        return reject("Non-tempo score identity changed")
    decision=ar.evaluate_plan(candidate,b,i)
    if decision["decision"]!="retain":
        return reject("Candidate did not pass full score review")
    review=decision["score_review"]
    if review["metrics"]["score_seconds"]>target:
        return reject("Candidate does not preserve ending reserve")
    result.update(status="artistic_review_required" if evidence else "candidate_available",
                  candidate_tempo_bpm=new_tempo,candidate_score_seconds=review["metrics"]["score_seconds"],
                  candidate_score_sha256=review["score_sha256"],notation_preserved_except_tempo=True,
                  tempo_text_fields=evidence,
                  note="Advisory only: approve the exact proposed BPM before synthesis; native MIDI, acoustic and artistic acceptance are unverified.")
    return result,{"abc":candidate,"brief":b,"intent":i,"review":decision}


def preview(abc,brief,intent,*,request=None):
    return propose(abc,brief,intent,request=request)[0]


def verify_frozen(parent,root,contract):
    """Byte-linked immutable revised inputs; no current score parser on historical reads."""
    original=parent/"production"
    production=root/"production"
    old=nd.read(original/"journal_plan.json")
    original_abc=(original/"native-plan.abc").read_bytes().decode("utf-8")
    candidate=(production/"duration-fit.abc").read_bytes().decode("utf-8")
    fit=contract["fit"]
    if (fit.get("schema")!="duration-fit-preview-v2" or fit.get("status") not in ("candidate_available","artistic_review_required")
            or fit.get("render_authorized") is not False
            or old.get("state")!="COMPLETED" or old.get("score_sha256")!=fit.get("original_score_sha256")
            or nd.digest(original_abc.encode("utf-8"))!=fit.get("original_score_sha256")
            or nd.digest(candidate.encode("utf-8"))!=fit.get("candidate_score_sha256")
            or contract.get("approved_tempo_bpm")!=fit.get("candidate_tempo_bpm")
            or replace_tempo(original_abc,fit["original_tempo_bpm"],fit["candidate_tempo_bpm"])!=candidate
            or not 1<Fraction(fit["candidate_tempo_bpm"],fit["original_tempo_bpm"])<=MAX_TEMPO_RATIO):
        raise ValueError("Retained duration fit identity differs")
    b,i,evidence=revised_inputs(nd.load_brief(parent/"brief.json"),nd.read(parent/"intent.json"),fit["candidate_tempo_bpm"])
    if (evidence!=fit["tempo_text_fields"] or b!=nd.load_brief(root/"brief.json")
            or i!=nd.read(root/"intent.json") or contract["review"]!=nd.read(production/"plan-decision.json")
            or contract["review"].get("decision")!="retain"
            or contract["review"]["score_review"].get("score_sha256")!=fit["candidate_score_sha256"]
            or contract["review"]["score_review"]["metrics"].get("score_seconds")!=fit["candidate_score_seconds"]
            or fit["candidate_score_seconds"]>b["duration_seconds"]-ENDING_RESERVE_SECONDS):
        raise ValueError("Retained revised brief or score decision differs")
    return candidate,b,i
