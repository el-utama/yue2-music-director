"""Offline boundary benchmark for one annotated audio excerpt, not pronunciation QA."""
from pathlib import Path
import re
import statistics

from .native_recognition import _sha, _write
from .multilingual_fidelity import distance

# HTK label units are 100 nanoseconds. Restrict to three-field interval labels.
TICKS_PER_SECOND=10_000_000
MAX_TICKS=60*TICKS_PER_SECOND


def parse_htk(text):
    if not isinstance(text,str) or len(text)>256000:
        raise ValueError("Invalid or oversized HTK label input")
    rows=[]
    previous=0
    for line in text.splitlines():
        if not line.strip():
            continue
        parts=line.split()
        if (len(parts)!=3 or any(not re.fullmatch(r"[0-9]{1,10}",p) for p in parts[:2])
                or len(parts[2])>128):
            raise ValueError("Expected start end phoneme in integer HTK ticks")
        start,end=map(int,parts[:2])
        if start<previous or end<=start or end>MAX_TICKS:
            raise ValueError("Labels overlap, have invalid duration or exceed 60 seconds")
        rows.append((start,end,parts[2]))
        previous=end
    if not rows or len(rows)>2000:
        raise ValueError("Expected 1 to 2000 phoneme intervals")
    return rows


def percentile(values,p):
    ordered=sorted(values)
    index=(len(ordered)-1)*p
    lo=int(index)
    hi=min(lo+1,len(ordered)-1)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(index-lo)


def compare(reference,candidate):
    """Exact phone inventory and order required before any boundary metrics."""
    a,b=parse_htk(reference),parse_htk(candidate)
    labels_a,labels_b=[r[2] for r in a],[r[2] for r in b]
    result={"schema":"alignment-boundary-benchmark-v1","reference_intervals":len(a),
            "candidate_intervals":len(b),"sequence_edit_distance":distance(labels_a,labels_b),
            "status":"sequence_mismatch","boundary_metrics":None,
            "phonetic_alignment_verified":False,"correction_allowed":False,
            "warnings":["Reference and candidate must describe the same audio excerpt and phoneme inventory.",
                        "Reference independence and label quality are operator supplied, not verified.",
                        "Matching forced labels does not demonstrate that the phonemes were sung.",
                        "Boundary statistics are descriptive, not a calibrated correction threshold."]}
    if labels_a!=labels_b:
        return result
    starts=[(y[0]-x[0])/10000 for x,y in zip(a,b)]
    ends=[(y[1]-x[1])/10000 for x,y in zip(a,b)]
    # Shared boundaries counted once, not once per adjacent interval.
    pairs=sorted(set((x[i],y[i]) for x,y in zip(a,b) for i in (0,1)))
    errors=[(y-x)/10000 for x,y in pairs]
    absolute=list(map(abs,errors))
    result["status"]="boundary_metrics_available"
    result["boundary_metrics"]={"boundary_count":len(errors),
        "mean_signed_ms":statistics.mean(errors),"mean_absolute_ms":statistics.mean(absolute),
        "median_absolute_ms":statistics.median(absolute),"p95_absolute_ms":percentile(absolute,.95),
        "max_absolute_ms":max(absolute),"within_20ms_fraction":sum(e<=20 for e in absolute)/len(errors),
        "within_50ms_fraction":sum(e<=50 for e in absolute)/len(errors),
        "mean_absolute_start_ms":statistics.mean(map(abs,starts)),
        "mean_absolute_end_ms":statistics.mean(map(abs,ends))}
    return result


def benchmark(audio,reference,candidate,out):
    paths=[Path(p).resolve(strict=True) for p in (audio,reference,candidate)]
    out=Path(out).resolve()
    if out.exists() or len(set(paths))!=3:
        raise ValueError("Distinct input files and fresh report required")
    if paths[0].suffix.lower() not in (".wav",".flac"):
        raise ValueError("Expected audio excerpt WAV or FLAC")
    hashes=[_sha(p) for p in paths]
    result=compare(paths[1].read_text(encoding="utf-8-sig"),paths[2].read_text(encoding="utf-8-sig"))
    result.update({"audio_sha256":hashes[0],"reference_labels_sha256":hashes[1],
                   "candidate_labels_sha256":hashes[2],"audio_duration_verified":False,
                   "reference_provenance_verified":False,"alignment_calls":0,
                   "recognition_calls":0,"audio_jobs_created":0,"library_mutations":0})
    if [_sha(p) for p in paths]!=hashes:
        raise ValueError("Benchmark input changed")
    out.parent.mkdir(parents=True,exist_ok=True)
    _write(out,result)
    return result
