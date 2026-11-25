"""Local launcher for the retained custom/native finishing comparison."""
import argparse
import json
import math
from pathlib import Path
import os
import sys
from datetime import datetime

from .audiobox_eval import AXES, MODEL_REVISION, WEIGHTS_SHA256, evaluate
from .native_recognition import _sha
from .mcp import Client, configured_endpoint, unpack
from .native_process import _source_file
from .director import direct
from .temporal_evidence import inspect_timing
from .audiobox_eval import summarize_evidence


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def discover(results):
    """Match only completed reports with identical source and screening identities."""
    pairs = []
    for path in results.rglob("report.json"):
        if path.parent.name != "headroom-continuation":
            continue
        native = path.parent.parent
        try:
            plan = read(path.parent/"plan.json")
            nr = read(path)
            parent = read(native/"report.json")
            sub = read(native/"submission.json")
            identity = read(native/"run_identity.json")
            if (parent["status"] != "preview_acoustic_blocked"
                or nr["status"] != "candidate_nonregression_unverified"
                or sub["state"] != "SUBMITTING"
                or not parent["run_id"] == identity["run_id"] == plan["run_id"]
                or not parent["request"] == sub["request"] == identity["request"]
                or not parent["source_sha256"] == sub["source_sha256"] == plan["source_sha256"]
                or sub["screening"] != plan["screening"]):
                continue
            source_hash = parent["source_sha256"]
            screening = sub["screening"]
            native_audio = path.parent/"candidate.flac"
            native_hash = nr["after"]["arms"]["B"]["sha256"]
            if nr["after"]["arms"]["A"]["sha256"] != source_hash or _sha(native_audio) != native_hash:
                continue
            for custom_report in native.parent.glob("*/report.json"):
                cr = read(custom_report)
                if cr.get("schema") != "finish-existing-v1" or cr.get("status") != "candidate_nonregression_unverified":
                    continue
                hashes = cr["source_sha256"]
                if hashes["mix"] != source_hash or {"language":cr["language"],
                    "lyrics_sha256":hashes["lyrics"],"baseline_asr_sha256":hashes["baseline_asr"]} != screening:
                    continue
                custom_audio = custom_report.parent/"dynamics/candidate.flac"
                if _sha(custom_audio) != cr["candidate_sha256"]:
                    continue
                pairs.append((sub["request"]["song_id"],custom_audio,native_audio,
                              [source_hash,cr["candidate_sha256"],native_hash]))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if len(pairs) != 1:
        raise ValueError(f"Expected one matching retained comparison, found {len(pairs)}. No evaluation started.")
    return pairs[0]


def cached(results, hashes):
    for path in sorted(results.glob("audiobox-*.json"), reverse=True):
        try:
            report = read(path)
            if (report["schema"] != "audiobox-evaluation-v1"
                or report["model_revision"] != MODEL_REVISION
                or report["weights_sha256"] != WEIGHTS_SHA256
                or report["device"] != "cpu"
                or report["automatic_acceptance"] is not False
                or [row["audio_sha256"] for row in report["rows"]] != hashes
                or [row["arm"] for row in report["rows"]] != [1,2,3]):
                continue
            if all(set(row["scores"]) == set(AXES)
                and all(type(v) in (int,float) and math.isfinite(v) for v in row["scores"].values())
                for row in report["rows"]):
                return report
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            continue
    return None


def source_audio(song_id, digest, url):
    client = Client(configured_endpoint(url), timeout=15).connect()
    if "library_song_files" not in {t.get("name") for t in client.tools()}:
        raise ValueError("Studio does not advertise library_song_files")
    files = unpack(client.call("library_song_files", {"song_id":song_id}))
    if not isinstance(files, dict):
        raise ValueError("Unexpected Studio library response")
    for key in ("audio","audio_path"):
        value = files.get(key)
        if isinstance(value, dict):
            value = value.get("path")
        if isinstance(value,str) and Path(value).is_absolute() and Path(value).is_file():
            source = Path(value).resolve()
            _source_file(files,source)
            if _sha(source) != digest:
                raise ValueError("Library source bytes changed; original comparison cannot be resumed")
            return source
    raise ValueError("Original library audio unavailable")


def run(repo, weights, url):
    results = repo/"results"
    print("Checking retained experiment evidence...", flush=True)
    song, custom, native, hashes = discover(results)
    report = cached(results,hashes)
    if report is not None:
        print("Reusing matching saved AudioBox scores.", flush=True)
    else:
        if not weights.is_file():
            raise ValueError("Local AudioBox checkpoint missing; no automatic download")
        print("Resolving original via read-only Studio library lookup...", flush=True)
        source = source_audio(song,hashes[0],url)
        # An exclusive local lock avoids launching two evaluations simultaneously.
        lock = results/".audiobox-running"
        try:
            fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        except FileExistsError:
            raise ValueError("Evaluation lock exists. Inspect previous run before retrying.") from None
        try:
            os.close(fd)
            report = cached(results,hashes)
            if report is None:
                out = results/("audiobox-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f")+".json")
                os.environ["HF_HUB_OFFLINE"] = "1"
                report = evaluate([source,custom,native],weights,out,confirm=True,
                                  progress=lambda msg:print(msg,flush=True))
        finally:
            lock.unlink()
    print("Candidate     CE       CU       PC       PQ")
    for name,row in zip(("Original","Custom","Native"),report["rows"]):
        print(f"{name:10s} "+" ".join(f"{row['scores'][axis]:8.4f}" for axis in AXES))
    return report


def reference_inputs(results, custom):
    """Recover the exact frozen text inputs from retained manifests and ASR reports."""
    report=read(custom/"report.json")
    hashes=report["source_sha256"]
    lyrics=[]
    for manifest in results.rglob("manifest.json"):
        try:
            entry=read(manifest)["inputs"]["lyrics"]
            if entry["sha256"]!=hashes["lyrics"]:
                continue
            path=Path(entry["path"])
            if path.is_absolute() and path.is_file() and _sha(path)==hashes["lyrics"]:
                lyrics.append(path.resolve())
        except (OSError, ValueError, KeyError, TypeError):
            continue
    baselines=[]
    for path in results.rglob("recognition.json"):
        if path.is_file() and _sha(path)==hashes["baseline_asr"]:
            baselines.append(path.resolve())
    # Byte-identical copies are equivalent, not an ambiguous choice.
    if not lyrics or not baselines:
        raise ValueError("Exact retained lyrics or baseline ASR not found; no new recognition requested")
    return sorted(set(lyrics))[0], sorted(set(baselines))[0],report["language"]


def review_retained(repo,url):
    """Read-only library lookup and offline decision; never evaluate again."""
    results=repo/"results"
    print("Checking completed comparison and saved evaluation...",flush=True)
    song,custom_audio,native_audio,hashes=discover(results)
    quality=cached(results,hashes)
    if quality is None:
        raise ValueError("Matching saved AudioBox evaluation unavailable; review does not run inference")
    custom=custom_audio.parent.parent
    native=native_audio.parent.parent
    lyrics,baseline,language=reference_inputs(results,custom)
    source=source_audio(song,hashes[0],url)
    out=results/("director-review-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    result=direct(source,lyrics,baseline,language,out,custom=custom,native=native,quality=quality)
    print("Decision:",result["status"])
    print("Provisional method:",result["native_first_actions"][0]["method"])
    print("AudioBox evidence:",result["quality_evidence"]["status"])
    print("Artistic winner: not established")
    print("Default custom dynamics: disabled")
    from .finishing_selection import read as read_selection
    selection=read_selection(out/"selection.json")
    for row in selection["candidates"]:
        print(f"{row['method']}: "+("technical pass" if row["eligible"] else row["reason"]))
        if "lyric_screen" in row:
            screen=row["lyric_screen"]
            key=screen["primary_metric"]
            print(f"  {key} edits: {screen['arms']['source'][key]['edits']} -> {screen['arms']['candidate'][key]['edits']}")
            print(f"  true peak: {row['true_peak_dbtp']:.2f} dBTP")
    if result["quality_evidence"]["status"]=="matched_descriptive_estimates":
        for row in result["quality_evidence"]["candidates"]:
            print(row["method"]+" score deltas: "+" ".join(f"{a}={row['delta_from_source'][a]:+.4f}" for a in AXES))
    print("New generation/ASR/evaluator inference: 0")
    return result


def timing_retained(repo,url):
    """Execute the read-only timing action from the completed Director review."""
    results=repo/"results"
    song,custom_audio,native_audio,hashes=discover(results)
    quality=cached(results,hashes)
    if quality is None:
        raise ValueError("Saved matching evaluation required; no inference requested")
    lyrics,baseline,language=reference_inputs(results,custom_audio.parent.parent)
    reference_hashes=[_sha(lyrics),_sha(baseline)]
    selected=None
    for folder in sorted(results.glob("director-review-*"),reverse=True):
        try:
            report=read(folder/"report.json")
            selection=read(folder/"selection.json")
            if (report["schema"]!="director-diagnosis-v1"
                or selection["schema"]!="finishing-selection-v1"
                or any([doc["source_sha256"],doc["lyrics_sha256"],doc["baseline_asr_sha256"]]
                       !=[hashes[0],*reference_hashes] for doc in (report,selection))
                or {row.get("sha256") for row in selection["candidates"]}!=set(hashes[1:])
                or report["quality_evidence"]!=summarize_evidence(quality,selection)
                or report["quality_evidence"]["status"]!="matched_descriptive_estimates"
                or not any(a["action"]=="inspect_existing_native_timing" for a in report["native_first_actions"])):
                continue
            selected=folder
            break
        except (OSError,ValueError,KeyError,TypeError):
            continue
    if selected is None:
        raise ValueError("No matching completed Director timing recommendation")
    duration=quality["rows"][0]["duration_seconds"]
    if type(duration) not in (float,int) or not math.isfinite(duration) or not 1<=duration<=360:
        raise ValueError("Recorded measured source duration invalid")
    print("Inspecting existing Studio karaoke metadata (read-only)...",flush=True)
    source=source_audio(song,hashes[0],url)
    out=selected/("timing-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f")+".json")
    report=inspect_timing(source,song,lyrics,baseline,language,duration,out,url)
    print("Metadata transport:",report["metadata_transport"])
    print("Timing evidence:",report["status"])
    print("Matched display lines:",len(report["lines"]))
    print("Enhanced word anchors:",sum(row["word_anchor_count"] for row in report["lines"]))
    print("Phonetic alignment: not verified")
    print("Automatic lyric/score correction: blocked")
    if report["status"]=="karaoke_display_anchors_only":
        cues=sorted((row for row in report["lines"] if row["asr_line_edits"]),
                    key=lambda row:-row["asr_line_edits"])[:5]
        for i,row in enumerate(cues,1):
            print(f"Review cue {i}: line {row['line_index']}, display anchor {row['start_seconds']:.2f}s, ASR edits {row['asr_line_edits']}")
        print("Next action: retain candidate; display anchors cannot authorize phonetic edits")
    else:
        print("Next action: retain candidate; no usable existing timing evidence")
    print("New generation/ASR/evaluator inference: 0")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--weights",type=Path)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--review",action="store_true")
    mode.add_argument("--timing",action="store_true")
    parser.add_argument("--url",required=True)
    args = parser.parse_args()
    try:
        if args.timing:
            timing_retained(args.repo.resolve(),args.url)
        elif args.review:
            review_retained(args.repo.resolve(),args.url)
        elif args.weights is not None:
            run(args.repo.resolve(),args.weights.resolve(),args.url)
        else:
            raise ValueError("--weights required outside review mode")
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
