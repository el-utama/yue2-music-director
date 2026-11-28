"""Bounded local native export acceptance using existing music only."""
import json
from pathlib import Path, PurePosixPath
import tempfile

from . import native_collection as nc, native_library_export as nl
from . import native_draft as nd, release_identity as ri
from .mcp import MCPError, configured_endpoint


def plan(url,*,collections_only=False,collection_kind=None):
    songs=nl.song_list(url)
    collections=nc.collections(url)
    ids=[row["id"] for row in songs[:2]]
    cases=[]
    if ids and not collections_only:
        cases.append({"id":"single-video","kind":"single","preset":"video","native_songs":ids[:1]})
    if len(ids)==2 and not collections_only:
        cases.append({"id":"ep-distribution","kind":"ep","title":"Acceptance EP","preset":"distribution","native_songs":ids})
    for kind,preset in (("album","production"),("playlist","video")):
        if collection_kind and kind!=collection_kind:
            continue
        cap=24 if kind=="album" else 100
        eligible=[row for row in collections if row["kind"]==kind and 1<=row["tracks"]<=cap]
        if eligible:
            selected=min(eligible,key=lambda row:(row["tracks"],row["id"]))
            cases.append({"id":kind+"-native","kind":kind,"preset":preset,"native_collection":selected["id"]})
        elif ids and not collections_only:
            cases.append({"id":kind+"-manual","kind":kind,"title":"Acceptance "+kind,"preset":preset,"native_songs":ids})
    return {"playable_count":len(songs),"collection_count":len(collections),"cases":cases,
            "native_album_count":sum(row["kind"]=="album" for row in collections),
            "native_playlist_count":sum(row["kind"]=="playlist" for row in collections),
            "collections_only":collections_only,"collection_kind":collection_kind,
            "native_album_available":any(c["id"]=="album-native" for c in cases),
            "native_playlist_available":any(c["id"]=="playlist-native" for c in cases)}


def verify_sample(package,manifest,case,expected):
    """Verify promised assets and track order, not only self-reported hashes."""
    from . import release_export as ex
    contract=manifest["contract"]
    ex.verify_export(package,contract)
    if (contract["type"]!=case["kind"] or contract["timing_policy"]!=ex.PRESETS[case["preset"]]
            or contract.get("source_policy")!="native-library-draft-v1"
            or manifest.get("release_approved") is not False
            or manifest.get("studio_mutations")!=0 or manifest.get("inference_calls")!=0):
        raise ValueError("Acceptance package contract differs")
    sources,tracks=contract["sources"],manifest["tracks"]
    ids=[s["song_id"] for s in sources]
    if ids!=expected or [t.get("song_id") for t in tracks]!=expected:
        raise ValueError("Acceptance package track membership or order differs")
    if len(tracks)!=len(sources):
        raise ValueError("Acceptance package track count differs")
    files=manifest["files"]
    required=set()
    audio_paths=[]
    for number,(source,track) in enumerate(zip(sources,tracks),1):
        if track["track"]!=number or track["audio_sha256"]!=source["audio_sha256"]:
            raise ValueError("Acceptance track identity differs")
        name=track["audio_file"]
        path=PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or name not in files or path.suffix!=source["audio_extension"]:
            raise ValueError("Invalid acceptance audio path")
        if files[name]!=source["audio_sha256"]:
            raise ValueError("Acceptance audio does not preserve source bytes")
        required.add(name)
        audio_paths.append(name)
        stem=name[:-len(path.suffix)]
        tagged=stem+".txt"
        text=(package/tagged).read_bytes() if tagged in files else b""
        if nd.digest(text)!=source["lyrics_sha256"]:
            raise ValueError("Acceptance production lyrics differ from source")
        if text:
            required.add(tagged)
        lyrics=text.decode("utf-8")
        clean=ex.clean_lyric_bytes({"brief":{"lyrics":lyrics},"native_snapshot":{}})
        if clean:
            clean_name=stem+".clean.txt"
            if clean_name not in files or (package/clean_name).read_bytes()!=clean:
                raise ValueError("Acceptance clean lyrics differ")
            required.add(clean_name)
        if track.get("clean_lyrics_available")!=bool(clean):
            raise ValueError("Acceptance clean lyrics availability differs")
        timing=track["timing"]["status"]
        if not clean and timing!="not_applicable":
            raise ValueError("Unexpected instrumental timing status")
        if clean and case["preset"]=="distribution" and timing!="not_requested":
            raise ValueError("Unexpected distribution timing status")
        if clean and case["preset"]!="distribution" and timing not in ("unavailable","exported_unverified_display_anchors"):
            raise ValueError("Unexpected vocal timing status")
        if timing=="exported_unverified_display_anchors":
            lrc_name,srt_name=stem+".lrc",stem+".srt"
            if lrc_name not in files or srt_name not in files:
                raise ValueError("Acceptance timed lyric assets missing")
            raw=(package/lrc_name).read_bytes()
            evidence=track["timing"]
            if evidence.get("word_timing_status")=="discarded_invalid_word_anchors":
                native_name=stem+".native.lrc"
                if native_name not in files:
                    raise ValueError("Missing preserved native LRC")
                original=(package/native_name).read_bytes()
                derived,srt,issue=ex.native_timing_assets(original.decode("utf-8"),lyrics,source["duration_seconds"],video=case["preset"]=="video")
                if (not issue or issue!=evidence.get("word_timing_issue") or nd.digest(original)!=evidence["source_lrc_sha256"]
                        or raw!=derived.encode("utf-8") or nd.digest(raw)!=evidence.get("derived_lrc_sha256")):
                    raise ValueError("Acceptance line fallback differs from native source")
                required.add(native_name)
            else:
                if nd.digest(raw)!=evidence["source_lrc_sha256"]:
                    raise ValueError("Acceptance LRC source hash differs")
                _,srt=ex.timed_text(raw.decode("utf-8"),lyrics,source["duration_seconds"],
                                    library_only=True,video=case["preset"]=="video")
            if (package/srt_name).read_bytes()!=srt.encode("utf-8"):
                raise ValueError("Acceptance SRT differs from native timing")
            required.update((lrc_name,srt_name))
            if case["preset"]=="video":
                line_name=stem+".line.lrc"
                if line_name not in files or (package/line_name).read_bytes()!=ex.video_line_bytes(raw.decode("utf-8"),lyrics,source["duration_seconds"],library_only=True):
                    raise ValueError("Acceptance line LRC differs")
                required.add(line_name)
    if case["kind"]=="playlist":
        expected_m3u=("#EXTM3U\n"+"\n".join(audio_paths)+"\n").encode("utf-8")
        if "playlist.m3u8" not in files or (package/"playlist.m3u8").read_bytes()!=expected_m3u:
            raise ValueError("Acceptance playlist order or relative paths differ")
        required.add("playlist.m3u8")
    if set(files)!=required:
        raise ValueError("Acceptance package has missing or unexpected assets")
    expected_status="partial_missing_timing" if any(t["timing"]["status"]=="unavailable" for t in tracks) else "complete"
    if manifest["status"]!=expected_status:
        raise ValueError("Acceptance status differs from actual assets")


def run(repo,url,*,confirm,launch,collections_only=False,collection_kind=None):
    url=configured_endpoint(url)
    selected=plan(url,collections_only=collections_only,collection_kind=collection_kind)
    print(json.dumps(selected,ensure_ascii=True,indent=2))
    if not selected["cases"]:
        print("No eligible native collection or playable sample; acceptance blocked")
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
                cap=24 if case["kind"]=="album" else 100
                if current["kind"]!=case["kind"] or len(current["song_ids"])>cap:
                    raise ValueError("Native acceptance collection changed or exceeds export track limit")
                args["library_only"]=True
                args["expected_collection"]=current
                expected=current["song_ids"]
            else:
                args["kind"]=case["kind"]
                expected=args["native_songs"]
            code=launch(root,case["id"],[],url,confirm=True,**args)
            package=ri._originals(root/"results/exports",case["id"])
            if package is None:
                raise ValueError("Acceptance export produced no package")
            manifest=nd.read(package/"release.json")
            verify_sample(package,manifest,case,expected)
            if code!=(0 if manifest["status"]=="complete" else 2):
                raise ValueError("Acceptance command status differs from package")
            outcomes.append({"case":case["id"],"exit_code":code,"status":manifest["status"],
                             "package":package.relative_to(root).as_posix(),
                             "tracks":len(manifest["tracks"]),
                             "timing":[track["timing"]["status"] for track in manifest["tracks"]],
                             "timing_issues":[track["timing"].get("reason","unavailable") for track in manifest["tracks"] if track["timing"]["status"]=="unavailable"],
                             "word_timing_fallbacks":[t["track"] for t in manifest["tracks"] if t["timing"].get("word_timing_status")=="discarded_invalid_word_anchors"],
                             "asset_checks":"passed"})
        except (OSError,ValueError,KeyError,TypeError,MCPError) as exc:
            outcomes.append({"case":case["id"],"exit_code":2,"status":"blocked","error":str(exc)})
    kinds={case["kind"] for case in selected["cases"]}
    required_kinds={collection_kind} if collection_kind else ({"album","playlist"} if collections_only else {"single","ep","album","playlist"})
    full=(kinds==required_kinds and ("album" not in required_kinds or selected["native_album_available"])
          and ("playlist" not in required_kinds or selected["native_playlist_available"]) and all(row["exit_code"]==0 for row in outcomes)
          and any("exported_unverified_display_anchors" in row.get("timing",[]) for row in outcomes))
    report={"schema":"native-export-acceptance-v1","status":((collection_kind+"_checks_passed" if collection_kind else "collection_checks_passed") if collections_only else "sample_checks_passed") if full else "incomplete",
            "plan":selected,"outcomes":outcomes,"native_mutations":0,"inference_calls":0,
            "human_player_review":False,"acoustic_alignment_verified":False}
    nd.atomic_write(root/"report.json",report)
    print(json.dumps(report,ensure_ascii=True,indent=2))
    print("Acceptance report:",root/"report.json")
    return 0 if full else 2
