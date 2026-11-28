"""Read-only native YuE2 playlist/album selection, no collection writes."""
import json
from urllib.parse import quote

from . import native_draft as nd
from .temporal_evidence import native_library_read

ALBUM_PREFIX="[YuE2-Studio:album:v1]\n"
COLLECTION_PREFIX="[YuE2-Studio:collection:v2]\n"


def parse_collection(raw):
    if not isinstance(raw,dict):
        raise ValueError("Invalid native collection")
    ident,name,ids=raw.get("id"),raw.get("name"),raw.get("song_ids")
    if (not isinstance(ident,str) or not ident.strip() or len(ident)>150
            or not isinstance(name,str) or not name.strip() or len(name)>150
            or not isinstance(ids,list) or any(not isinstance(x,str) or not x.strip() or len(x)>150 for x in ids)):
        raise ValueError("Invalid native collection identity or membership")
    description=raw.get("description")
    if description is None:
        description=""
    if not isinstance(description,str):
        raise ValueError("Invalid collection description")
    kind="playlist"
    if description.startswith(ALBUM_PREFIX):
        kind="album"
    elif description.startswith(COLLECTION_PREFIX):
        envelope=json.loads(description[len(COLLECTION_PREFIX):])
        if not isinstance(envelope,dict) or envelope.get("kind") not in ("album","playlist"):
            raise ValueError("Unrecognized native collection envelope")
        kind=envelope["kind"]
    return {"id":ident,"name":name,"kind":kind,"song_ids":ids}


def collections(url):
    raw=native_library_read(url,"/v1/library/playlists")
    if not isinstance(raw,list) or len(raw)>10000:
        raise ValueError("Invalid native collection list")
    result=[parse_collection(x) for x in raw]
    if len({x["id"] for x in result})!=len(result):
        raise ValueError("Duplicate native collection identity")
    return [{"id":x["id"],"name":x["name"],"kind":x["kind"],"tracks":len(x["song_ids"])} for x in result]


def collection(url,ident):
    if not isinstance(ident,str) or not ident.strip() or len(ident)>150 or ident in (".",".."):
        raise ValueError("Select exact native collection ID")
    result=parse_collection(native_library_read(url,"/v1/library/playlists/"+quote(ident,safe="")))
    if result["id"]!=ident:
        raise ValueError("Native collection identity differs")
    ids=result["song_ids"]
    cap=100 if result["kind"]=="playlist" else 24
    if not 1<=len(ids)<=cap or len(set(ids))!=len(ids):
        raise ValueError("Collection requires distinct ordered songs within export track limit")
    return result


def retained_jobs(repo,selection):
    """Match native song IDs to exactly one completed local result; full
    retained-source validation is performed by the exporter afterwards."""
    index={song:[] for song in selection["song_ids"]}
    root=repo/"results/autonomous"
    if root.is_dir():
        for parent in sorted(root.iterdir()):
            if not parent.is_dir() or parent.is_symlink():
                continue
            for job in (parent,parent/"continuation-1"):
                path=job/"result.json"
                if path.is_file() and not job.is_symlink():
                    try:
                        if path.stat().st_size>2_000_000:
                            continue
                        result=nd.read(path)
                        song=result.get("song_id") if isinstance(result,dict) else None
                        if isinstance(song,str) and song in index:
                            index[song].append(parent.name)
                    except (OSError,ValueError,TypeError):
                        continue
    if any(len(v)!=1 for v in index.values()):
        raise ValueError("Each native collection song needs exactly one completed Director result; Studio-only or ambiguous songs are not supported yet")
    return [index[song][0] for song in selection["song_ids"]]
