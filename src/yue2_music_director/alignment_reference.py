"""Prepare a short, independently annotated WAV excerpt without inference."""
import re
import wave
from fractions import Fraction
from pathlib import Path

from .alignment_benchmark import TICKS_PER_SECOND, parse_htk
from .native_recognition import _sha, _write

MAX_SOURCE_SECONDS=600
MAX_EXCERPT_SECONDS=60


def labels(text,unit):
    if unit not in ("htk","seconds") or len(text)>512000:
        raise ValueError("Explicit label unit and bounded annotation required")
    rows=[]
    previous=0
    for line in text.splitlines():
        if not line.strip():
            continue
        parts=line.split()
        if len(parts)!=3 or len(parts[2])>128:
            raise ValueError("Expected three-field phoneme interval")
        ticks=[]
        for value in parts[:2]:
            pattern=r"[0-9]{1,10}" if unit=="htk" else r"[0-9]{1,3}(?:\.[0-9]{1,7})?"
            if not re.fullmatch(pattern,value):
                raise ValueError("Invalid timestamp or precision")
            ticks.append(int(Fraction(value)*(TICKS_PER_SECOND if unit=="seconds" else 1)))
        a,b=ticks
        if a<previous or b<=a or b>MAX_SOURCE_SECONDS*TICKS_PER_SECOND:
            raise ValueError("Overlapping, empty or out-of-range annotation interval")
        previous=b
        rows.append((a,b,parts[2]))
    if not rows or len(rows)>10000:
        raise ValueError("Expected 1 to 10000 intervals")
    return rows


def prepare(audio, annotation, unit, first, last, out):
    audio,annotation=[Path(p).resolve(strict=True) for p in (audio,annotation)]
    out=Path(out).resolve()
    if audio==annotation or audio.suffix.lower()!=".wav" or out.exists():
        raise ValueError("Distinct PCM WAV and labels, fresh output required")
    hashes=[_sha(p) for p in (audio,annotation)]
    rows=labels(annotation.read_text(encoding="utf-8-sig"),unit)
    if (type(first) is not int or type(last) is not int
            or not 1<=first<=last<=len(rows)):
        raise ValueError("Invalid one-based inclusive interval range")
    selected=rows[first-1:last]
    if any(x[1]!=y[0] for x,y in zip(selected,selected[1:])):
        raise ValueError("Selected reference must be contiguous; no invented gap labels")
    with wave.open(str(audio),"rb") as src:
        rate,channels,width,frames=(src.getframerate(),src.getnchannels(),src.getsampwidth(),src.getnframes())
        if (src.getcomptype()!="NONE" or not 8000<=rate<=96000 or channels not in (1,2)
                or width not in (2,3) or not 0<frames<=rate*MAX_SOURCE_SECONDS):
            raise ValueError("Expected 8-96 kHz mono/stereo 16/24-bit PCM WAV, up to 10 minutes")
        if rows[-1][1]*rate>frames*TICKS_PER_SECOND:
            raise ValueError("Annotation extends beyond audio")
        start=round(Fraction(selected[0][0]*rate,TICKS_PER_SECOND))
        end=round(Fraction(selected[-1][1]*rate,TICKS_PER_SECOND))
        if not 0<end-start<=rate*MAX_EXCERPT_SECONDS:
            raise ValueError("Excerpt must be positive and no longer than 60 seconds")
        # Interior boundaries retain their original annotation precision.
        origin=Fraction(start*TICKS_PER_SECOND,rate)
        duration=round(Fraction((end-start)*TICKS_PER_SECOND,rate))
        relative=[(max(0,round(a-origin)),min(duration,round(b-origin)),p)
                  for a,b,p in selected]
        relative[0]=(0,relative[0][1],relative[0][2])
        relative[-1]=(relative[-1][0],duration,relative[-1][2])
        lab="".join(f"{a} {b} {p}\n" for a,b,p in relative)
        parse_htk(lab)
        src.setpos(start)
        pcm=src.readframes(end-start)
        if len(pcm)!=(end-start)*channels*width:
            raise ValueError("Truncated source PCM")
    if [_sha(p) for p in (audio,annotation)]!=hashes:
        raise ValueError("Source inputs changed")
    out.mkdir(parents=True,exist_ok=False)
    target=out/"excerpt.wav"
    with wave.open(str(target),"wb") as dst:
        dst.setnchannels(channels)
        dst.setsampwidth(width)
        dst.setframerate(rate)
        dst.writeframes(pcm)
    ref=out/"reference.lab"
    ref.write_text(lab,encoding="utf-8")
    (out/"phones.txt").write_text(" ".join(p for _,_,p in relative)+"\n",encoding="utf-8")
    report={"schema":"alignment-reference-excerpt-v1","source_audio_sha256":hashes[0],
            "source_annotation_sha256":hashes[1],"source_label_unit":unit,
            "first_interval":first,"last_interval":last,"interval_count":len(relative),
            "source_start_frame":start,"source_end_frame_exclusive":end,"sample_rate_hz":rate,
            "channels":channels,"bits_per_sample":width*8,"excerpt_duration_seconds":(end-start)/rate,
            "excerpt_sha256":_sha(target),"reference_sha256":_sha(ref),
            "phone_sequence_sha256":_sha(out/"phones.txt"),
            "reference_provenance_verified":False,"correction_allowed":False,
            "alignment_calls":0,"recognition_calls":0,"audio_jobs_created":0,"library_mutations":0,
            "warnings":["Source annotation independence and license are operator supplied.",
                        "Audio cut at nearest sample; outer interval bounds snapped to excerpt edges.",
                        "No resampling or label inventory conversion; no phoneme inference."]}
    _write(out/"report.json",report)
    return report
