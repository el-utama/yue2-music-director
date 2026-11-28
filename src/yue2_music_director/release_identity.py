"""Stable release identities and portable immutable package destinations."""
import os
from pathlib import Path
import re
import unicodedata

from . import native_draft as nd, creative_core as cc

FOLDERS={"single":"songs","album":"albums","ep":"eps","playlist":"playlists"}
DEFAULT_SNAPSHOT="v1"
RESERVED=re.compile(r"^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$",re.I)


def safe_title(title,limit=56):
    stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]',"_",unicodedata.normalize("NFC",title)).strip(" .")
    if RESERVED.fullmatch(stem.split(".")[0].rstrip(" ")):
        stem="_"+stem
    # Bound both byte-length (Unix) and UTF-16 code units (Windows).
    while len(stem.encode("utf-8"))>limit or len(stem.encode("utf-16-le"))//2>limit:
        stem=stem[:-1]
    stem=stem.rstrip(" .") or "Untitled"
    if RESERVED.fullmatch(stem.split(".")[0].rstrip(" ")):
        stem="_"+stem
    return stem


def ensure_paths(paths,*,windows=None):
    if windows is None:
        windows=os.name=="nt"
    for path in paths:
        path=Path(path)
        if any(len(part.encode("utf-8"))>255 for part in path.parts):
            raise ValueError("Release filename exceeds portable component length")
        if windows and len(str(path.absolute()).encode("utf-16-le"))//2>240:
            raise ValueError("Release path exceeds conservative Windows length; use shorter IDs or repo path")


def track_names(root,titles,kind,extensions,*,video=False,native=False,windows=None):
    """Keep existing short names; shorten new long paths before any writes.

    Budget for both final and temporary staging paths. Track numbers keep
    collection filenames distinct even after shortening.
    """
    width=max(2,len(str(len(titles))))
    if native and kind in ("album","ep") and len(titles)>1:
        numbered=[re.fullmatch(r"\s*(\d{1,3})\.\s+(.+)",title) for title in titles]
        if all(match and int(match.group(1))==number for number,match in enumerate(numbered,1)):
            titles=[match.group(2) for match in numbered]
    names=[]
    for number,(title,ext) in enumerate(zip(titles,extensions),1):
        prefix=f"{number:0{width}d} - " if kind!="single" else ""
        suffixes=(ext,".txt",".clean.txt",".lrc",".srt")+((".line.lrc",) if video else ())+((".native.lrc",) if native else ())
        for limit in range(56,7,-1):
            name=prefix+safe_title(title,limit)
            candidates=[(base/name if kind!="single" else base)/(name+suffix)
                        for base in (root,root.parent/".export-00000000") for suffix in suffixes]
            try:
                ensure_paths(candidates,windows=windows)
            except ValueError:
                continue
            names.append(name)
            break
        else:
            raise ValueError("Export path too long even with shortened title; use a shorter release ID or repo path")
    return names


def _originals(exports,release):
    found=[]
    for folder in FOLDERS.values():
        base=exports/folder
        if not base.is_dir():
            continue
        for root in base.iterdir():
            if root.name.startswith(".export-") or not root.is_dir():
                continue
            suffix=root.name.casefold().endswith("--"+release.casefold())
            manifest=root/"release.json"
            if not manifest.is_file():
                if suffix:
                    raise ValueError("Existing release destination has no manifest; preserve evidence")
                continue
            try:
                if manifest.stat().st_size>2_000_000:
                    raise ValueError("Oversized manifest")
                contract=nd.read(manifest)["contract"]
                existing=contract["release"]
                if not isinstance(existing,str):
                    raise ValueError("Invalid release ID")
            except (OSError,ValueError,TypeError,KeyError):
                if suffix:
                    raise ValueError("Existing release manifest is unreadable; preserve evidence") from None
                continue
            if existing.casefold()==release.casefold():
                if root.is_symlink() or not suffix or existing!=release:
                    raise ValueError("Existing release ID or path differs (including case)")
                found.append(root)
    if len(found)>1:
        raise ValueError("Multiple packages share this release ID; preserve all evidence")
    return found[0] if found else None


def _safe_relative(exports,relative,release,kind):
    if not isinstance(relative,str):
        raise ValueError("Invalid indexed release path")
    parts=relative.split("/")
    if (len(parts)!=2 or parts[0]!=FOLDERS[kind] or parts[1] in ("",".","..")
            or "\\" in relative or ":" in relative
            or not parts[1].casefold().endswith("--"+release.casefold())):
        raise ValueError("Indexed release path differs")
    root=exports.joinpath(*parts)
    if root.is_symlink() or root.parent.is_symlink():
        raise ValueError("Unexpected symlink in release destination")
    return root


def original(exports,contract):
    """Locate legacy packages without modifying them; new IDs get a reservation."""
    release,kind=contract["release"],contract["type"]
    cc.validate_job(release,"placeholder","en",195)
    index=exports/".release-index"/release.casefold()/"identity.json"
    found=_originals(exports,release)
    if index.exists():
        record=nd.read(index)
        if (record.get("schema")!="release-identity-v1" or record.get("contract")!=contract):
            raise ValueError("Release ID already reserved for different metadata, type, or ordered sources")
        root=_safe_relative(exports,record.get("original_relative"),release,kind)
        if found is not None and found!=root:
            raise ValueError("Indexed and discovered release paths differ")
    else:
        root=found or exports/FOLDERS[kind]/(safe_title(contract["title"])+"--"+release)
        relative=root.relative_to(exports).as_posix()
        root=_safe_relative(exports,relative,release,kind)
        record={"schema":"release-identity-v1","contract":contract,"original_relative":relative}
    if root.exists():
        manifest=nd.read(root/"release.json")
        if manifest.get("contract")!=contract:
            raise ValueError("Release ID already belongs to a different immutable contract")
    return root,index,record


def reserve(index,record):
    if index.exists():
        if nd.read(index)!=record:
            raise ValueError("Release identity reservation differs")
        return
    if index.is_symlink() or index.parent.is_symlink():
        raise ValueError("Unexpected release registry symlink")
    index.parent.mkdir(parents=True,exist_ok=True)
    nd.create_journal(index,record)


def revision(exports,contract,original_root,snapshot):
    cc.validate_job(snapshot,"placeholder","en",195)
    if snapshot.casefold()==DEFAULT_SNAPSHOT:
        if snapshot!=DEFAULT_SNAPSHOT:
            raise ValueError("Use exact default snapshot ID v1")
        return original_root,contract
    if not (original_root/"release.json").is_file():
        raise ValueError("An explicit revision requires the completed v1 package (partial timing is allowed)")
    root=exports/"revisions"/contract["release"].casefold()/snapshot.casefold()
    if any(p.is_symlink() for p in (root,root.parent,root.parent.parent)):
        raise ValueError("Unexpected revision destination symlink")
    return root,{**contract,"snapshot":snapshot,"base_snapshot":"v1",
                 "base_release_manifest_sha256":nd._sha(original_root/"release.json")}
