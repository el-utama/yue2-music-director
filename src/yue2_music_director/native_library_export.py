"""Draft-only read-only export of current native library audio and written text.

No autonomous receipt, evaluation, acceptance or generation is inferred.
"""
import json
import math
from pathlib import Path
import shutil

from . import native_draft as nd
from .acoustic import _run
from .mcp import Client, configured_endpoint, unpack
from .native_process import _source_file
from .temporal_evidence import native_library_read, native_song_read, karaoke_metadata

FORMATS={".flac":"flac",".wav":"wav",".mp3":"mp3",".ogg":"ogg",".oga":"ogg",
         ".aac":"aac",".m4a":"mov",".mp4":"mov"}
CODECS={".flac":("flac",),".mp3":("mp3",),".ogg":("vorbis","opus","flac"),
        ".oga":("vorbis","opus","flac"),".aac":("aac",),".m4a":("aac",),".mp4":("aac",)}


def song_list(url):
    data=native_library_read(url,"/v1/library/songs")
    if not isinstance(data,list) or len(data)>10000:
        raise ValueError("Invalid native song list")
    rows=[]
    for song in data:
        if not isinstance(song,dict) or not isinstance(song.get("id"),str) or not isinstance(song.get("title"),str):
            raise ValueError("Invalid native library song")
        if song.get("audio_path"):
            rows.append({"id":song["id"],"title":song["title"]})
    if len({r["id"] for r in rows})!=len(rows):
        raise ValueError("Duplicate native song identity")
    return rows


def read_song(url,song_id):
    if not isinstance(song_id,str) or not song_id.strip() or len(song_id)>150 or song_id in (".",".."):
        raise ValueError("Invalid native song ID")
    song=native_song_read(url,song_id)
    if not isinstance(song,dict) or song.get("id")!=song_id:
        raise ValueError("Native song identity differs")
    title,lyrics=song.get("title"),song.get("lyrics")
    if not isinstance(title,str) or not title.strip() or len(title)>150:
        raise ValueError("Invalid native title")
    if lyrics is None:
        lyrics=""
    if not isinstance(lyrics,str) or len(lyrics)>512000:
        raise ValueError("Invalid native lyrics")
    lrc=karaoke_metadata(song,song_id,detailed=True)
    if lrc is not None and not isinstance(lrc,str):
        raise ValueError("Invalid native LRC")
    meta=song.get("metadata") or {}
    return {"id":song_id,"title":title,"lyrics":lyrics,"lrc":lrc,
            "active_version":meta.get("active_version"),"updated_at":song.get("updated_at"),
            "audio_path":song.get("audio_path")}


def file_for(client,song_id):
    files=unpack(client.call("library_song_files",{"song_id":song_id}))
    if not isinstance(files,dict):
        raise ValueError("Invalid native library files")
    raw=files.get("audio",files.get("audio_path"))
    if isinstance(raw,dict):
        raw=raw.get("path")
    if not isinstance(raw,str) or not raw.strip():
        raise ValueError("Native song has no resolved audio file; check playback in Studio")
    path=Path(raw)
    if not path.is_absolute():
        raise ValueError("Native audio path is not absolute; check Studio storage configuration")
    if not path.is_file():
        raise ValueError("Native audio file missing or inaccessible; check Studio storage and playback")
    if path.suffix.lower() not in FORMATS:
        raise ValueError("Unsupported native audio extension: "+repr(path.suffix.lower())+"; use Studio export to a supported format")
    path=path.resolve(strict=True)
    _source_file(files,path)
    return path


def duration(path):
    ffprobe=shutil.which("ffprobe")
    if not ffprobe:
        raise ValueError("ffprobe required for native draft export")
    output=_run([ffprobe,"-v","error","-f",FORMATS[path.suffix.lower()],
                 "-protocol_whitelist","file","-select_streams","a",
                 "-show_entries","stream=duration,codec_name:format=duration",
                 "-of","json",str(path)],30)
    data=json.loads(output.stdout)
    streams=data.get("streams",[])
    if len(streams)!=1:
        raise ValueError("Expected exactly one audio stream")
    codec=streams[0].get("codec_name","")
    ext=path.suffix.lower()
    if (ext==".wav" and not codec.startswith("pcm_") or
            ext!=".wav" and codec not in CODECS.get(ext,())):
        raise ValueError("Native audio format differs from supported file extension")
    raw=streams[0].get("duration")
    if raw in (None,"","N/A"):
        raw=data.get("format",{}).get("duration")
    try:
        seconds=float(raw)
    except (ValueError,TypeError):
        raise ValueError("Missing measurable native audio duration") from None
    if not math.isfinite(seconds) or not 0<seconds<=1800:
        raise ValueError("Invalid native audio duration")
    return seconds


def track(url,song_id):
    client=Client(configured_endpoint(url),timeout=30).connect()
    before=read_song(url,song_id)
    audio=file_for(client,song_id)
    sha=nd._sha(audio)
    seconds=duration(audio)
    if (read_song(url,song_id)!=before or file_for(client,song_id)!=audio or nd._sha(audio)!=sha):
        raise ValueError("Native library audio or metadata changed during read")
    evidence={"source":"native-library-draft-v1","song_id":song_id,
              "audio_sha256":sha,"title":before["title"],
              "lyrics_sha256":nd.digest(before["lyrics"].encode("utf-8")),
              "audio_extension":audio.suffix.lower(),"duration_seconds":seconds}
    return {"job":None,"brief":{"title":before["title"],"lyrics":before["lyrics"]},
            "audio":audio,"report":{"acoustic":{"duration_seconds":seconds}},
            "result":{"song_id":song_id,"audio_sha256":sha,"status":"native_library_unreviewed"},
            "evidence":evidence,"native_snapshot":before}


def verify_current(url,track):
    client=Client(configured_endpoint(url),timeout=30).connect()
    if (read_song(url,track["result"]["song_id"])!=track["native_snapshot"]
            or file_for(client,track["result"]["song_id"])!=track["audio"]
            or nd._sha(track["audio"])!=track["result"]["audio_sha256"]):
        raise ValueError("Native song changed during export")
