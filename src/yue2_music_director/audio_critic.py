"""Bounded offline calibration of an audio-aware critic on the retained P5 pair."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile

from . import native_draft as nd

# Published release and LFS identities, not floating main URLs.
ASSETS = (
    ("HOT-Step-CPP-v1.5.2-win-x64-cpu.zip",
     "https://github.com/scragnog/HOT-Step-CPP/releases/download/v1.5.2/HOT-Step-CPP-v1.5.2-win-x64-cpu.zip",
     158725706, "92de8271d38f16922d44ba176bcad9bff71df24bae301ba3e2594a6c2893d4a3"),
    ("moss-aud-f16.gguf",
     "https://huggingface.co/scragnog/MOSS-Music-8B-Instruct-GGUF/resolve/9f3246e276573548571db14638d9dcc69cdf08ac/moss-aud-f16.gguf",
     1724480640, "014b971719a9b46586ea78ea3d15f39ac0f1932678e30c72fa63222f8aea5f79"),
    ("moss-lm-q4_k_m.gguf",
     "https://huggingface.co/nerualdreming/MOSS-Music-8B-Instruct-GGUF/resolve/0b4eac01086c26baf93238aa8b142ec07b3ae56d/moss-lm-q4_k_m.gguf",
     5188223648, "bc2783b68fee6dac606599c4b8f15bff5e37913b8d10fbfb8c550f5667dee3e8"),
)

# Requirements authored independently from the original demo brief. C01/C02
# are sanity controls, not targets to improve. No user listening verdict or
# route label is given to the evaluator.
RUBRIC = (
    ("R01", "A slow blues/soul ballad character."),
    ("R02", "An intimate male low-register lead vocal with restrained, conversational phrasing."),
    ("R03", "Warm piano and electric guitar responses around the vocal."),
    ("R04", "Brushed or restrained drums with a gradual increase in rhythmic support."),
    ("R05", "A contrast between quiet verses and a more expansive later refrain."),
    ("R06", "Expressive pauses or space between vocal phrases."),
    ("R07", "An ending that resolves gently rather than stopping abruptly."),
    ("C01", "The recording is wholly instrumental with no singing."),
    ("C02", "The dominant style is a fast, aggressive electronic dance track."),
)

def prompt_text():
    checks = "\n".join(f"{key}: {claim}" for key, claim in RUBRIC)
    return (
        "Assess the actual recording only. Do not infer from the requested properties. "
        "For each ID below report supported, contradicted, or uncertain, and one short "
        "specific audible cue. Use uncertain for weak or unlocalized evidence. "
        "Do not guess artist, title, human authorship, precise timestamps or exact lyrics. "
        "Return only a JSON array of objects with exactly id, status, evidence, "
        "one per ID, in the listed order. Do not give a numerical quality score.\n" + checks
    )

def parse_response(raw):
    """Malformed or missing answers are unknown, never silently repaired."""
    unknown = [{"id": key, "status": "uncertain", "evidence": None}
               for key, _ in RUBRIC]
    try:
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) != len(RUBRIC):
            raise ValueError("coverage")
        by_id = {}
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"id", "status", "evidence"}
                    or row["id"] in by_id
                    or row["status"] not in ("supported", "contradicted", "uncertain")
                    or not isinstance(row["evidence"], str)
                    or not row["evidence"].strip() or len(row["evidence"]) > 1000):
                raise ValueError("row")
            by_id[row["id"]] = row
        if set(by_id) != {key for key, _ in RUBRIC}:
            raise ValueError("identity")
        return "parsed_unvalidated", [by_id[key] for key, _ in RUBRIC]
    except (ValueError, TypeError, KeyError):
        return "unparseable", unknown

def retained_pair(repo):
    brief = nd.load_brief(repo/"examples/artist-demo/brief.json")
    root = repo/"results/drafts"/("artist-"+nd.digest(nd._canonical(brief)))
    comparison = root/"direct-native-comparison"
    joined = nd.read(comparison/"comparison-result.json")
    if (joined.get("schema") != "matched-native-result-v1"
            or joined.get("automatic_winner") is not False
            or joined.get("saved_score_identity") != "identical"):
        raise ValueError("Expected the retained unchanged-score comparison")
    candidates = [p for p in (root/"draft",root/"oom-recovery-1"/"draft")
                  if (p/"report.json").is_file()]
    if len(candidates) != 1:
        raise ValueError("Exactly one reviewed arm required")
    rows = []
    for name, route, draft in (
        ("reviewed", "reviewed_native", candidates[0]),
        ("direct", "direct_native", comparison/"draft"),
    ):
        report = nd.read(draft/"report.json")
        journal = nd.read(draft/"journal_song.json")
        request = nd.read(draft/"request.json")
        if (report != joined[name] or report.get("generation_path") != route
                or nd.read(draft/"brief.json") != brief
                or report.get("brief_sha256") != nd.digest(nd._canonical(brief))
                or report.get("request_sha256") != nd.digest(nd._canonical(request))
                or journal.get("request_sha256") != report["request_sha256"]
                or journal.get("state") != "COMPLETED"
                or journal.get("job_id") != report.get("job_id")
                or journal.get("song_id") != report.get("song_id")
                or journal.get("reference_configuration") != joined["comparison"]["reference_configuration"]
                or journal.get("audio_sha256") != report.get("audio_sha256")
                or report.get("automatic_acceptance") is not False):
            raise ValueError("Retained arm identity differs")
        expected = nd.request_for(brief)
        if name == "reviewed":
            expected["abc"] = (root/"native-plan.abc").read_bytes().decode("utf-8")
        if request != expected:
            raise ValueError("Retained request differs")
        audio = Path(report["audio"])
        seconds = report["acoustic"]["duration_seconds"]
        if (not audio.is_absolute() or not audio.is_file() or audio.suffix.lower() != ".flac"
                or nd._sha(audio) != report["audio_sha256"]
                or report["acoustic"]["sha256"] != report["audio_sha256"]
                or type(seconds) not in (float, int) or not math.isfinite(seconds)
                or not 1 <= seconds <= 210):
            raise ValueError("Retained FLAC identity or duration differs")
        rows.append({"arm": name, "audio": str(audio), "audio_sha256": report["audio_sha256"],
                     "acoustic": report["acoustic"], "lyric_screen": report["lyric_screen"]})
    if rows[0]["audio_sha256"] == rows[1]["audio_sha256"]:
        raise ValueError("Expected distinct recordings")
    return rows

def verify_file(path, size, sha):
    if not path.is_file() or path.stat().st_size != size or nd._sha(path) != sha:
        raise ValueError(f"Missing or changed pinned asset: {path.name}")

def download(root, asset):
    name, url, size, sha = asset
    path = root/name
    if path.exists():
        verify_file(path, size, sha)
        print("Reusing verified", name, flush=True)
        return
    curl = shutil.which("curl.exe")
    if not curl:
        raise ValueError("Windows curl.exe is required for explicit setup")
    part = path.with_suffix(path.suffix+".part")
    if part.exists() and part.stat().st_size > size:
        raise ValueError("Oversized partial download; inspect manually")
    remaining = size-(part.stat().st_size if part.exists() else 0)
    if shutil.disk_usage(root).free < remaining+512*1024**2:
        raise ValueError("Insufficient free disk space")
    if remaining:
        print("Downloading pinned", name, flush=True)
        subprocess.run([curl, "--fail", "--location", "--retry", "2", "--connect-timeout", "30",
                        "--continue-at", "-", "--output", str(part), url], check=True,
                       timeout=10800)
    verify_file(part, size, sha)
    part.replace(path)

def archive_members(archive):
    # Only the captioner and its direct sibling DLLs; no UI, server or installer.
    with zipfile.ZipFile(archive) as z:
        files = [i for i in z.infolist() if not i.is_dir()]
        candidates = [i for i in files if PurePosixPath(i.filename).name == "ace-caption.exe"]
        if len(candidates) != 1:
            raise ValueError("Expected exactly one captioner in pinned release")
        parent = PurePosixPath(candidates[0].filename).parent
        chosen = [i for i in files if PurePosixPath(i.filename).parent == parent
                  and (PurePosixPath(i.filename).suffix.lower() == ".dll"
                       or i == candidates[0])]
        names = [PurePosixPath(i.filename).name for i in chosen]
        if (len(set(n.casefold() for n in names)) != len(names)
                or any("/" in n or "\\" in n or ":" in n or n in (".","..") for n in names)
                or not {"ggml.dll","ggml-base.dll"}.issubset(names)
                or sum(i.file_size for i in chosen) > 1024**3):
            raise ValueError("Unexpected pinned archive layout")
        return [(i.filename, PurePosixPath(i.filename).name) for i in chosen]

def verify_runtime(root):
    for name, _, size, sha in ASSETS:
        verify_file(root/name, size, sha)
    archive = root/ASSETS[0][0]
    engine = root/"engine"
    members = archive_members(archive)
    if not engine.is_dir() or {p.name for p in engine.iterdir()} != {n for _, n in members}:
        raise ValueError("Captioner runtime missing or changed; use --setup")
    with zipfile.ZipFile(archive) as z:
        for member, name in members:
            with z.open(member) as f:
                digest = hashlib.sha256()
                for block in iter(lambda: f.read(1024*1024), b""):
                    digest.update(block)
            if nd._sha(engine/name) != digest.hexdigest():
                raise ValueError("Captioner runtime differs from pinned archive")
    return engine/"ace-caption.exe"

def setup(root):
    if os.name != "nt":
        raise ValueError("Pinned setup is Windows x64 only")
    root.mkdir(parents=True, exist_ok=True)
    for asset in ASSETS:
        download(root, asset)
    engine = root/"engine"
    if not engine.exists():
        stage = root/"engine.staging"
        stage.mkdir(exist_ok=False)
        with zipfile.ZipFile(root/ASSETS[0][0]) as z:
            for member, name in archive_members(root/ASSETS[0][0]):
                with z.open(member) as src, (stage/name).open("xb") as dst:
                    shutil.copyfileobj(src,dst)
        stage.rename(engine)
    verify_runtime(root)
    print("Verified CPU captioner and both model files. No inference executed.", flush=True)

def evaluate(repo, runtime, out, rows):
    if os.name != "nt":
        raise ValueError("Pinned evaluator is Windows x64 only")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg required for native FLAC input")
    exe = verify_runtime(runtime)
    prompt = out/"prompt.txt"
    text = prompt_text()
    if prompt.read_text(encoding="utf-8") != text:
        raise ValueError("Frozen rubric prompt differs")
    env = dict(os.environ, GGML_BACKEND="CPU", GGML_BACKEND_PATH=str(exe.parent))
    # Do not run model in Studio or alter its settings. CPU-only process exits
    # after each arm; no persistent service, no cloud requests.
    evidence = []
    for i, row in enumerate(rows, 1):
        raw = out/f"arm-{i}.txt"
        log = out/f"arm-{i}.log"
        receipt = out/f"arm-{i}.json"
        marker = out/f"arm-{i}.attempt"
        identity = {"audio_sha256": row["audio_sha256"],
                    "prompt_sha256": nd._sha(prompt), "assets": [a[3] for a in ASSETS]}
        if receipt.exists():
            record = nd.read(receipt)
            if record.get("identity") != identity or record.get("response_sha256") != nd._sha(raw):
                raise ValueError("Retained critic evidence differs")
        else:
            if marker.exists() or raw.exists() or log.exists():
                raise ValueError("Unresolved previous critic attempt; retain logs, no automatic retry")
            marker.write_text(json.dumps(identity), encoding="utf-8")
            print(f"Evaluating retained recording {i}/{len(rows)} on CPU", flush=True)
            args = [str(exe), "--family", "moss", "--models", str(runtime),
                    "--lm", str(runtime/ASSETS[2][0]), "--src-audio", row["audio"],
                    "--mode", "prose", "--prompt-file", str(prompt), "--ffmpeg", ffmpeg,
                    "--max-seconds", "215", "--max-tokens", "1024", "--temperature", "0",
                    "--seed", "137", "-o", str(raw)]
            with log.open("xb") as stream:
                subprocess.run(args, cwd=exe.parent, env=env, stdout=stream,
                               stderr=subprocess.STDOUT, timeout=3600, check=True)
            if not raw.is_file() or not 0 < raw.stat().st_size <= 100000:
                raise ValueError("Missing or oversized critic response")
            if "using the first" in log.read_text(encoding="utf-8", errors="replace"):
                raise ValueError("Captioner truncated audio")
            if nd._sha(Path(row["audio"])) != identity["audio_sha256"]:
                raise ValueError("Source changed during critic evaluation")
            record = {"identity": identity, "response_sha256": nd._sha(raw)}
            nd.atomic_write(receipt, record)
        status, checks = parse_response(raw.read_text(encoding="utf-8", errors="replace"))
        print(f"Recording {i}: {status}; raw answer retained", flush=True)
        evidence.append({"arm": row["arm"], "format_status": status, "checks": checks,
                         "raw_response": raw.read_text(encoding="utf-8", errors="replace")})
    return evidence

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--setup", action="store_true", help="Explicitly download about 7.1 GB of pinned assets; no inference")
    modes.add_argument("--confirm-evaluation", action="store_true", help="Evaluate the existing pair on CPU only")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        runtime = repo/"results/critic-runtime"
        out = repo/"results/critic-calibration"
        lock = repo/"results/.critic-active"
        lock.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            if args.setup:
                setup(runtime)
                return 0
            rows = retained_pair(repo)
            contract = {"schema": "critic-calibration-v1", "inputs": rows,
                        "rubric": [{"id": k, "claim": v} for k,v in RUBRIC],
                        "provider": "MOSS-Music-8B-Instruct-Q4_K_M/ace-caption-v1.5.2/CPU",
                        "assets": [list(a) for a in ASSETS],
                        "generation_calls": 0, "recognition_calls": 0, "automatic_acceptance": False,
                        "warnings": ["Model claims are unvalidated, not verified listening evidence.",
                                     "Mono input cannot assess stereo mixing.",
                                     "Same-brief pair is a sanity check, not proof of general critic accuracy."]}
            out.mkdir(parents=True, exist_ok=True)
            path = out/"contract.json"
            if path.exists():
                if nd.read(path) != contract or (out/"prompt.txt").read_text(encoding="utf-8") != prompt_text():
                    raise ValueError("Retained critic contract differs")
            else:
                (out/"prompt.txt").write_text(prompt_text(), encoding="utf-8")
                nd.atomic_write(path, contract)
            if not args.confirm_evaluation:
                print("Retained pair verified. Rubric prepared. Zero inference/downloads.", flush=True)
                print("Contract:", path, flush=True)
                return 0
            evidence = evaluate(repo, runtime, out, rows)
            result = {"contract": contract, "evidence": evidence, "automatic_winner": False,
                      "artistic_acceptance": "unverified", "next_action": "review_critic_evidence"}
            nd.atomic_write(out/"report.json", result)
            print("Report:", out/"report.json", flush=True)
            # Include the actual answers in the short operator transcript.
            for item in evidence:
                print(item["arm"]+":\n"+item["raw_response"], flush=True)
            print("No song generation, ASR or Studio mutation.", flush=True)
            return 0
        finally:
            lock.unlink()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print("ERROR:", exc, file=sys.stderr, flush=True)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
