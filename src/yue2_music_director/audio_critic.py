"""Bounded offline calibration of an audio-aware critic on the retained P5 pair."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

from . import native_draft as nd

# Exact managed paths and sizes from Studio v5.0.0, not a second installation.
STUDIO_REVISION = "bfd35a0e594cbd1268557833001d5675ebbdd2d3"
TOOLS_FOLDER = "hotstep-tools-479cbeb8-xcr0"
MODEL_FILES = (("moss-aud-f16.gguf", 1724480640), ("moss-lm-q4_k_m.gguf", 5188223648))
CPU_LIMIT = 120

# Requirements authored independently from the original demo brief. C01/C02
# are sanity controls, not targets to improve. No user listening verdict or
# route label is given to the evaluator.
RUBRIC = (
    ("R01", "A slow blues/soul ballad character."),
    ("R02", "An intimate male low-register lead vocal with restrained, conversational phrasing."),
    ("R03", "Warm piano and electric guitar responses around the vocal."),
    ("R04", "Brushed or restrained drums with a gradual increase in rhythmic support."),
    ("R05", "A contrast between quiet verses and a more expansive refrain within this excerpt."),
    ("R06", "Expressive pauses or space between vocal phrases."),
    ("R07", "A musical ending that resolves gently rather than stopping abruptly, if audible; otherwise uncertain."),
    ("C01", "The supplied excerpt contains no singing."),
    ("C02", "The excerpt has a fast, aggressive electronic dance style."),
)

def prompt_text():
    checks = "\n".join(f"{key}: {claim}" for key, claim in RUBRIC)
    return (
        "Assess only the supplied excerpt of the recording. Do not infer from the requested properties. "
        "For each ID below report supported, contradicted, or uncertain, and one short "
        "specific audible cue. Use uncertain for weak evidence or properties requiring the rest of the song. "
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

def inventory(rows):
    """Resolve the exact v5.0 managed paths from the retained library files.

    Do not scan drives, choose stale runtimes, download, or mutate Studio.
    File sizes check completeness only; hashes identify local bytes, not trust.
    """
    media = {Path(row["audio"]).resolve().parent for row in rows}
    if len(media) != 1 or next(iter(media)).name.lower() != "media":
        raise ValueError("Retained audio must share Studio's managed media directory")
    data = next(iter(media)).parent
    models = data/"training/models/moss"
    engine = data/"hotstep"/TOOLS_FOLDER
    exe = engine/"ace-caption.exe"
    entries = []
    for file, expected in [(exe, None), *((models/name, size) for name,size in MODEL_FILES)]:
        size = file.stat().st_size if file.is_file() else None
        complete = size is not None and (size > 0 if expected is None else size == expected)
        entries.append({"path": str(file), "bytes": size, "expected_bytes": expected,
                        "complete": complete})
    # Studio installs a local captioner with its runtime libraries. The exact
    # managed path is intentional; an arbitrary executable is never discovered.
    for name in ("ggml.dll", "ggml-base.dll"):
        file = engine/name
        entries.append({"path": str(file), "bytes": file.stat().st_size if file.is_file() else None,
                        "expected_bytes": None, "complete": file.is_file() and file.stat().st_size > 0})
    return {"data_root": str(data), "models": str(models), "captioner": str(exe),
            "files": entries, "ready": all(row["complete"] for row in entries),
            "studio_source_revision": STUDIO_REVISION,
            "warning": "Managed-path and size checks, not independent package authentication."}


def excerpt_ranges(seconds):
    # Cover the song in two contiguous halves, each below Studio's CPU limit.
    if not math.isfinite(seconds) or not 1 <= seconds <= 210:
        raise ValueError("Unsupported retained duration")
    midpoint = seconds/2
    return ((0.0, midpoint), (midpoint, seconds-midpoint))


def freeze_contract(repo, rows, installed):
    contract = {"schema": "critic-calibration-v2", "inputs": rows,
                "rubric": [{"id": k, "claim": v} for k,v in RUBRIC],
                "provider": "Studio-v5.0-MOSS-Q4_K_M/CPU",
                "studio_source_revision": STUDIO_REVISION,
                "cpu_limit_seconds": CPU_LIMIT,
                "generation_calls": 0, "recognition_calls": 0, "automatic_acceptance": False,
                "warnings": ["Unvalidated audio-model judgments, not listening proof.",
                             "Excerpt-local mono analysis cannot establish whole-song structure or stereo mixing.",
                             "Same-brief pair is a sanity check, not a general benchmark."]}
    out = repo/"results/critic-calibration"
    out.mkdir(parents=True, exist_ok=True)
    path = out/"contract.json"
    prompt = out/"prompt.txt"
    if path.exists():
        if nd.read(path) != contract or prompt.read_text(encoding="utf-8") != prompt_text():
            raise ValueError("Retained critic contract differs")
    else:
        if prompt.exists():
            raise ValueError("Incomplete prior critic contract; inspect before continuing")
        prompt.write_text(prompt_text(), encoding="utf-8")
        nd.atomic_write(path, contract)
    nd.atomic_write(out/"inventory.json", installed)
    return out, contract


def evaluate(out, rows, installed):
    if os.name != "nt":
        raise ValueError("Studio Windows captioner required")
    if not installed["ready"]:
        raise ValueError("Install the native Studio auto-describe listening pack first; no download initiated")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg required for bounded mono excerpts")
    exe = Path(installed["captioner"])
    models = Path(installed["models"])
    # Bind the actual installed files to this run. Do not claim this attests
    # upstream authenticity; use Studio's own installation mechanism.
    binaries = sorted({Path(row["path"]) for row in installed["files"]}
                      | set(exe.parent.glob("*.dll")))
    fingerprints = {str(p): nd._sha(p) for p in binaries}
    identity_path = out/"runtime.json"
    if identity_path.exists():
        if nd.read(identity_path) != fingerprints:
            raise ValueError("Installed runtime changed; do not mix critic evidence")
    else:
        nd.atomic_write(identity_path, fingerprints)
    env = dict(os.environ, GGML_BACKEND="CPU", CUDA_VISIBLE_DEVICES="-1",
               GGML_BACKEND_PATH=str(exe.parent))
    evidence = []
    prompt = out/"prompt.txt"
    for i,row in enumerate(rows,1):
        for j,(start, duration) in enumerate(excerpt_ranges(row["acoustic"]["duration_seconds"]),1):
            stem = f"arm-{i}-part-{j}"
            raw = out/(stem+".txt")
            log = out/(stem+".log")
            receipt = out/(stem+".json")
            marker = out/(stem+".attempt")
            wav = out/(stem+".wav")
            identity = {"audio_sha256":row["audio_sha256"], "start_seconds":start,
                        "duration_seconds":duration, "prompt_sha256":nd._sha(prompt),
                        "runtime":fingerprints}
            if receipt.exists():
                record = nd.read(receipt)
                if record.get("identity") != identity or record.get("response_sha256") != nd._sha(raw):
                    raise ValueError("Retained critic evidence differs")
            else:
                if any(p.exists() for p in (marker,raw,log,wav)):
                    raise ValueError("Unresolved previous critic attempt; retain logs, no automatic retry")
                if nd._sha(Path(row["audio"])) != row["audio_sha256"]:
                    raise ValueError("Source changed before critic evaluation")
                nd.create_journal(marker,identity)
                print(f"Recording {i}/{len(rows)}, excerpt {j}/2: CPU analysis",flush=True)
                # Explicit subprocess arguments, not the captioner's FLAC shell wrapper.
                subprocess.run([ffmpeg,"-nostdin","-v","error","-n","-ss",str(start),
                                "-i",row["audio"],"-t",str(duration),"-map","0:a:0",
                                "-ac","1","-ar","16000","-c:a","pcm_s16le",str(wav)],
                               check=True,timeout=120)
                args=[str(exe),"--family","moss","--models",str(models),
                      "--lm",str(models/MODEL_FILES[1][0]),"--src-audio",str(wav),
                      "--mode","prose","--prompt-file",str(prompt),"--max-seconds",str(CPU_LIMIT),
                      "--max-tokens","1024","--temperature","0","--rep-penalty","1.0",
                      "--freq-penalty","0.3","--seed","137","-o",str(raw)]
                with log.open("xb") as stream:
                    subprocess.run(args,cwd=exe.parent,env=env,stdout=stream,
                                   stderr=subprocess.STDOUT,timeout=3600,check=True)
                if not raw.is_file() or not 0 < raw.stat().st_size <= 100000:
                    raise ValueError("Missing or oversized critic response")
                if "using the first" in log.read_text(encoding="utf-8",errors="replace"):
                    raise ValueError("Captioner truncated excerpt")
                if nd._sha(Path(row["audio"])) != row["audio_sha256"]:
                    raise ValueError("Source changed during critic evaluation")
                nd.atomic_write(receipt,{"identity":identity,"response_sha256":nd._sha(raw),
                                        "excerpt_sha256":nd._sha(wav)})
                wav.unlink()
            status,checks = parse_response(raw.read_text(encoding="utf-8",errors="replace"))
            evidence.append({"arm":row["arm"],"start_seconds":start,"duration_seconds":duration,
                             "format_status":status,"checks":checks,
                             "raw_response":raw.read_text(encoding="utf-8",errors="replace")})
    if any(nd._sha(Path(p)) != digest for p,digest in fingerprints.items()):
        raise ValueError("Runtime changed during evaluation")
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--confirm-evaluation",action="store_true",
                        help="Use only the already-installed Studio captioner; CPU excerpts")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        lock = repo/"results/.critic-active"
        lock.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.close(fd)
        try:
            rows=retained_pair(repo)
            installed=inventory(rows)
            out,contract=freeze_contract(repo,rows,installed)
            print("Retained comparison verified. Studio v5.0 listening pack:",flush=True)
            for row in installed["files"]:
                print(("Present: " if row["complete"] else "Missing/incomplete: ")+row["path"],flush=True)
            print("Ready:",installed["ready"],flush=True)
            if not args.confirm_evaluation:
                print("Zero inference, downloads or Studio mutations.",flush=True)
                if not installed["ready"]:
                    print("If needed, install Auto-describe in Studio; do not download duplicate models.",flush=True)
                return 0
            evidence=evaluate(out,rows,installed)
            nd.atomic_write(out/"report.json",{"contract":contract,"evidence":evidence,
                           "automatic_winner":False,"artistic_acceptance":"unverified",
                           "next_action":"review_critic_evidence"})
            for item in evidence:
                print(f"{item['arm']} excerpt from {item['start_seconds']:.1f}s:\n"+item["raw_response"],flush=True)
            print("No generation, ASR, downloads or Studio mutation.",flush=True)
            return 0
        finally:
            lock.unlink()
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print("ERROR:",exc,file=sys.stderr,flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
