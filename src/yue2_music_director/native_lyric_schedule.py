"""Advisory evidence of the saved native lyric schedule, never sung alignment."""
import re

_TAG = re.compile(r"^\[\s*([^\]]*?)\s*\]$")
_INSTRUMENTAL = re.compile(r"\b(instrumental|solo|break|interlude)\b", re.I)


def _sung_blocks(lyrics):
    """Match the pinned Studio's tagged, alphanumeric sung block convention."""
    blocks=[]
    current=None
    offset=0
    for line in lyrics.split("\n"):
        tag=_TAG.fullmatch(line.strip())
        if tag:
            if current is not None:
                blocks.append((*current,offset))
            current=(offset,tag[1],False)
        elif current is not None and any(c.isalnum() for c in line):
            current=(current[0],current[1],True)
        offset+=len(line)+1
    if current is not None:
        blocks.append((*current,len(lyrics)))
    return [(start,start+len(lyrics[start:end].rstrip()))
            for start,label,sung,end in blocks if sung and not _INSTRUMENTAL.search(label)]


def _number(value,low,high=None):
    return (type(value) in (int,float) and low<=value
            and (high is None or value<=high)
            and abs(value)<=1e308)


def inspect_schedule(settings):
    """Summarize saved metadata only; no inference or acoustic timing claim."""
    result={"schema":"native-lyric-schedule-evidence-v1",
            "source":"saved_generation_settings","status":"unknown",
            "expected_sung_blocks":None,"scheduled_sung_blocks":None,
            "mode":None,"first_vocal_score_seconds":None,
            "last_vocal_score_seconds":None,
            "acoustic_alignment_verified":False,
            "interpretation":"Recorded section-level conditioning, not measured singing or syllable alignment."}
    if not isinstance(settings,dict):
        return result
    lyrics=settings.get("lyrics")
    if not isinstance(lyrics,str) or "\r" in lyrics:
        return result
    blocks=_sung_blocks(lyrics)
    result["expected_sung_blocks"]=len(blocks)
    if "lyric_schedule" not in settings or settings["lyric_schedule"] is None:
        result["status"]="not_recorded"
        return result
    result["status"]="invalid_or_unrecognized"
    schedule=settings["lyric_schedule"]
    if not isinstance(schedule,dict) or schedule.get("mode") not in ("bias","mask"):
        return result
    mode=schedule["mode"]
    if mode=="bias" and (not _number(schedule.get("bias"),-60,0) or schedule["bias"]==0):
        return result
    if settings.get("cot")=="off" or ("cfg_scale" in settings and settings["cfg_scale"]!=1):
        return result
    entries=schedule.get("sections")
    if not isinstance(entries,list) or not 1<=len(entries)<=256:
        return result
    index={span:i for i,span in enumerate(blocks)}
    matched=[]
    times=[]
    for item in entries:
        if not isinstance(item,dict):
            return result
        span=item.get("lyric")
        start=item.get("start_sec")
        if (not isinstance(span,list) or len(span)!=2 or any(type(v) is not int for v in span)
                or not _number(start,0) or (times and start<times[-1])):
            return result
        i=index.get(tuple(span))
        if i is None or (matched and i<=matched[-1]):
            return result
        matched.append(i)
        times.append(start)
    result.update(status="all_blocks_recorded" if len(matched)==len(blocks) else "partial_blocks_recorded",
                  mode=mode,scheduled_sung_blocks=len(matched),
                  first_vocal_score_seconds=times[0],last_vocal_score_seconds=times[-1])
    return result
