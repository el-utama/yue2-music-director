"""Read existing karaoke anchors; never generate, edit or mistake interpolation for ASR."""
import math
import re
from pathlib import Path

from .mcp import Client, configured_endpoint, unpack
from .native_process import _source_file
from .native_recognition import _sha, _write, _recognition, review
from .finishing_selection import read
from .prosody import parse_lyrics
from .multilingual_fidelity import assess

STAMP=r"(\d{1,4}):(\d{2})[.](\d{2,3})"
LINE=re.compile(r"^\["+STAMP+r"\](.*)$")
WORD=re.compile(r"<"+STAMP+r">")


def seconds(groups):
    minute,second,frac=groups
    if int(second)>=60:
        raise ValueError("Invalid seconds in LRC timestamp")
    return int(minute)*60+int(second)+int(frac)/10**len(frac)


def parse_lrc(lrc,duration):
    if not isinstance(lrc,str) or len(lrc)>512000 or not math.isfinite(duration) or not 0<duration<=1800:
        raise ValueError("Invalid LRC or audio duration")
    rows=[]
    previous=-1
    previous_word=-1
    for line in lrc.splitlines():
        line=line.strip()
        if not line:
            continue
        match=LINE.fullmatch(line)
        if match is None:
            raise ValueError("Unsupported LRC line format or metadata")
        start=seconds(match.groups()[:3])
        if start<=previous or start>=duration or start<previous_word:
            raise ValueError("LRC line starts are not strictly ordered within source duration")
        previous=start
        body=match.group(4)
        tags=list(WORD.finditer(body))
        words=[]
        if tags:
            if body[:tags[0].start()].strip():
                raise ValueError("Untagged text before enhanced LRC words")
            last=start
            for i,tag in enumerate(tags):
                time=seconds(tag.groups())
                word=body[tag.end():tags[i+1].start() if i+1<len(tags) else len(body)].strip()
                if not word or "<" in word or ">" in word or time<last or time>=duration:
                    raise ValueError("Malformed or unordered enhanced LRC word")
                words.append({"text":word,"start_seconds":time,"provenance":"unknown_matched_or_interpolated"})
                last=time
            previous_word=last
            text=" ".join(w["text"] for w in words)
        else:
            if "<" in body or ">" in body:
                raise ValueError("Malformed word timing tag")
            text=body.strip()
            previous_word=start
        if not text:
            raise ValueError("Empty timed line")
        rows.append({"text":text,"start_seconds":start,"word_anchors":words})
    if not rows:
        raise ValueError("No timed lines")
    return rows


def karaoke_metadata(song,song_id,*,detailed=False):
    """Studio Song.metadata is nullable JSON; concise exposes has_karaoke."""
    if not isinstance(song,dict):
        raise ValueError("Unrecognized library response type: "+type(song).__name__)
    if song.get("id")!=song_id:
        raise ValueError("Library response identity mismatch or missing id; object fields="+str(len(song)))
    if "metadata" not in song:
        raise ValueError("Library response missing metadata field")
    metadata=song["metadata"]
    if metadata is None:
        return None
    if not isinstance(metadata,dict):
        raise ValueError("Unexpected library metadata type: "+type(metadata).__name__)
    if detailed:
        if "lrc" not in metadata and metadata.get("has_karaoke") is True:
            raise ValueError("Detailed response omitted advertised karaoke content")
        return metadata.get("lrc")
    if metadata.get("has_karaoke") is False and "lrc" not in metadata:
        return None
    if metadata.get("has_karaoke") is True:
        return True
    if "lrc" in metadata:
        return metadata["lrc"]
    # Older concise implementations may omit the flag. Verify with detailed.
    return True


def inspect_timing(source, song_id, lyrics, baseline_asr, language, duration, out, url=None):
    """Read existing library metadata only; no karaoke_make or recognition."""
    source,lyrics,baseline_asr=[Path(p).resolve(strict=True) for p in (source,lyrics,baseline_asr)]
    out=Path(out).resolve()
    if out.exists():
        raise ValueError("Fresh timing evidence report required")
    if not isinstance(song_id,str) or not song_id.strip():
        raise ValueError("Song ID required")
    if not math.isfinite(duration) or not 0<duration<=1800:
        raise ValueError("Measured source duration required")
    hashes=[_sha(p) for p in (source,lyrics,baseline_asr)]
    reference=lyrics.read_text(encoding="utf-8-sig")
    raw=read(baseline_asr)
    assess(reference,_recognition(raw),language)
    client=Client(configured_endpoint(url),timeout=30).connect()
    if not {"library_song_get","library_song_files"}<={t.get("name") for t in client.tools()}:
        raise ValueError("Required read-only Studio tools missing")
    _source_file(unpack(client.call("library_song_files",{"song_id":song_id})),source)
    song=unpack(client.call("library_song_get",{"song_id":song_id,"response_format":"concise"}))
    lrc=karaoke_metadata(song,song_id)
    if lrc is True:
        song=unpack(client.call("library_song_get",{"song_id":song_id,"response_format":"detailed"}))
        lrc=karaoke_metadata(song,song_id,detailed=True)
        if lrc is None or lrc=="":
            raise ValueError("Detailed response lacks expected karaoke; cannot verify availability")
    result={"schema":"temporal-evidence-v1","source_sha256":hashes[0],"lyrics_sha256":hashes[1],
            "baseline_asr_sha256":hashes[2],"duration_seconds_operator_supplied":duration,
            "status":"no_existing_karaoke","lines":[],"phonetic_alignment_verified":False,
            "audio_timestamps_verified":False,"correction_allowed":False,
            "recognition_calls":0,"audio_jobs_created":0,"processing_calls":0,"library_mutations":0,
            "warnings":["Existing LRC may be imported, edited, stale or interpolated.",
                        "Upstream karaoke matches written words and interpolates unmatched words; no observed/interpolated flag is serialized.",
                        "No phoneme timing, word end times, or verified sung pronunciation.",
                        "Source path identity does not authenticate karaoke provenance; supplied duration is not independently measured here."]}
    if lrc is not None and lrc!="":
        try:
            rows=parse_lrc(lrc,duration)
            expected=[(g["name"],g["occurrence"],i,line) for g in parse_lyrics(reference)
                      for i,line in enumerate(g["lines"],1)]
            if len(rows)!=len(expected) or any(" ".join(row["text"].split())!=" ".join(e[3].split()) for row,e in zip(rows,expected)):
                raise ValueError("Karaoke text/order differs from frozen reference")
            localization=None
            if language=="en":
                mapped=review(reference,raw,raw)
                localization={(p["section"],p["line_index"]):p["A_count"] for p in mapped["reference_lines"]}
            for row,(name,occ,i,_) in zip(rows,expected):
                section=f"{name}#{occ}"
                result["lines"].append({"section":section,"line_index":i,
                    "start_seconds":row["start_seconds"],"word_anchor_count":len(row["word_anchors"]),
                    "word_start_seconds":[w["start_seconds"] for w in row["word_anchors"]],
                    "asr_line_edits":localization[(section,i)] if localization is not None else None,
                    "timing_evidence":"unverified_karaoke_display_anchor"})
            result["status"]="karaoke_display_anchors_only"
        except ValueError as exc:
            result["status"]="karaoke_evidence_blocked"
            result["reason"]=str(exc)
    _source_file(unpack(client.call("library_song_files",{"song_id":song_id})),source)
    if [_sha(p) for p in (source,lyrics,baseline_asr)]!=hashes:
        raise ValueError("Timing evidence inputs changed")
    out.parent.mkdir(parents=True,exist_ok=True)
    _write(out,result)
    return result
