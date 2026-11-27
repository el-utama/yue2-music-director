"""Validate an explicitly supplied local cover image; no generation or network.

The local delivery profile is square 3000px, opaque 8-bit JPEG/PNG. This
does not certify artwork quality, embedded color profile or copyright.
"""
import json
from pathlib import Path
import shutil
import struct
import zlib

from . import acoustic as ac, native_draft as nd

PIXELS=3000
MAX_BYTES=25*1024*1024
FORMATS={".jpg":("mjpeg","mjpeg","jpg"),".jpeg":("mjpeg","mjpeg","jpg"),
         ".png":("png_pipe","png","png")}


def _png_chunks(path):
    # Reject APNG, transparency, corrupt/trailing chunks even when a decoder
    # would otherwise silently display only the first frame.
    with path.open("rb") as stream:
        stream.read(8)
        remaining=path.stat().st_size-8
        first=True
        while remaining>=12:
            length,kind=struct.unpack(">I4s",stream.read(8))
            if length>remaining-12:
                raise ValueError("Invalid PNG chunk length")
            if first and (kind!=b"IHDR" or length!=13):
                raise ValueError("Invalid PNG header")
            first=False
            if kind in (b"acTL",b"fcTL",b"fdAT",b"tRNS"):
                raise ValueError("Animated or transparent PNG not supported")
            data=stream.read(length)
            crc=struct.unpack(">I",stream.read(4))[0]
            if zlib.crc32(kind+data)!=crc:
                raise ValueError("Invalid PNG chunk checksum")
            remaining-=12+length
            if kind==b"IEND":
                if length or remaining:
                    raise ValueError("Unexpected PNG trailing data")
                return
    raise ValueError("Incomplete PNG")


def inspect(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in FORMATS:
        raise ValueError("Supply a local JPEG or PNG cover")
    if not 0<path.stat().st_size<=MAX_BYTES:
        raise ValueError("Cover exceeds local file-size profile")
    path=path.resolve(strict=True)
    fmt,codec,ext=FORMATS[path.suffix.lower()]
    with path.open("rb") as stream:
        magic=stream.read(8)
    if (codec=="png" and magic!=b"\x89PNG\r\n\x1a\n"
            or codec=="mjpeg" and not magic.startswith(b"\xff\xd8\xff")):
        raise ValueError("Cover extension differs from image signature")
    if codec=="png":
        _png_chunks(path)
    ffmpeg,ffprobe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise ValueError("FFmpeg and ffprobe required for artwork validation")
    sha=nd._sha(path)
    options=["-f",fmt,"-protocol_whitelist","file"]
    result=ac._run([ffprobe,"-v","error",*options,"-show_entries",
                    "stream=codec_name,codec_type,width,height,pix_fmt","-of","json",str(path)],30)
    streams=json.loads(result.stdout).get("streams",[])
    if result.stderr.strip() or len(streams)!=1:
        raise ValueError("Cover must contain one readable image")
    s=streams[0]
    allowed={"rgb24"} if codec=="png" else {"yuvj420p","yuvj422p","yuvj444p","yuv420p","yuv422p","yuv444p"}
    if (s.get("codec_name")!=codec or s.get("codec_type")!="video"
            or s.get("width")!=PIXELS or s.get("height")!=PIXELS or s.get("pix_fmt") not in allowed):
        raise ValueError("Cover must be 3000 x 3000, opaque 8-bit RGB JPEG/PNG")
    # Require exactly one successfully decoded frame, not just header dimensions.
    frames=ac._run([ffprobe,"-v","error",*options,"-count_frames","-show_entries",
                    "stream=nb_read_frames","-of","json",str(path)],60)
    if frames.stderr.strip() or json.loads(frames.stdout).get("streams")!=[{"nb_read_frames":"1"}]:
        raise ValueError("Cover decode failed or contains multiple frames")
    ac._run([ffmpeg,"-nostdin","-v","error","-xerror",*options,"-i",str(path),
             "-map","0:v:0","-f","null","-"],60)
    if nd._sha(path)!=sha:
        raise ValueError("Cover changed during validation")
    return {"schema":"cover-import-v1","file":"cover."+ext,"sha256":sha,
            "codec":codec,"width":PIXELS,"height":PIXELS,"pixel_format":s["pix_fmt"],
            "size_bytes":path.stat().st_size,"profile":"local-3000-square-opaque-v1",
            "rights_review":"operator_required","color_profile_verified":False}
