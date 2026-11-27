"""Immutable local delivery package and explicit whole-package human review.

No network, no publishing, no audio rewriting, no inferred approval.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile

from . import release_assembly as ra, release_identity as ri
from . import native_draft as nd, cover_import as ci
from .operation_lock import lock


def assembly(repo,release,assembly_id):
    ra._id(release)
    ra._id(assembly_id)
    root=repo/"results/release-assembly"/release.casefold()/assembly_id.casefold()
    if any(p.is_symlink() for p in (root,root.parent,root.parent.parent,root/"assembly.json")):
        raise ValueError("Unexpected assembly symlink")
    saved=nd.read(root/"assembly.json")
    contract=saved["contract"]
    if (contract.get("schema")!="release-assembly-v1" or contract.get("release")!=release
            or contract.get("assembly_id")!=assembly_id
            or contract.get("artwork_attached") is not False
            or saved.get("release_approved") is not False
            or saved.get("publishing_authorized") is not False):
        raise ValueError("Assembly identity differs")
    variants={t["identity"]["job"]:t["identity"]["variant"] for t in contract["tracks"]}
    export,base,_,selections=ra.prepare(repo,release,contract["snapshot"],variants)
    tracks=[{k:v for k,v in t.items() if k!="audio"} for t in selections]
    if (tracks!=contract["tracks"] or any(t["approval"] is None for t in tracks)
            or nd._sha(export/"release.json")!=contract["base_manifest_sha256"]):
        raise ValueError("Assembly source or current audio approval differs")
    hashes=dict(base["files"])
    for t in selections:
        hashes[t["file"]]=t["identity"]["audio_sha256"]
    if saved["files"]!=hashes or saved["status"]!=base["status"]:
        raise ValueError("Assembly manifest differs from source")
    files=ra._files(root,saved)
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual!=set(hashes)|{"assembly.json"}:
        raise ValueError("Unexpected assembly files")
    metadata={"release":release,"type":base["contract"]["type"],
              "title":base["contract"]["title"],"artist":base["contract"]["artist"],
              "tracks":[{"track":t["track"],"job":t["job"],"title":t["title"],
                         "artist":base["contract"]["artist"]} for t in base["tracks"]]}
    return root,saved,files,metadata


def _history(root,manifest_sha):
    if not root.exists():
        return []
    previous=None
    entries=[]
    for i,path in enumerate(sorted(root.iterdir()),1):
        if path.name!=f"{i:06d}.json" or path.is_symlink() or not path.is_file():
            raise ValueError("Unexpected package review ledger entry")
        r=nd.read(path)
        if (r.get("schema")!="release-review-v1" or r.get("sequence")!=i
                or r.get("previous_sha256")!=previous
                or r.get("delivery_manifest_sha256")!=manifest_sha
                or r.get("decision") not in ("approve","revoke")
                or r.get("recorded_by")!="human_operator"
                or r.get("rights_typography_credits_reviewed")!=(r["decision"]=="approve")
                or r.get("publishing_authorized") is not False):
            raise ValueError("Package review ledger identity differs")
        previous=nd._sha(path)
        entries.append(r)
    return entries


def _verify(root,manifest,source,metadata):
    contract=manifest["contract"]
    if (manifest.get("schema")!="release-delivery-v1"
            or contract.get("assembly_manifest_sha256")!=nd._sha(source/"assembly.json")
            or manifest.get("metadata")!=metadata
            or manifest.get("publishing_authorized") is not False):
        raise ValueError("Delivery contract differs")
    art=manifest["artwork"]
    if (art.get("schema")!="cover-import-v1" or art.get("file") not in ("cover.jpg","cover.png")
            or art.get("width")!=ci.PIXELS or art.get("height")!=ci.PIXELS
            or art.get("profile")!="local-3000-square-opaque-v1"):
        raise ValueError("Retained artwork validation differs")
    assembly_manifest=nd.read(source/"assembly.json")
    expected=dict(assembly_manifest["files"])
    expected[art["file"]]=art["sha256"]
    expected["metadata.json"]=nd._sha(root/"metadata.json")
    if nd.read(root/"metadata.json")!=metadata or manifest["files"]!=expected:
        raise ValueError("Delivery metadata or file identity differs")
    ra._files(root,manifest)
    if {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}!=set(expected)|{"delivery.json"}:
        raise ValueError("Unexpected delivery files")
    if manifest.get("status")!=assembly_manifest["status"]:
        raise ValueError("Delivery timing status differs")


def launch(repo,release,*,assembly_id="package-v1",delivery_id="delivery-v1",artwork=None,
           confirm=False,decision=None,expected_artwork_sha256=None,expected_assembly_sha256=None):
    ra._id(delivery_id)
    if decision not in (None,"approve","revoke") or decision and not confirm:
        raise ValueError("Explicit confirmation required for package review")
    base=repo/"results/release-delivery"
    root=base/release.casefold()/delivery_id.casefold()
    ledger=repo/"results/release-review"/release.casefold()/delivery_id.casefold()
    def resolve():
        source,saved,files,metadata=assembly(repo,release,assembly_id)
        contract={"release":release,"assembly_id":assembly_id,"delivery_id":delivery_id,
                  "assembly_manifest_sha256":nd._sha(source/"assembly.json")}
        if expected_assembly_sha256 is not None and contract["assembly_manifest_sha256"]!=expected_assembly_sha256:
            raise ValueError("Frozen workflow assembly hash differs")
        return source,saved,files,metadata,contract

    def existing(data):
        source,saved,files,metadata,contract=data
        if any(p.is_symlink() for p in (base,root.parent,root,root/"delivery.json",ledger,ledger.parent)):
            raise ValueError("Unexpected delivery or review symlink")
        manifest=nd.read(root/"delivery.json")
        if manifest["contract"]!=contract:
            raise ValueError("Existing delivery differs; choose another delivery ID")
        if expected_artwork_sha256 is not None and manifest["artwork"]["sha256"]!=expected_artwork_sha256:
            raise ValueError("Frozen workflow cover hash differs")
        if artwork is not None and nd._sha(Path(artwork))!=manifest["artwork"]["sha256"]:
            raise ValueError("Existing delivery cover differs; choose another delivery ID")
        _verify(root,manifest,source,metadata)
        sha=nd._sha(root/"delivery.json")
        records=_history(ledger,sha)
        return manifest,sha,records

    data=resolve()
    source,saved,files,metadata,contract=data
    print(json.dumps(metadata,ensure_ascii=False,indent=2),flush=True)
    if root.exists():
        manifest,sha,records=existing(data)
        print("Delivery:",root,"Cover SHA-256:",manifest["artwork"]["sha256"],flush=True)
        print("Manifest SHA-256:",sha,flush=True)
        print("Current package approval:",bool(records and records[-1]["decision"]=="approve"),flush=True)
        if decision is None:
            return 0 if manifest["status"]=="complete" else 2
    elif decision is not None:
        raise ValueError("Prepare and review the exact delivery before approval")
    elif artwork is None:
        print("No delivery yet. Supply a local JPEG/PNG cover; no image generation.",flush=True)
        return 2
    elif not confirm:
        print("Plan only. Cover:",artwork,"Output:",root,flush=True)
        print("Confirmation validates and copies the image; no approval.",flush=True)
        return 0

    with ExitStack() as stack:
        for area in ("feedback","exports","release-assembly","release-delivery"):
            stack.enter_context(lock(repo/"results"/area/".active",
                context={"root":root.relative_to(repo).as_posix(),"stage":"delivery","release":release}))
        if resolve()!=data:
            raise ValueError("Assembly or approvals changed")
        if root.exists():
            manifest,sha,records=existing(data)
            if decision is None:
                return 0 if manifest["status"]=="complete" else 2
            if decision=="approve":
                if manifest["status"]!="complete":
                    raise ValueError("Partial timing package cannot receive final package approval")
                if not metadata["artist"].strip():
                    raise ValueError("Explicit artist credit required for final approval")
                print("Review the exact cover, audio, title, artist, track order, typography and usage rights.")
                if input("Type APPROVE only after reviewing all credits, rights and package contents: ").strip()!="APPROVE":
                    raise ValueError("No package approval recorded")
            elif input("Type REVOKE to revoke this package decision: ").strip()!="REVOKE":
                raise ValueError("No revocation recorded")
            if resolve()!=data or existing(data)!=(manifest,sha,records):
                raise ValueError("Delivery or approvals changed during review")
            ledger.mkdir(parents=True,exist_ok=True)
            index=len(records)+1
            receipt={"schema":"release-review-v1","sequence":index,"delivery_manifest_sha256":sha,
                     "previous_sha256":nd._sha(ledger/f"{index-1:06d}.json") if records else None,
                     "decision":decision,"recorded_by":"human_operator",
                     "recorded_utc":datetime.now(timezone.utc).isoformat(),
                     "rights_typography_credits_reviewed":decision=="approve","publishing_authorized":False}
            nd.create_journal(ledger/f"{index:06d}.json",receipt)
            if _history(ledger,sha)[-1]!=receipt:
                raise ValueError("Package review receipt differs")
            print("Recorded human package decision:",decision,"; no publishing authorized.")
            return 0

        if decision is not None or any(p.is_symlink() for p in (base,root.parent,root)) or ledger.exists():
            raise ValueError("Unexpected delivery destination or prior approval evidence")
        art=ci.inspect(artwork)
        if expected_artwork_sha256 is not None and art["sha256"]!=expected_artwork_sha256:
            raise ValueError("Frozen workflow cover changed")
        if art["file"] in files or "metadata.json" in files or "delivery.json" in files:
            raise ValueError("Reserved delivery filename collision")
        ri.ensure_paths([root/"delivery.json",root/"metadata.json",root/art["file"],*(root/n for n in files)])
        root.parent.mkdir(parents=True,exist_ok=True)
        stage=Path(tempfile.mkdtemp(prefix=".delivery-",dir=root.parent))
        try:
            ri.ensure_paths([stage/"delivery.json",stage/"metadata.json",stage/art["file"],*(stage/n for n in files)])
            for name,path in files.items():
                target=stage/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target)
                if nd._sha(target)!=saved["files"][name]:
                    raise ValueError("Assembly file changed during copy")
            shutil.copyfile(artwork,stage/art["file"])
            if nd._sha(stage/art["file"])!=art["sha256"] or nd._sha(Path(artwork))!=art["sha256"]:
                raise ValueError("Artwork changed during copy")
            nd.atomic_write(stage/"metadata.json",metadata)
            hashes={**saved["files"],art["file"]:art["sha256"],
                    "metadata.json":nd._sha(stage/"metadata.json")}
            manifest={"schema":"release-delivery-v1","contract":contract,"metadata":metadata,
                      "artwork":art,"files":hashes,"status":saved["status"],
                      "release_approved":False,"publishing_authorized":False,"inference_calls":0}
            nd.atomic_write(stage/"delivery.json",manifest)
            _verify(stage,manifest,source,metadata)
            if resolve()!=data or root.exists():
                raise ValueError("Assembly or destination changed during delivery")
            stage.rename(root)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    print("Delivery:",root,"; human package review still required.")
    return 0 if manifest["status"]=="complete" else 2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--release-delivery",required=True)
    p.add_argument("--assembly-id",default="package-v1")
    p.add_argument("--delivery-id",default="delivery-v1")
    p.add_argument("--artwork",type=Path)
    g=p.add_mutually_exclusive_group()
    g.add_argument("--approve",action="store_true")
    g.add_argument("--revoke",action="store_true")
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        return launch(a.repo.resolve(),a.release_delivery,assembly_id=a.assembly_id,
                      delivery_id=a.delivery_id,artwork=a.artwork,confirm=a.confirm_run,
                      decision="approve" if a.approve else "revoke" if a.revoke else None)
    except (OSError,ValueError,KeyError,TypeError,EOFError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
