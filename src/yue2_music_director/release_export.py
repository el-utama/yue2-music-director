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
from .temporal_evidence import parse_lrc, LINE, WORD
from .export_timing import read_timing
from .prosody import parse_lyrics
from . import native_collection as nc, native_library_export as nl
from .export_selection import by_name


def retained(repo,job):
    return load(repo,job)


def lyric_bytes(track):
    lyrics=track["brief"]["lyrics"]
    if "native_snapshot" in track:
        return lyrics.encode("utf-8")
    if track.get("identity",{}).get("production_policy")=="reviewed-score-v4-typed" and track["identity"]["creative_spec"].get("lyrics") is not None:
        if lyrics!=track["identity"]["creative_spec"]["lyrics"]:
            raise ValueError("Exact supplied lyric text differs")
        return lyrics.encode("utf-8")
    return (lyrics.rstrip()+"\n").encode("utf-8")


CLEAN_LYRIC_POLICY="section-stripped-stanzas-v1"
PRESETS={"production":"studio-display-anchors-v2","distribution":"not-requested-v1",
         "video":"studio-display-video-v1"}


def lyric_stanzas(lyrics,*,library_only=False):
    if not library_only:
        return [g["lines"] for g in parse_lyrics(lyrics) if g["lines"]]
    # Native written text can be plain, tagged or instrumental. Keep words
    # and stanza boundaries; never guess the meaning of an inline direction.
    groups=[]
    current=[]
    for line in lyrics.splitlines():
        line=line.strip()
        if not line or re.fullmatch(r"\[[^\]]+\]",line):
            if current:
                groups.append(current)
                current=[]
        else:
            current.append(line)
    if current:
        groups.append(current)
    return groups


def clean_lyric_bytes(track):
    """Use existing lyric section grammar, not a generative text rewrite.

    Keep repetitions, punctuation and sung parentheticals. Only standalone
    bracket section/direction tags and excess blank lines are removed.
    Ambiguous inline directions remain for human review.
    """
    library_only="native_snapshot" in track
    stanzas=["\n".join(lines) for lines in lyric_stanzas(track["brief"]["lyrics"],library_only=library_only)]
    if not stanzas:
        if library_only:
            return b""
        raise ValueError("No sung lyric lines to export")
    return ("\n\n".join(stanzas)+"\n").encode("utf-8")


def stamp(ms,*,srt=False):
    minutes,rest=divmod(ms,60000)
    second,milli=divmod(rest,1000)
    if srt:
        hour,minute=divmod(minutes,60)
        return f"{hour:02}:{minute:02}:{second:02},{milli:03}"
    return f"{minutes:02}:{second:02}.{milli:03}"


def timing_rows(lrc,lyrics,duration,*,library_only=False,video=False):
    # Match the pinned Studio UI's subtitle display policy, independently
    # implemented from app/services/lrc-parser.ts (bfd35a0).
    # Section labels are not sung cues; preserve them in the original LRC.
    if not isinstance(lrc,str) or len(lrc)>512000:
        raise ValueError("Invalid native LRC")
    sung=[]
    for raw in lrc.splitlines():
        if video:
            # Only known non-timing headers are ignored in derived assets.
            # An offset changes the clock; require corrected native timing.
            raw=raw.lstrip("\ufeff") if not sung else raw
            if re.fullmatch(r"\[(?:ar|al|ti|au|by|re|ve|length):[^\]]*\]",raw.strip(),re.I):
                continue
            if re.fullmatch(r"\[offset:[+-]?0+\]",raw.strip(),re.I):
                continue
        match=LINE.fullmatch(raw.strip())
        if match and re.fullmatch(r"\[.*\]",match.group(4).strip()):
            continue
        sung.append(raw)
    rows=parse_lrc("\n".join(sung),duration)
    expected=[line for group in lyric_stanzas(lyrics,library_only=library_only) for line in group]
    if [" ".join(r["text"].split()) for r in rows]!=[" ".join(x.split()) for x in expected]:
        raise ValueError("Native LRC does not cover the exact lyric lines in order")
    return rows


def timed_text(lrc,lyrics,duration,*,library_only=False,video=False):
    rows=timing_rows(lrc,lyrics,duration,library_only=library_only,video=video)
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


def video_line_bytes(lrc,lyrics,duration,*,library_only=False):
    rows=timing_rows(lrc,lyrics,duration,library_only=library_only,video=True)
    lines=[]
    for row in rows:
        ms=math.floor(row["start_seconds"]*1000+0.5)
        time=stamp(ms)
        if ms%10==0:
            time=time[:-1]
        lines.append("[{}]{}".format(time,row["text"]))
    return ("\n".join(lines)+"\n").encode("utf-8")


def native_line_fallback(lrc,lyrics,duration,*,video=False):
    """Retain valid native line starts, not invalid word clocks."""
    stripped=[]
    for raw in lrc.splitlines():
        match=LINE.fullmatch(raw.strip())
        if not match:
            stripped.append(raw)
            continue
        body=match.group(4)
        tags=list(WORD.finditer(body))
        if not tags:
            stripped.append(raw)
            continue
        if body[:tags[0].start()].strip():
            raise ValueError("Untagged text before enhanced LRC words")
        words=[]
        for index,tag in enumerate(tags):
            word=body[tag.end():tags[index+1].start() if index+1<len(tags) else len(body)].strip()
            if not word or "<" in word or ">" in word:
                raise ValueError("Malformed enhanced LRC text")
            words.append(word)
        stripped.append(raw.strip()[:match.start(4)]+" ".join(words))
    source="\n".join(stripped)
    timing_rows(source,lyrics,duration,library_only=True,video=video)
    return video_line_bytes(source,lyrics,duration,library_only=True).decode("utf-8")


def native_timing_assets(lrc,lyrics,duration,*,video=False):
    try:
        native,srt=timed_text(lrc,lyrics,duration,library_only=True,video=video)
    except ValueError as exc:
        # An independent strict line-only parse must still succeed.
        if str(exc) not in ("Malformed or unordered enhanced LRC word",
                            "LRC line starts are not strictly ordered within source duration",
                            "Invalid seconds in LRC timestamp"):
            raise
        native=native_line_fallback(lrc,lyrics,duration,video=video)
        _,srt=timed_text(native,lyrics,duration,library_only=True,video=video)
        return native,srt,str(exc)
    return native,srt,None


def playlist_bytes(names,extensions=None):
    """Portable relative paths only, in exact exported track order."""
    extensions=extensions or [".flac"]*len(names)
    return ("#EXTM3U\n"+"\n".join(f"{name}/{name}{ext}" for name,ext in zip(names,extensions))+"\n").encode("utf-8")


def verify_export(root,contract):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Unexpected symlink in export package")
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


def launch(repo,release,jobs,url,*,kind="single",title=None,artist="",snapshot=ri.DEFAULT_SNAPSHOT,confirm=False,timing_reader=None,preset="production",native_collection=None,native_songs=None,library_only=False,expected_collection=None):
    if preset not in PRESETS:
        raise ValueError("Unknown export preset")
    cc.validate_job(release,"placeholder","en",195)
    url=configured_endpoint(url)
    selection=None
    if native_songs is not None:
        if jobs or native_collection is not None or not native_songs:
            raise ValueError("Select either native song IDs, a native collection or retained jobs")
        library_only=True
    if library_only and native_songs is None and native_collection is None:
        raise ValueError("Library-only mode requires native song or collection IDs")
    if native_collection is not None:
        if jobs or kind!="single" or title is not None:
            raise ValueError("Native collection supplies its own type, title and order; do not override them")
        selection=nc.collection(url,native_collection)
        if expected_collection is not None and selection!=expected_collection:
            raise ValueError("Native collection changed after acceptance selection")
        kind,title=selection["kind"],selection["name"]
        if library_only:
            native_songs=selection["song_ids"]
        else:
            jobs=nc.retained_jobs(repo,selection)
    if library_only:
        jobs=native_songs
    if (kind not in ri.FOLDERS or not 1<=len(jobs)<=(100 if kind=="playlist" else 24)
            or len(set(jobs))!=len(jobs) or (kind=="single" and len(jobs)!=1)):
        raise ValueError("Select distinct ordered tracks: single 1, EP/album up to 24, playlist up to 100")
    if (title is not None and (not isinstance(title,str) or not title.strip() or len(title)>150)
            or not isinstance(artist,str) or len(artist)>150 or (kind!="single" and not title)):
        raise ValueError("Album/EP requires title; invalid release metadata")
    tracks=[]
    for number,j in enumerate(jobs,1):
        try:
            tracks.append(nl.track(url,j) if library_only else retained(repo,j))
        except (ValueError,MCPError,OSError,TypeError,KeyError) as exc:
            if not library_only:
                raise
            raise ValueError(f"Native track {number} (ID {j}): {exc}") from exc
    if selection is not None and [t["result"].get("song_id") for t in tracks]!=selection["song_ids"]:
        raise ValueError("Retained result does not match native collection order")
    title=title or tracks[0]["brief"]["title"]
    exports=repo/"results/exports"
    original_contract={"schema":"release-export-v1","release":release,"type":kind,"title":title,"artist":artist,
                       "sources":[t["evidence"] for t in tracks],"audio_variant":"original",
                       "timing_policy":PRESETS[preset]}
    if library_only:
        original_contract["source_policy"]="native-library-draft-v1"
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
    print("Tracks:",len(tracks),flush=True)
    for i,track in enumerate(tracks,1):
        print(f"  {i:02d}. "+json.dumps(track["brief"]["title"],ensure_ascii=True),flush=True)
    extensions=[t["audio"].suffix.lower() if library_only else ".flac" for t in tracks]
    names=None if root.exists() else ri.track_names(root,[t["brief"]["title"] for t in tracks],kind,extensions,video=preset=="video",native=library_only)
    if names is not None:
        for name,ext in zip(names,extensions):
            print("  File:",json.dumps(name+ext,ensure_ascii=True),flush=True)
    if not confirm:
        print("Plan only; no package writes or inference." if selection is not None or library_only else "Plan only; no writes or Studio calls.",flush=True)
        return 0
    with ld.lock(exports/".active",context={"root":root.relative_to(repo).as_posix(),"stage":"export","release":release}):
        if destination()!=(root,contract,index,record):
            raise ValueError("Release destination changed during preparation")
        if root.exists():
            manifest=verify_export(root,contract)
            print("Existing export verified:",root,flush=True)
            return 0 if manifest["status"]=="complete" else 2
        names=ri.track_names(root,[t["brief"]["title"] for t in tracks],kind,extensions,video=preset=="video",native=library_only)
        def paths(base):
            return [base/"release.json",*([base/"playlist.m3u8"] if kind=="playlist" else []),*[(base/name if kind!="single" else base)/(name+suffix)
                    for name,ext in zip(names,extensions) for suffix in (ext,".txt",".clean.txt",".lrc",".srt")+((".line.lrc",) if preset=="video" else ())+((".native.lrc",) if library_only else ())]]
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
                target=dest/(name+extensions[i-1])
                shutil.copyfile(t["audio"],target)
                if nd._sha(target)!=t["result"]["audio_sha256"] or nd._sha(t["audio"])!=t["result"]["audio_sha256"]:
                    raise ValueError("Audio changed during export")
                lyrics=t["brief"]["lyrics"]
                tagged=lyric_bytes(t)
                clean=clean_lyric_bytes(t)
                if tagged:
                    (dest/(name+".txt")).write_bytes(tagged)
                if clean:
                    (dest/(name+".clean.txt")).write_bytes(clean)
                timing={"status":"unavailable","acoustic_timing_verified":False}
                if library_only and not clean:
                    timing={"status":"not_applicable","acoustic_timing_verified":False}
                elif preset=="distribution":
                    timing={"status":"not_requested","acoustic_timing_verified":False}
                else:
                    try:
                        lrc=t["native_snapshot"]["lrc"] if library_only else (timing_reader or read_timing)(t,url)
                        if not lrc:
                            raise ValueError("No retained native karaoke LRC")
                        duration=t["report"]["acoustic"]["duration_seconds"]
                        fallback=None
                        if library_only:
                            lrc_out,srt_out,fallback=native_timing_assets(lrc,lyrics,duration,video=preset=="video")
                        else:
                            lrc_out,srt_out=timed_text(lrc,lyrics,duration,video=preset=="video")
                        if preset=="video":
                            line_lrc=video_line_bytes(lrc_out,lyrics,duration,library_only=library_only)
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
                                "lrc_preserved":fallback is None}
                        if fallback is not None:
                            (dest/(name+".native.lrc")).write_bytes(lrc.encode("utf-8"))
                            timing.update(word_timing_status="discarded_invalid_word_anchors",
                                          word_timing_issue=fallback,
                                          native_lrc_preserved_separately=True,
                                          derived_lrc_sha256=nd.digest(lrc_out.encode("utf-8")))
                        if preset=="video":
                            (dest/(name+".line.lrc")).write_bytes(line_lrc)
                            rows=timing_rows(lrc_out,lyrics,duration,library_only=library_only,video=True)
                            timing.update(line_lrc_policy="native-line-onset-only-v1",
                                          lyric_line_count=len(rows),
                                          enhanced_line_count=sum(bool(row["word_anchors"]) for row in rows))
                        if timing_reader is None:
                            timing["source_identity_screen"]="native_library_current_snapshot_v1" if library_only else "matched_retained_audio_and_stable_library_snapshot_v1"
                            timing["karaoke_provenance_verified"]=False
                if nd._sha(t["audio"])!=t["result"]["audio_sha256"]:
                    raise ValueError("Source audio changed during timing export")
                details.append({"track":i,"job":t["job"],"title":t["brief"]["title"],"audio_sha256":t["result"]["audio_sha256"],
                                "source_status":t["result"]["status"],"timing":timing})
                details[-1]["audio_file"]=target.relative_to(stage).as_posix()
                if library_only:
                    details[-1].update(song_id=t["result"]["song_id"],audio_extension=extensions[i-1],clean_lyrics_available=bool(clean))
                print("Track",i,":",timing["status"],flush=True)
            if library_only:
                for track in tracks:
                    nl.verify_current(url,track)
            if selection is not None and nc.collection(url,native_collection)!=selection:
                raise ValueError("Native collection changed during export; preserve previous package")
            if kind=="playlist":
                (stage/"playlist.m3u8").write_bytes(playlist_bytes(names,extensions))
            files={p.relative_to(stage).as_posix():nd._sha(p) for p in stage.rglob("*") if p.is_file()}
            manifest={"contract":contract,"tracks":details,"files":files,
                      "lyric_assets":CLEAN_LYRIC_POLICY,
                      "status":"complete" if all(t["timing"]["status"] in ("exported_unverified_display_anchors","not_requested","not_applicable") for t in details) else "partial_missing_timing",
                      "release_approved":False,"studio_mutations":0,"inference_calls":0}
            nd.atomic_write(stage/"release.json",manifest)
            verify_export(stage,contract)
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
    p.add_argument("--list-songs",action="store_true",help="List playable native song IDs and titles")
    p.add_argument("--native-song",action="append",help="Select current native song ID, repeat for ordered tracks")
    p.add_argument("--song-name",action="append",help="Select an unambiguous exact native title, repeat for ordered tracks")
    p.add_argument("--collection-name",help="Select an unambiguous exact native album or playlist name (draft source)")
    p.add_argument("--check-library",action="store_true",help="Consolidated native library acceptance; preview or confirmed sample exports")
    p.add_argument("--collections-only",action="store_true",help="With --check-library, retest native album and playlist only")
    p.add_argument("--collection-kind",choices=("album","playlist"),help="Limit collection-only check to one kind")
    p.add_argument("--library-only",action="store_true",help="Export current native collection as draft, without Director receipts")
    p.add_argument("--song",action="append")
    p.add_argument("--type",choices=tuple(ri.FOLDERS),default="single")
    p.add_argument("--title")
    p.add_argument("--artist",default="")
    p.add_argument("--preset",choices=sorted(PRESETS),default="production",help="production: all existing timed assets; distribution: audio and lyric texts; video: production plus simple line LRC")
    p.add_argument("--snapshot",default=ri.DEFAULT_SNAPSHOT,help="Explicit immutable revision of existing v1 release")
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        if a.check_library:
            if (a.export or a.list_collections or a.list_songs or a.song or a.native_collection or a.native_song
                    or a.song_name or a.collection_name or a.library_only or a.title or a.artist
                    or a.type!="single" or a.snapshot!=ri.DEFAULT_SNAPSHOT or a.preset!="production"):
                raise ValueError("Use --export --check-library [--confirm-run] alone")
            from .export_acceptance import run
            if a.collection_kind and not a.collections_only:
                raise ValueError("--collection-kind requires --collections-only")
            return run(a.repo.resolve(),a.url,confirm=a.confirm_run,launch=launch,collections_only=a.collections_only,collection_kind=a.collection_kind)
        if a.collections_only or a.collection_kind:
            raise ValueError("--collections-only requires --check-library")
        if a.list_collections or a.list_songs:
            if (a.list_collections and a.list_songs or a.export or a.song or a.native_collection or a.native_song or a.song_name or a.collection_name or a.library_only or a.confirm_run or a.title or a.artist or a.type!="single" or a.snapshot!=ri.DEFAULT_SNAPSHOT or a.preset!="production"):
                raise ValueError("Use --export with exactly one list option alone")
            print(json.dumps(nc.collections(a.url) if a.list_collections else nl.song_list(a.url),ensure_ascii=False,indent=2))
            return 0
        if not a.export:
            raise ValueError("Export release ID required")
        if a.song_name:
            if a.song or a.native_song or a.native_collection or a.collection_name is not None:
                raise ValueError("Choose one native song/collection selection method")
            rows=nl.song_list(a.url)
            a.native_song=[by_name(rows,name,"title") for name in a.song_name]
        if a.collection_name is not None:
            if a.song or a.native_song or a.native_collection:
                raise ValueError("Choose one native song/collection selection method")
            a.native_collection=by_name(nc.collections(a.url),a.collection_name,"name")
            a.library_only=True
        return launch(a.repo.resolve(),a.export,a.song or ([] if a.native_collection or a.native_song else [a.export]),a.url,kind=a.type,title=a.title,artist=a.artist,snapshot=a.snapshot,confirm=a.confirm_run,preset=a.preset,native_collection=a.native_collection,native_songs=a.native_song,library_only=a.library_only)
    except (OSError,ValueError,KeyError,TypeError,MCPError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
