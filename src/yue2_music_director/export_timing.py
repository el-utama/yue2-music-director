"""Read-only timing snapshot for an exact retained audio source.

This checks observable library identity and metadata stability, not acoustic
alignment or the provenance of imported/edited karaoke.
"""
from http.client import HTTPException
from pathlib import Path

from . import native_draft as nd
from .mcp import Client, MCPError, configured_endpoint, unpack
from .native_process import _source_file
from .temporal_evidence import native_song_read, karaoke_metadata


def _snapshot(url, song_id, job_id, lyrics):
    song=native_song_read(url,song_id)
    if (not isinstance(song,dict) or song.get("id")!=song_id
            or not isinstance(song.get("metadata"),dict)
            or song["metadata"].get("job_id")!=job_id):
        raise ValueError("Native timing song/job identity differs")
    settings=song.get("generation_settings")
    if not isinstance(settings,dict) or settings.get("lyrics")!=lyrics:
        raise ValueError("Native timing lyric identity differs")
    lrc=karaoke_metadata(song,song_id,detailed=True)
    if lrc is not None and not isinstance(lrc,str):
        raise ValueError("Invalid native LRC type")
    return song,lrc


def read_timing(track,url):
    """Return unchanged LRC only after source and snapshot checks succeed."""
    try:
        report=track["report"]
        song_id,job_id=report["song_id"],report["job_id"]
        if not all(isinstance(x,str) and x.strip() for x in (song_id,job_id)):
            raise ValueError("Missing retained song/job identity")
        source=Path(track["audio"]).resolve(strict=True)
        expected=track["result"]["audio_sha256"]
        if nd._sha(source)!=expected:
            raise ValueError("Retained source audio hash differs")
        url=configured_endpoint(url)
        client=Client(url,timeout=30).connect()
        _source_file(unpack(client.call("library_song_files",{"song_id":song_id})),source)
        before,lrc=_snapshot(url,song_id,job_id,track["brief"]["lyrics"])
        after,_=_snapshot(url,song_id,job_id,track["brief"]["lyrics"])
        _source_file(unpack(client.call("library_song_files",{"song_id":song_id})),source)
        if before!=after:
            raise ValueError("Native timing metadata changed during read")
        if nd._sha(source)!=expected:
            raise ValueError("Retained source audio changed during timing read")
        return lrc
    except (MCPError,OSError,HTTPException,KeyError,TypeError,AttributeError) as exc:
        # Transport/schema failures at this read-only boundary are timing
        # unavailability, never a request to regenerate or edit metadata.
        raise ValueError("Native timing read unavailable: "+type(exc).__name__) from None
