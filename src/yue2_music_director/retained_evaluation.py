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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--weights",type=Path,required=True)
    parser.add_argument("--url",required=True)
    args = parser.parse_args()
    try:
        run(args.repo.resolve(),args.weights.resolve(),args.url)
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
