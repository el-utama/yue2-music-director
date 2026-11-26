"""Independent release packaging. No synthesis, recognition, or publishing."""
import argparse
import math
import re
import shutil
import sys
import tempfile
from pathlib import Path

from . import native_draft as nd, creative_core as cc, cover_art, listening_director as ld
from .mcp import MCPError, configured_endpoint
from .temporal_evidence import native_song_read, karaoke_metadata, parse_lrc
from .prosody import parse_lyrics


def safe_title(title):
    # Bounded portable path; release/job IDs disambiguate identical titles.
    stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]',"_",title).strip(" .")
    return stem[:64].rstrip(" .") or "Untitled"


def retained(repo,job):
    _,evidence=cover_art.track(repo,job)
    parent=repo/"results/autonomous"/job
    root=parent if (parent/"result.json").is_file() else parent/"continuation-1"
    result=nd.read(root/"result.json")
    brief=nd.load_brief(root/"brief.json")
    draft=root/"production/draft"
    report=nd.read(draft/"report.json")
    row=ld.verify_take(draft,brief,report)
    audio=Path(row["audio"])
    if result.get("audio")!=str(audio) or result["audio_sha256"]!=row["audio_sha256"]:
        raise ValueError("Export audio identity differs")
    return {"job":job,"brief":brief,"report":report,"result":result,"audio":audio,
            "evidence":evidence}


def stamp(ms,*,srt=False):
    minutes,rest=divmod(ms,60000)
    second,milli=divmod(rest,1000)
    if srt:
        hour,minute=divmod(minutes,60)
        return f"{hour:02}:{minute:02}:{second:02},{milli:03}"
    return f"{minutes:02}:{second:02}.{milli:03}"


def timed_text(lrc,lyrics,duration):
    rows=parse_lrc(lrc,duration)
    expected=[line for group in parse_lyrics(lyrics) for line in group["lines"]]
    if [" ".join(r["text"].split()) for r in rows]!=[" ".join(x.split()) for x in expected]:
        raise ValueError("Native LRC does not cover the exact lyric lines in order")
    starts=[round(r["start_seconds"]*1000) for r in rows]
    limit=math.floor(duration*1000)
    if any(a>=b for a,b in zip(starts,starts[1:]+[limit])):
        raise ValueError("Timestamp precision collapses display interval")
    lrc_out="".join(f"[{stamp(start)}]{line}\n" for start,line in zip(starts,expected))
    srt_out="\n".join(f"{i+1}\n{stamp(start,srt=True)} --> {stamp(end,srt=True)}\n{line}\n"
                      for i,(start,end,line) in enumerate(zip(starts,starts[1:]+[limit],expected)))
    return lrc_out,srt_out


def read_timing(track,url):
    report=track["report"]
    song=native_song_read(url,report["song_id"])
    if (not isinstance(song,dict) or song.get("id")!=report["song_id"]
            or not isinstance(song.get("metadata"),dict)
            or song["metadata"].get("job_id")!=report["job_id"]):
        raise ValueError("Native timing song/job identity differs")
    settings=song.get("generation_settings")
    if not isinstance(settings,dict) or settings.get("lyrics")!=track["brief"]["lyrics"]:
        raise ValueError("Native timing lyric identity differs")
    return karaoke_metadata(song,report["song_id"],detailed=True)


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


def launch(repo,release,jobs,url,*,kind="single",title=None,artist="",confirm=False,timing_reader=None):
    cc.validate_job(release,"placeholder","en",195)
    if (kind not in ("single","album","ep") or not 1<=len(jobs)<=24
            or len(set(jobs))!=len(jobs) or (kind=="single" and len(jobs)!=1)):
        raise ValueError("Select single, album or EP with 1–24 distinct ordered tracks")
    if (title is not None and (not isinstance(title,str) or not title.strip() or len(title)>150)
            or not isinstance(artist,str) or len(artist)>150 or (kind!="single" and not title)):
        raise ValueError("Album/EP requires title; invalid release metadata")
    url=configured_endpoint(url)
    tracks=[retained(repo,j) for j in jobs]
    title=title or tracks[0]["brief"]["title"]
    folder={"single":"songs","album":"albums","ep":"eps"}[kind]
    base=repo/"results/exports"/folder
    root=base/(safe_title(title)+"--"+release)
    contract={"schema":"release-export-v1","release":release,"type":kind,"title":title,"artist":artist,
              "sources":[t["evidence"] for t in tracks],"audio_variant":"original",
              "timing_policy":"native-display-anchors-v1"}
    print("Export folder:",root,flush=True)
    if not confirm:
        print("Plan only; no writes or Studio calls.",flush=True)
        return 0
    with ld.lock(repo/"results/exports/.active"):
        if root.exists():
            manifest=verify_export(root,contract)
            print("Existing export verified:",root,flush=True)
            return 0 if manifest["status"]=="complete" else 2
        base.mkdir(parents=True,exist_ok=True)
        stage=Path(tempfile.mkdtemp(prefix=".export-",dir=base))
        try:
            details=[]
            for i,t in enumerate(tracks,1):
                name=f"{i:02d} - {safe_title(t['brief']['title'])}" if kind!="single" else safe_title(t["brief"]["title"])
                dest=stage/name if kind!="single" else stage
                dest.mkdir(exist_ok=True)
                target=dest/(name+".flac")
                shutil.copyfile(t["audio"],target)
                if nd._sha(target)!=t["result"]["audio_sha256"] or nd._sha(t["audio"])!=t["result"]["audio_sha256"]:
                    raise ValueError("Audio changed during export")
                lyrics=t["brief"]["lyrics"]
                (dest/(name+".txt")).write_bytes((lyrics.rstrip()+"\n").encode("utf-8"))
                timing={"status":"unavailable","acoustic_timing_verified":False}
                try:
                    lrc=(timing_reader or read_timing)(t,url)
                    if not lrc:
                        raise ValueError("No retained native karaoke LRC")
                    lrc_out,srt_out=timed_text(lrc,lyrics,t["report"]["acoustic"]["duration_seconds"])
                    (dest/(name+".lrc")).write_bytes(lrc_out.encode("utf-8"))
                    (dest/(name+".srt")).write_bytes(srt_out.encode("utf-8"))
                    timing={"status":"exported_unverified_display_anchors","acoustic_timing_verified":False,
                            "source_lrc_sha256":nd.digest(lrc.encode("utf-8")),
                            "srt_end_policy":"next line onset; final line ends at measured recording duration"}
                except (ValueError,MCPError) as exc:
                    timing["reason"]=str(exc)
                details.append({"track":i,"job":t["job"],"title":t["brief"]["title"],"audio_sha256":t["result"]["audio_sha256"],
                                "source_status":t["result"]["status"],"timing":timing})
                print("Track",i,":",timing["status"],flush=True)
            files={p.relative_to(stage).as_posix():nd._sha(p) for p in stage.rglob("*") if p.is_file()}
            manifest={"contract":contract,"tracks":details,"files":files,
                      "status":"complete" if all(t["timing"]["status"]=="exported_unverified_display_anchors" for t in details) else "partial_missing_timing",
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
    p.add_argument("--export",required=True,metavar="RELEASE")
    p.add_argument("--song",action="append")
    p.add_argument("--type",choices=("single","album","ep"),default="single")
    p.add_argument("--title")
    p.add_argument("--artist",default="")
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        return launch(a.repo.resolve(),a.export,a.song or [a.export],a.url,kind=a.type,title=a.title,artist=a.artist,confirm=a.confirm_run)
    except (OSError,ValueError,KeyError,TypeError,MCPError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
