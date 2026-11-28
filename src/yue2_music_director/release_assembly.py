"""Offline release assembly from immutable exports and explicitly approved takes."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile

from . import audio_variant as av, human_feedback as hf, release_identity as ri
from . import release_export as ex, native_draft as nd, creative_core as cc
from .operation_lock import lock


def _id(value):
    cc.validate_job(value,"placeholder","en",195)
    return value


def _files(root,manifest):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Unexpected symlink in package")
    paths={}
    for name,sha in manifest["files"].items():
        parts=PurePosixPath(name).parts
        if not parts or any(p in ("","..",".","/") for p in parts) or "\\" in name or ":" in name:
            raise ValueError("Invalid package file path")
        path=root.joinpath(*parts)
        if not path.is_file() or nd._sha(path)!=sha:
            raise ValueError("Package file identity differs")
        paths[name]=path
    return paths


def prepare(repo,release,snapshot,variants):
    _id(release)
    _id(snapshot)
    exports=repo/"results/exports"
    original=ri._originals(exports,release)
    if original is None:
        raise ValueError("Existing original export required; assembly does not run export")
    base_contract=nd.read(original/"release.json")["contract"]
    root,_,_=ri.original(exports,base_contract)
    if (root!=original or base_contract.get("schema")!="release-export-v1"
            or base_contract.get("audio_variant")!="original"
            or base_contract.get("type") not in ri.FOLDERS):
        raise ValueError("Original release identity differs")
    if base_contract["type"]=="playlist":
        raise ValueError("Playlist export is a listening collection, not an approved release; export Single, EP or Album for assembly")
    ex.verify_export(root,base_contract)
    root,contract=ri.revision(exports,base_contract,root,snapshot)
    manifest=ex.verify_export(root,contract)
    files=_files(root,manifest)
    evidence=contract["sources"]
    tracks=manifest["tracks"]
    jobs=[e["job"] for e in evidence]
    if (not jobs or len(set(jobs))!=len(jobs) or len(tracks)!=len(jobs)
            or set(variants)-set(jobs)):
        raise ValueError("Track or variant selection differs")
    selections=[]
    expected_files=set()
    lyric_policy=manifest.get("lyric_assets")
    if lyric_policy not in (None,ex.CLEAN_LYRIC_POLICY):
        raise ValueError("Unknown export lyric asset policy")
    timing_policy=contract.get("timing_policy")
    if timing_policy not in (None,*ex.PRESETS.values()):
        raise ValueError("Unknown export timing policy")
    for i,(e,t) in enumerate(zip(evidence,tracks),1):
        job=e["job"]
        source=ex.retained(repo,job)
        if (source["evidence"]!=e or t["job"]!=job or t["track"]!=i
                or t["audio_sha256"]!=source["result"]["audio_sha256"]
                or t["title"]!=source["brief"]["title"]):
            raise ValueError("Export track lineage differs")
        matches=[name for name in files if name.endswith(".flac") and
                 (contract["type"]=="single" or name.startswith(f"{i:02d} - "))]
        if len(matches)!=1:
            raise ValueError("Ambiguous exported track audio")
        name=matches[0]
        stem=name[:-5]
        if manifest["files"][name]!=t["audio_sha256"]:
            raise ValueError("Export audio hash differs from retained original")
        expected=ex.lyric_bytes(source)
        if (stem+".txt" not in files or files[stem+".txt"].read_bytes()!=expected):
            raise ValueError("Export lyric text differs")
        if lyric_policy==ex.CLEAN_LYRIC_POLICY:
            clean=stem+".clean.txt"
            if clean not in files or files[clean].read_bytes()!=ex.clean_lyric_bytes(source):
                raise ValueError("Clean export lyric text differs")
            expected_files.add(clean)
        statuses=("not_requested",) if timing_policy==ex.PRESETS["distribution"] else ("exported_unverified_display_anchors","unavailable")
        if t["timing"]["status"] not in statuses:
            raise ValueError("Unknown source timing status for preset")
        timed=t["timing"]["status"]=="exported_unverified_display_anchors"
        expected_files.update((name,stem+".txt"))
        if timed:
            expected_files.update((stem+".lrc",stem+".srt"))
        if any((stem+suffix in files)!=timed for suffix in (".lrc",".srt")):
            raise ValueError("Incomplete or unexpected timed text pair")
        selected=av.select(repo,source,variants.get(job,"original"))
        key=selected["identity"]
        approval=hf.approval_receipt(repo,key,release)
        selections.append({"track":i,"file":name,"identity":key,"approval":approval,
                           "audio":selected["audio"],"timing":t["timing"]})
    if set(files)!=expected_files:
        raise ValueError("Unexpected files in source package")
    expected_status="complete" if all(s["timing"]["status"] in ("exported_unverified_display_anchors","not_requested") for s in selections) else "partial_missing_timing"
    if manifest.get("status")!=expected_status:
        raise ValueError("Source package timing status differs")
    return root,manifest,files,selections


def assembly_contract(root,release,snapshot,assembly_id,selections):
    return {"schema":"release-assembly-v1","release":release,"snapshot":snapshot,
            "assembly_id":assembly_id,"base_manifest_sha256":nd._sha(root/"release.json"),
            "tracks":[{k:v for k,v in s.items() if k!="audio"} for s in selections],
            "artwork_attached":False}


def launch(repo,release,*,snapshot="v1",assembly_id="package-v1",variants=None,confirm=False,
           expected_contract=None):
    _id(assembly_id)
    variants=variants or {}
    for job,variant in variants.items():
        _id(job)
        _id(variant)
    def resolve():
        root,manifest,files,selections=prepare(repo,release,snapshot,variants)
        contract=assembly_contract(root,release,snapshot,assembly_id,selections)
        if expected_contract is not None and contract!=expected_contract:
            raise ValueError("Frozen workflow assembly contract differs")
        return contract,manifest,files,selections
    contract,manifest,files,selections=resolve()
    base=repo/"results/release-assembly"
    root=base/release.casefold()/assembly_id.casefold()
    print(json.dumps(contract,ensure_ascii=False,indent=2),flush=True)
    missing=[s["identity"]["job"] for s in selections if s["approval"] is None]
    if missing:
        print("Missing current explicit audio approvals:",", ".join(missing),flush=True)
        return 2
    if not confirm:
        print("Plan only. No writes, inference or publishing.",flush=True)
        return 0
    with ExitStack() as stack:
        # No feedback revocation or export writer may interleave with assembly.
        for area in ("feedback","exports","release-assembly"):
            stack.enter_context(lock(repo/"results"/area/".active",
                context={"root":root.relative_to(repo).as_posix(),"stage":"assembly","release":release}))
        if resolve()!=(contract,manifest,files,selections):
            raise ValueError("Release source or approval changed")
        if any(p.is_symlink() for p in (base,root.parent,root)):
            raise ValueError("Unexpected assembly destination symlink")
        hashes=dict(manifest["files"])
        for s in selections:
            hashes[s["file"]]=s["identity"]["audio_sha256"]
        result={"contract":contract,"files":hashes,"status":manifest["status"],
                "audio_approvals_verified_at_assembly":True,"release_approved":False,
                "publishing_authorized":False,"inference_calls":0,
                "timing_note":"Retained display anchors; verified gain preserves timeline, not acoustic alignment."}
        if root.exists():
            if nd.read(root/"assembly.json")!=result:
                raise ValueError("Existing assembly differs; choose a new assembly ID")
            actual={p.relative_to(root).as_posix():nd._sha(p) for p in root.rglob("*")
                    if p.is_file() and p!=root/"assembly.json"}
            if actual!=hashes or any(p.is_symlink() for p in root.rglob("*")):
                raise ValueError("Existing assembly file hashes differ")
            print("Existing assembly verified:",root)
            return 0 if result["status"]=="complete" else 2
        ri.ensure_paths([root/"assembly.json",*(root/name for name in hashes)])
        root.parent.mkdir(parents=True,exist_ok=True)
        stage=Path(tempfile.mkdtemp(prefix=".assembly-",dir=root.parent))
        try:
            ri.ensure_paths([stage/"assembly.json",*(stage/name for name in hashes)])
            replacements={s["file"]:s["audio"] for s in selections}
            for name,source in files.items():
                target=stage/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(replacements.get(name,source),target)
                if nd._sha(target)!=hashes[name]:
                    raise ValueError("Assembly input changed during copy")
            if resolve()!=(contract,manifest,files,selections):
                raise ValueError("Release source or approval changed during assembly")
            nd.atomic_write(stage/"assembly.json",result)
            if root.exists():
                raise ValueError("Assembly destination appeared")
            stage.rename(root)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    print("Assembly:",root,"; no publishing or final release approval.")
    return 0 if result["status"]=="complete" else 2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--assemble-release",required=True)
    p.add_argument("--snapshot",default="v1")
    p.add_argument("--assembly-id",default="package-v1")
    p.add_argument("--variant",action="append",default=[],metavar="JOB=VARIANT")
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        variants={}
        for item in a.variant:
            job,sep,variant=item.partition("=")
            if not sep or job in variants:
                raise ValueError("Use one JOB=VARIANT selection per track")
            variants[job]=variant
        return launch(a.repo.resolve(),a.assemble_release,snapshot=a.snapshot,
                      assembly_id=a.assembly_id,variants=variants,confirm=a.confirm_run)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
