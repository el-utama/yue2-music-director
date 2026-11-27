"""Private, explicit artist profiles and immutable typed-spec compilation.

No provider, Studio, inference or automatic learning. Only explicitly
supplied typed defaults can enter a compiled creative specification.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from . import typed_creative as tc
from .creative_provider import strict_json
from .native_draft import create_journal
from .operation_lock import now

PROFILE="artist-profile-v1"
FIELDS={"opening","vocal","narrator","style","score_constraints"}
RESERVED={"con","prn","aux","nul",*(f"com{i}" for i in range(1,10)),*(f"lpt{i}" for i in range(1,10))}
LIMIT=100000


def artist_id(value):
    if (not isinstance(value,str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}",value)
            or value in RESERVED):
        raise ValueError("Artist ID must be a portable lowercase ID")
    return value


def _under(repo,*parts):
    root=Path(repo).resolve()
    path=root.joinpath(*parts)
    # No following symlinks/junctions outside the private repository.
    if path.resolve()!=path or any(p.is_symlink() for p in [path,*path.parents] if p!=root and root in p.parents):
        raise ValueError("Unexpected linked artist-memory path")
    return path


def _read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>LIMIT:
        raise ValueError("Invalid or oversized artist-memory JSON")
    raw=path.read_bytes()
    if len(raw)>LIMIT:
        raise ValueError("Oversized artist-memory JSON")
    return strict_json(raw.decode("utf-8-sig")),hashlib.sha256(raw).hexdigest()


def _notes(value):
    return (isinstance(value,list) and len(value)<=30 and
            all(isinstance(x,str) and x.strip() and len(x)<=500 for x in value))


def validate(value):
    if (not isinstance(value,dict) or set(value)!={"schema","defaults","confirmed_preferences",
            "inferred_observations","provenance"} or value["schema"]!=PROFILE):
        raise ValueError("Invalid artist profile fields")
    defaults=value["defaults"]
    if (not isinstance(defaults,dict) or not set(defaults)<=FIELDS
            or not isinstance(defaults.get("score_constraints",{}),dict)
            or not set(defaults.get("score_constraints",{}))<={"key","tempo_bpm"}):
        raise ValueError("Profile defaults must be reusable typed requirements, not song lyrics or sections")
    if (not _notes(value["confirmed_preferences"]) or not _notes(value["inferred_observations"])
            or not isinstance(value["provenance"],str) or not value["provenance"].strip()
            or len(value["provenance"])>1000):
        raise ValueError("Provide bounded preference notes and operator provenance")
    tc.validate_spec({"schema":tc.SPEC_SCHEMA,**defaults})
    return deepcopy(value)


def history(repo,artist):
    directory=_under(repo,"local","artist-memory",artist_id(artist))
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise ValueError("Invalid profile directory")
    records=[]
    previous=None
    for index,path in enumerate(sorted(directory.iterdir()),1):
        if path.name!=f"{index:06d}.json":
            raise ValueError("Unexpected profile ledger entry; retain evidence")
        record,sha=_read(path)
        if (not isinstance(record,dict) or set(record)!={"schema","artist","revision","previous_sha256",
                "recorded_utc","recorded_by","profile"} or record["schema"]!="artist-memory-revision-v1"
                or record["artist"]!=artist or type(record["revision"]) is not int or record["revision"]!=index
                or record["previous_sha256"]!=previous or record["recorded_by"]!="human_operator"
                or not isinstance(record["recorded_utc"],str)):
            raise ValueError("Artist profile lineage differs")
        validate(record["profile"])
        records.append({"record":record,"sha256":sha})
        previous=sha
    return records


def save(repo,artist,value,expected_revision,*,confirm=False):
    profile=validate(value)
    if not confirm or type(expected_revision) is not int or expected_revision<0:
        raise ValueError("Explicit confirmation and expected revision required")
    records=history(repo,artist)
    if len(records)!=expected_revision:
        raise ValueError("Artist profile revision changed; inspect before saving")
    directory=_under(repo,"local","artist-memory",artist_id(artist))
    directory.mkdir(parents=True,exist_ok=True)
    record={"schema":"artist-memory-revision-v1","artist":artist,"revision":expected_revision+1,
            "previous_sha256":records[-1]["sha256"] if records else None,
            "recorded_utc":now(),"recorded_by":"human_operator","profile":profile}
    # Exclusive file creation rejects competing writes to the same revision.
    create_journal(directory/f"{expected_revision+1:06d}.json",record)
    saved=history(repo,artist)
    if saved[expected_revision]["record"]!=record:
        raise ValueError("Artist profile write verification failed; preserve ledger")
    return saved[expected_revision]


def compile_spec(repo,artist,*,revision=None,overrides=None):
    records=history(repo,artist)
    if not records:
        raise ValueError("No confirmed artist profile")
    revision=len(records) if revision is None else revision
    if type(revision) is not int or not 1<=revision<=len(records):
        raise ValueError("Unknown profile revision")
    source=records[revision-1]
    # Missing override inherits; explicit null clears scalar; a supplied
    # score_constraints mapping replaces the entire default mapping.
    override={"schema":tc.SPEC_SCHEMA} if overrides is None else overrides
    tc.validate_spec(override)
    spec=tc.validate_spec({"schema":tc.SPEC_SCHEMA,**source["record"]["profile"]["defaults"],**override})
    identity={"schema":"artist-spec-compilation-v1","artist":artist,"revision":revision,
              "profile_sha256":source["sha256"],"spec":spec,"automatic_learning":False,
              "inferred_observations_applied":False,"execution_authorized":False}
    return identity


def export_spec(repo,identity,*,confirm=False):
    if not confirm:
        raise ValueError("Explicit local export confirmation required")
    spec=tc.validate_spec(identity["spec"])
    artist=artist_id(identity["artist"])
    raw=json.dumps(identity,ensure_ascii=True,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    digest=hashlib.sha256(raw).hexdigest()
    folder=_under(repo,"local","artist-specs",artist,digest)
    files={"creative-spec.json":spec,"receipt.json":identity}
    if folder.exists():
        for name,value in files.items():
            if _read(folder/name)[0]!=value:
                raise ValueError("Retained artist spec compilation differs")
    else:
        folder.mkdir(parents=True,exist_ok=False)
        for name,value in files.items():
            create_journal(folder/name,value)
        for name,value in files.items():
            if _read(folder/name)[0]!=value:
                raise ValueError("Artist spec export verification failed")
    return folder/"creative-spec.json"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",required=True,type=Path)
    p.add_argument("--artist-memory",required=True)
    actions=p.add_mutually_exclusive_group()
    actions.add_argument("--save",type=Path)
    actions.add_argument("--compile",action="store_true")
    p.add_argument("--expected-revision",type=int)
    p.add_argument("--revision",type=int)
    p.add_argument("--overrides",type=Path)
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        if a.save is not None:
            if a.revision is not None or a.overrides is not None:
                raise ValueError("Save does not accept compilation arguments")
            result=save(a.repo,a.artist_memory,_read(a.save)[0],a.expected_revision,confirm=a.confirm_run)
            print("Saved revision:",result["record"]["revision"])
            print("Profile SHA-256:",result["sha256"])
        elif a.compile:
            if a.expected_revision is not None:
                raise ValueError("Expected revision is only for saving")
            identity=compile_spec(a.repo,a.artist_memory,revision=a.revision,
                                  overrides=_read(a.overrides)[0] if a.overrides else None)
            if a.confirm_run:
                path=export_spec(a.repo,identity,confirm=True)
                print("Local creative spec:",path)
                print("Use --creative-spec with a separately authorized new job.")
            else:
                print(json.dumps(identity,indent=2,ensure_ascii=True))
                print("Preview only; no files written.")
        else:
            if any(x is not None for x in (a.expected_revision,a.revision,a.overrides)) or a.confirm_run:
                raise ValueError("Select a save or compile action")
            records=history(a.repo,a.artist_memory)
            print(json.dumps({"artist":a.artist_memory,"revisions":len(records),
                              "latest":records[-1] if records else None},indent=2,ensure_ascii=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,UnicodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
