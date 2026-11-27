"""One bounded local release workflow, with immutable plan and stage evidence.

Uses completed exports only. Does not generate, finish, approve, or publish
anything implicitly. A partial delivery never modifies the completed songs.
"""
import argparse
import json
from pathlib import Path
import sys

from . import release_assembly as ra, release_delivery as rd, cover_import as ci
from . import native_draft as nd
from .operation_lock import lock


def _art_hash(path):
    path=Path(path)
    if (path.is_symlink() or not path.is_file()
            or path.suffix.lower() not in ci.FORMATS
            or not 0<path.stat().st_size<=ci.MAX_BYTES):
        raise ValueError("Supply a bounded local JPEG/PNG cover")
    return nd._sha(path)


def launch(repo,release,*,workflow_id="release-v1",snapshot=None,variants=None,
           artwork=None,confirm=False,artist=None):
    ra._id(release)
    ra._id(workflow_id)
    base=repo/"results/release-workflow"
    root=base/release.casefold()/workflow_id.casefold()
    plan_path=root/"plan.json"
    result_path=root/"result.json"
    if any(p.is_symlink() for p in (base,root.parent,root,plan_path,result_path)):
        raise ValueError("Unexpected release workflow symlink")
    # Use deterministic stage IDs unique to this workflow, not default folders
    # which might already belong to independently created assemblies.
    stage_id=workflow_id
    old=nd.read(plan_path) if plan_path.is_file() else None
    if old is not None:
        if (old.get("schema")!="release-workflow-v1" or old.get("release")!=release
                or old.get("workflow_id")!=workflow_id):
            raise ValueError("Retained workflow identity differs")
        if snapshot is not None and snapshot!=old["snapshot"] or variants is not None and variants!=old["variants"]:
            raise ValueError("Workflow selection differs; choose a new workflow ID")
        snapshot=old["snapshot"]
        variants=old["variants"]
        if artist is None and "artist_completion" in old:
            artist=old["artist_completion"]["artist"]
    else:
        snapshot=snapshot or "v1"
        variants=variants or {}
    ra._id(snapshot)
    for job,variant in variants.items():
        ra._id(job)
        ra._id(variant)

    def resolve():
        export,manifest,_,selections=ra.prepare(repo,release,snapshot,variants)
        return manifest,ra.assembly_contract(export,release,snapshot,stage_id,selections)
    manifest,contract=resolve()
    credit,completion=rd.complete_credit(manifest["contract"]["artist"],artist)
    missing=[t["identity"]["job"] for t in contract["tracks"] if t["approval"] is None]
    if missing:
        print("Awaiting explicit audio approvals:",", ".join(missing),flush=True)
        return 2
    delivery=repo/"results/release-delivery"/release.casefold()/stage_id.casefold()
    assembly=repo/"results/release-assembly"/release.casefold()/stage_id.casefold()
    if artwork is None and old is None:
        print("Approved audio available; supply local finished cover to plan delivery.",flush=True)
        return 2
    sha=_art_hash(artwork) if artwork is not None else old["artwork_sha256"]
    plan={"schema":"release-workflow-v1","release":release,"workflow_id":workflow_id,
          "snapshot":snapshot,"variants":variants,"assembly_contract":contract,
          "artwork_sha256":sha,"release_type":manifest["contract"]["type"],
          "title":manifest["contract"]["title"],"artist":credit,
          "stage_ids":{"assembly":stage_id,"delivery":stage_id},
          "budgets":{"provider_calls":0,"native_jobs":0,"recognition_calls":0,
                     "image_generation_calls":0,"finishing_renders":0,"publishing_calls":0}}
    if completion is not None:
        plan["artist_completion"]=completion
    if old is not None and old!=plan:
        raise ValueError("Frozen workflow differs; select another workflow ID")
    if old is None and (assembly.exists() or delivery.exists() or root.exists()):
        raise ValueError("Workflow destination already exists independently; choose another workflow ID")
    print(json.dumps(plan,ensure_ascii=False,indent=2),flush=True)

    def retained_result():
        assembly_path,saved,_,metadata=rd.assembly(repo,release,stage_id)
        if saved["contract"]!=contract:
            raise ValueError("Workflow assembly identity differs")
        # Existing delivery is verified read-only, with current approvals.
        code=rd.launch(repo,release,assembly_id=stage_id,delivery_id=stage_id,
                       artist=artist,expected_artwork_sha256=sha,expected_assembly_sha256=nd._sha(assembly_path/"assembly.json"))
        saved_delivery=nd.read(delivery/"delivery.json")
        result={"schema":"release-workflow-result-v1","plan_sha256":nd._sha(plan_path),
                "stages":{"audio_assembly":{"status":saved["status"],"manifest_sha256":nd._sha(assembly_path/"assembly.json")},
                          "delivery":{"status":saved_delivery["status"],"manifest_sha256":nd._sha(delivery/"delivery.json")}},
                "status":saved_delivery["status"],"package_approval_separate":True,
                "publishing_authorized":False}
        if result_path.exists() and nd.read(result_path)!=result:
            raise ValueError("Retained workflow result differs")
        return code,result

    if result_path.exists():
        return retained_result()[0]
    if not confirm:
        print("Plan only; no output or provider/Studio calls. Confirm to copy existing approved audio and cover.",flush=True)
        return 0
    if not delivery.exists() and artwork is None:
        raise ValueError("Incomplete workflow needs the exact previously selected cover bytes")
    with lock(base/".active",context={"root":root.relative_to(repo).as_posix(),"stage":"release_workflow","release":release}):
        if resolve()!=(manifest,contract):
            raise ValueError("Release source or approval changed")
        if plan_path.exists():
            if nd.read(plan_path)!=plan:
                raise ValueError("Retained workflow plan differs")
        else:
            if assembly.exists() or delivery.exists() or root.exists():
                raise ValueError("Workflow destination already exists")
            root.mkdir(parents=True,exist_ok=False)
            nd.create_journal(plan_path,plan)
        if result_path.exists():
            return retained_result()[0]
        ra.launch(repo,release,snapshot=snapshot,assembly_id=stage_id,variants=variants,
                  confirm=True,expected_contract=contract)
        # Assembly may have completed with missing timing (exit 2). Its
        # actual verified receipt is authoritative, not the exit code alone.
        assembly_path,saved,_,_=rd.assembly(repo,release,stage_id)
        if saved["contract"]!=contract:
            raise ValueError("Workflow assembly contract differs")
        rd.launch(repo,release,assembly_id=stage_id,delivery_id=stage_id,
                  artwork=None if delivery.exists() else artwork,confirm=True,
                  artist=artist,expected_artwork_sha256=sha,expected_assembly_sha256=nd._sha(assembly_path/"assembly.json"))
        code,result=retained_result()
        nd.create_journal(result_path,result)
    print("Workflow:",root,"; package approval remains a separate human decision.",flush=True)
    return code


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--release",required=True)
    p.add_argument("--workflow-id",default="release-v1")
    p.add_argument("--snapshot")
    p.add_argument("--variant",action="append",metavar="JOB=VARIANT")
    p.add_argument("--artwork",type=Path)
    p.add_argument("--artist",help="Explicitly fill an omitted original export artist credit")
    p.add_argument("--confirm-run",action="store_true")
    a=p.parse_args()
    try:
        variants=None
        if a.variant is not None:
            variants={}
            for item in a.variant:
                job,sep,variant=item.partition("=")
                if not sep or job in variants:
                    raise ValueError("Use one JOB=VARIANT selection per track")
                variants[job]=variant
        return launch(a.repo.resolve(),a.release,workflow_id=a.workflow_id,snapshot=a.snapshot,
                      variants=variants,artwork=a.artwork,confirm=a.confirm_run,artist=a.artist)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        print("Retain completed stages and retry only the same workflow; no external replay.",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
