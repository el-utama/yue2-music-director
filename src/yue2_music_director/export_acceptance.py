"""Bounded local native export acceptance using existing music only."""
import json
from pathlib import Path
import tempfile

from . import native_collection as nc, native_library_export as nl
from . import native_draft as nd, release_identity as ri
from .mcp import MCPError, configured_endpoint


def plan(url):
    songs=nl.song_list(url)
    collections=nc.collections(url)
    ids=[row["id"] for row in songs[:2]]
    cases=[]
    if ids:
        cases.append({"id":"single-video","kind":"single","preset":"video","native_songs":ids[:1]})
    if len(ids)==2:
        cases.append({"id":"ep-distribution","kind":"ep","title":"Acceptance EP","preset":"distribution","native_songs":ids})
    for kind,preset in (("album","production"),("playlist","video")):
        eligible=[row for row in collections if row["kind"]==kind and 1<=row["tracks"]<=8]
        if eligible:
            selected=min(eligible,key=lambda row:(row["tracks"],row["id"]))
            cases.append({"id":kind+"-native","kind":kind,"preset":preset,"native_collection":selected["id"]})
        elif ids:
            cases.append({"id":kind+"-manual","kind":kind,"title":"Acceptance "+kind,"preset":preset,"native_songs":ids})
    return {"playable_count":len(songs),"collection_count":len(collections),"cases":cases,
            "native_album_available":any(c["id"]=="album-native" for c in cases),
            "native_playlist_available":any(c["id"]=="playlist-native" for c in cases)}


def run(repo,url,*,confirm,launch):
    url=configured_endpoint(url)
    selected=plan(url)
    print(json.dumps(selected,ensure_ascii=True,indent=2))
    if not selected["cases"]:
        print("No playable native library songs; acceptance blocked")
        return 2
    if not confirm:
        print("Plan only; no exports or inference.")
        return 0
    area=repo/"results/export-check"
    if area.is_symlink():
        raise ValueError("Unexpected acceptance destination symlink")
    area.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix="run-",dir=area))
    outcomes=[]
    for case in selected["cases"]:
        args={k:v for k,v in case.items() if k not in ("id","kind")}
        try:
            if "native_collection" in args:
                # Recheck bounded collection immediately before export; the
                # ordinary exporter also checks its own membership snapshot.
                current=nc.collection(url,args["native_collection"])
                if current["kind"]!=case["kind"] or len(current["song_ids"])>8:
                    raise ValueError("Native acceptance collection changed or exceeds eight tracks")
                args["library_only"]=True
            else:
                args["kind"]=case["kind"]
            code=launch(root,case["id"],[],url,confirm=True,**args)
            package=ri._originals(root/"results/exports",case["id"])
            if package is None:
                raise ValueError("Acceptance export produced no package")
            manifest=nd.read(package/"release.json")
            from .release_export import verify_export
            verify_export(package,manifest["contract"])
            outcomes.append({"case":case["id"],"exit_code":code,"status":manifest["status"],
                             "package":package.relative_to(root).as_posix(),
                             "tracks":len(manifest["tracks"]),
                             "timing":[track["timing"]["status"] for track in manifest["tracks"]]})
        except (OSError,ValueError,KeyError,TypeError,MCPError) as exc:
            outcomes.append({"case":case["id"],"exit_code":2,"status":"blocked","error":str(exc)})
    kinds={case["kind"] for case in selected["cases"]}
    full=(kinds=={"single","ep","album","playlist"} and selected["native_album_available"]
          and selected["native_playlist_available"] and all(row["exit_code"]==0 for row in outcomes)
          and any("exported_unverified_display_anchors" in row.get("timing",[]) for row in outcomes))
    report={"schema":"native-export-acceptance-v1","status":"sample_checks_passed" if full else "incomplete",
            "plan":selected,"outcomes":outcomes,"native_mutations":0,"inference_calls":0,
            "human_player_review":False,"acoustic_alignment_verified":False}
    nd.atomic_write(root/"report.json",report)
    print(json.dumps(report,ensure_ascii=True,indent=2))
    print("Acceptance report:",root/"report.json")
    return 0 if full else 2
