"""Independent release packaging. No synthesis, recognition, or publishing."""
import argparse
import json
import math
import re
import shutil
import sys
import tempfile
from pathlib import Path

from . import native_draft as nd, creative_core as cc, listening_director as ld
from .retained_source import load
from . import release_identity as ri
from .release_identity import safe_title
from .mcp import MCPError, configured_endpoint
from .temporal_evidence import parse_lrc, LINE
from .export_timing import read_timing
from .prosody import parse_lyrics
from . import native_collection as nc


def retained(repo,job):
    return load(repo,job)


def lyric_bytes(track):
    lyrics=track["brief"]["lyrics"]
    if track.get("identity",{}).get("production_policy")=="reviewed-score-v4-typed" and track["identity"]["creative_spec"].get("lyrics") is not None:
        if lyrics!=track["identity"]["creative_spec"]["lyrics"]:
            raise ValueError("Exact supplied lyric text differs")
        return lyrics.encode("utf-8")
    return (lyrics.rstrip()+"\n").encode("utf-8")


CLEAN_LYRIC_POLICY="section-stripped-stanzas-v1"
PRESETS={"production":"studio-display-anchors-v2","distribution":"not-requested-v1"}


def clean_lyric_bytes(track):
    """Use existing lyric section grammar, not a generative text rewrite.

    Keep repetitions, punctuation and sung parentheticals. Only standalone
    bracket section/direction tags and excess blank lines are removed.
    Ambiguous inline directions remain for human review.
    """
    groups=parse_lyrics(track["brief"]["lyrics"])
    stanzas=["\n".join(group["lines"]) for group in groups if group["lines"]]
    if not stanzas:
        raise ValueError("No sung lyric lines to export")
    return ("\n\n".join(stanzas)+"\n").encode("utf-8")


def stamp(ms,*,srt=False):
    minutes,rest=divmod(ms,60000)
    second,milli=divmod(rest,1000)
    if srt:
        hour,minute=divmod(minutes,60)
        return f"{hour:02}:{minute:02}:{second:02},{milli:03}"
    return f"{minutes:02}:{second:02}.{milli:03}"


def timed_text(lrc,lyrics,duration):
    # Match the pinned Studio UI's subtitle display policy, independently
    # implemented from app/services/lrc-parser.ts (bfd35a0).
    # Section labels are not sung cues; preserve them in the original LRC.
    if not isinstance(lrc,str) or len(lrc)>512000:
        raise ValueError("Invalid native LRC")
    sung=[]
    for raw in lrc.splitlines():
        match=LINE.fullmatch(raw.strip())
        if match and re.fullmatch(r"\[.*\]",match.group(4).strip()):
            continue
        sung.append(raw)
    rows=parse_lrc("\n".join(sung),duration)
    expected=[line for group in parse_lyrics(lyrics) for line in group["lines"]]
    if [" ".join(r["text"].split()) for r in rows]!=[" ".join(x.split()) for x in expected]:
        raise ValueError("Native LRC does not cover the exact lyric lines in order")
    cues=[]
    for i,row in enumerate(rows):
        start=row["start_seconds"]
        words=row["word_anchors"]
        ceiling=rows[i+1]["start_seconds"] if i+1<len(rows) else start+3
        if words:
            span=words[-1]["start_seconds"]-words[0]["start_seconds"]
            tail=span/(len(words)-1) if len(words)>1 else 0.8
            line_end=words[-1]["start_seconds"]+max(0.3,min(1.5,tail))
        else:
            line_end=start+4
        end=min(duration,ceiling,max(start+0.3,min(line_end,ceiling)))
        # JS Math.round for nonnegative time, with measured duration as extra cap.
        start_ms=math.floor(start*1000+0.5)
        end_ms=min(math.floor(end*1000+0.5),math.floor(duration*1000))
        if end_ms<=start_ms:
            raise ValueError("Timestamp precision collapses display interval")
        cues.append(f"{i+1}\n{stamp(start_ms,srt=True)} --> {stamp(end_ms,srt=True)}\n{row['text']}\n")
    return lrc,"\n".join(cues)


def playlist_bytes(names):
    """Portable relative paths only, in exact exported track order."""
    return ("#EXTM3U\n"+"\n".join(f"{name}/{name}.flac" for name in names)+"\n").encode("utf-8")


def verify_export(root,contract):
    manifest=nd.read(root/"release.json")
    if manifest.get("contract")!=contract:
        raise ValueError("Existing export differs; choose a new release ID")
    files=manifest.get("files")
    if not isinstance(files,dict) or not files:
        raise ValueError("Export manifest missing files")
    actual={p.relative_to(root).as_posix():nd._sha(p) for p in root.rglob("*")
            if p.is_file() and p!=root/"release.json"}
    if actual!=files:
        raise ValueError("Existing export file hashes differ")
    return manifest


def launch(repo,release,jobs,url,*,kind="single",title=None,artist="",snapshot=ri.DEFAULT_SNAPSHOT,confirm=False,timing_reader=None,preset="production",native_collection=None):
    if preset not in PRESETS:
        raise ValueError("Unknown export preset")
    cc.validate_job(release,"placeholder","en",195)
    url=configured_endpoint(url)
    selection=None
    if native_collection is not None:
        if jobs or kind!="single" or title is not None:
            raise ValueError("Native collection supplies its own type, title and order; do not override them")
        selection=nc.collection(url,native_collection)
        kind,title=selection["kind"],selection["name"]
        jobs=nc.retained_jobs(repo,selection)
    if (kind not in ri.FOLDERS or not 1<=len(jobs)<=(100 if kind=="playlist" else 24)
            or len(set(jobs))!=len(jobs) or (kind=="single" and len(jobs)!=1)):
        raise ValueError("Select distinct ordered tracks: single 1, EP/album up to 24, playlist up to 100")
    if (title is not None and (not isinstance(title,str) or not title.strip() or len(title)>150)
            or not isinstance(artist,str) or len(artist)>150 or (kind!="single" and not title)):
        raise ValueError("Album/EP requires title; invalid release metadata")
    tracks=[retained(repo,j) for j in jobs]
    if selection is not None and [t["result"].get("song_id") for t in tracks]!=selection["song_ids"]:
        raise ValueError("Retained result does not match native collection order")
    title=title or tracks[0]["brief"]["title"]
    exports=repo/"results/exports"
    original_contract={"schema":"release-export-v1","release":release,"type":kind,"title":title,"artist":artist,
                       "sources":[t["evidence"] for t in tracks],"audio_variant":"original",
                       "timing_policy":PRESETS[preset]}
    if selection is not None:
        original_contract["native_collection"]=selection
    def destination():
        original,index,record=ri.original(exports,original_contract)
        root,contract=ri.revision(exports,original_contract,original,snapshot)
        if snapshot!=ri.DEFAULT_SNAPSHOT:
            verify_export(original,original_contract)
        return root,contract,index,record
    root,contract,index,record=destination()
    print("Export folder:",root,flush=True)
    print("Export preset:",preset,flush=True)
    if not confirm:
        print("Plan only; no package writes or inference." if selection is not None else "Plan only; no writes or Studio calls.",flush=True)
        return 0
    with ld.lock(exports/".active",context={"root":root.relative_to(repo).as_posix(),"stage":"export","release":release}):
        if destination()!=(root,contract,index,record):
            raise ValueError("Release destination changed during preparation")
        if root.exists():
            manifest=verify_export(root,contract)
            print("Existing export verified:",root,flush=True)
            return 0 if manifest["status"]=="complete" else 2
        width=max(2,len(str(len(tracks))))
        names=[f"{i:0{width}d} - {safe_title(t['brief']['title'])}" if kind!="single" else safe_title(t["brief"]["title"])
               for i,t in enumerate(tracks,1)]
        def paths(base):
            return [base/"release.json",*([base/"playlist.m3u8"] if kind=="playlist" else []),*[(base/name if kind!="single" else base)/(name+suffix)
                    for name in names for suffix in (".flac",".txt",".clean.txt",".lrc",".srt")]]
        ri.ensure_paths([index,*paths(root)])
        ri.reserve(index,record)
        base=root.parent
        base.mkdir(parents=True,exist_ok=True)
        stage=Path(tempfile.mkdtemp(prefix=".export-",dir=base))
        try:
            ri.ensure_paths(paths(stage))
            details=[]
            for i,t in enumerate(tracks,1):
                name=names[i-1]
                dest=stage/name if kind!="single" else stage
                dest.mkdir(exist_ok=True)
                target=dest/(name+".flac")
                shutil.copyfile(t["audio"],target)
                if nd._sha(target)!=t["result"]["audio_sha256"] or nd._sha(t["audio"])!=t["result"]["audio_sha256"]:
                    raise ValueError("Audio changed during export")
                lyrics=t["brief"]["lyrics"]
                (dest/(name+".txt")).write_bytes(lyric_bytes(t))
                (dest/(name+".clean.txt")).write_bytes(clean_lyric_bytes(t))
                timing={"status":"unavailable","acoustic_timing_verified":False}
                if preset=="distribution":
                    timing={"status":"not_requested","acoustic_timing_verified":False}
                else:
                    try:
                        lrc=(timing_reader or read_timing)(t,url)
                        if not lrc:
                            raise ValueError("No retained native karaoke LRC")
                        lrc_out,srt_out=timed_text(lrc,lyrics,t["report"]["acoustic"]["duration_seconds"])
                    except (ValueError,MCPError,TypeError,KeyError,OSError) as exc:
                        timing["reason"]=str(exc)
                    else:
                        # Write failures are not timing unavailability. Abort the
                        # staged export instead of publishing a partial timed pair.
                        (dest/(name+".lrc")).write_bytes(lrc_out.encode("utf-8"))
                        (dest/(name+".srt")).write_bytes(srt_out.encode("utf-8"))
                        timing={"status":"exported_unverified_display_anchors","acoustic_timing_verified":False,
                                "source_lrc_sha256":nd.digest(lrc.encode("utf-8")),
                                "srt_end_policy":"Studio UI word-tail/plain-line heuristic; capped at next onset, final 3 seconds and measured duration",
                                "lrc_preserved":True}
                        if timing_reader is None:
                            timing["source_identity_screen"]="matched_retained_audio_and_stable_library_snapshot_v1"
                            timing["karaoke_provenance_verified"]=False
                if nd._sha(t["audio"])!=t["result"]["audio_sha256"]:
                    raise ValueError("Source audio changed during timing export")
                details.append({"track":i,"job":t["job"],"title":t["brief"]["title"],"audio_sha256":t["result"]["audio_sha256"],
                                "source_status":t["result"]["status"],"timing":timing})
                print("Track",i,":",timing["status"],flush=True)
            if selection is not None and nc.collection(url,native_collection)!=selection:
                raise ValueError("Native collection changed during export; preserve previous package")
            if kind=="playlist":
                (stage/"playlist.m3u8").write_bytes(playlist_bytes(names))
            files={p.relative_to(stage).as_posix():nd._sha(p) for p in stage.rglob("*") if p.is_file()}
            manifest={"contract":contract,"tracks":details,"files":files,
                      "lyric_assets":CLEAN_LYRIC_POLICY,
                      "status":"complete" if all(t["timing"]["status"] in ("exported_unverified_display_anchors","not_requested") for t in details) else "partial_missing_timing",
                      "release_approved":False,"studio_mutations":0,"inference_calls":0}
            nd.atomic_write(stage/"release.json",manifest)
            if root.exists():
                raise ValueError("Export destination appeared; preserve existing folder")
            stage.rename(root)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    print("Export:",manifest["status"],root,flush=True)
    print("Original audio preserved. No inference, publishing or timing fabrication.",flush=True)
    return 0 if manifest["status"]=="complete" else 2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--url",required=True)
    p.add_argument("--export",required=True,nargs="?",const="",metavar="RELEASE")
    p.add_argument("--list-collections",action="store_true",help="Read native playlist and album IDs, names and track counts")
    p.add_argument("--native-collection",metavar="ID",help="Export exact native playlist or album in its current track order")
    p.add_argument("--song",action="append")
    p.add_argument("--type",choices=tuple(ri.FOLDERS),default="single")
    p.add_argument("--title")
    p.add_argument("--artist",default="")
    p.add_argument("--preset",choices=sorted(PRESETS),default="production",help="production: audio, both lyric texts and native LRC/SRT; distribution: audio and both lyric texts only")
    p.add_argument("--snapshot",default=ri.DEFAULT_SNAPSHOT,help="Explicit immutable revision of existing v1 release")
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        if a.list_collections:
            if a.export or a.song or a.native_collection or a.confirm_run or a.title or a.artist or a.type!="single" or a.snapshot!=ri.DEFAULT_SNAPSHOT or a.preset!="production":
                raise ValueError("Use --export --list-collections alone")
            print(json.dumps(nc.collections(a.url),ensure_ascii=False,indent=2))
            return 0
        if not a.export:
            raise ValueError("Export release ID required")
        return launch(a.repo.resolve(),a.export,a.song or ([] if a.native_collection else [a.export]),a.url,kind=a.type,title=a.title,artist=a.artist,snapshot=a.snapshot,confirm=a.confirm_run,preset=a.preset,native_collection=a.native_collection)
    except (OSError,ValueError,KeyError,TypeError,MCPError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
