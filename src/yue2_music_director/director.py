"""Offline diagnosis and planning, without speculative audio or score edits."""
from pathlib import Path

from .finishing_selection import select, read
from .native_recognition import _sha, _write, _recognition, review
from .phrase_rhythm import analyze
from .multilingual_fidelity import assess


def direct(source, lyrics, baseline_asr, language, out, *, custom=None, native=None, abc=None):
    source,lyrics,baseline_asr=[Path(p).resolve(strict=True) for p in (source,lyrics,baseline_asr)]
    out=Path(out).resolve()
    if out.exists():
        raise ValueError("Fresh director directory required")
    input_paths=[source,lyrics,baseline_asr]
    if abc is not None:
        abc=Path(abc).resolve(strict=True)
        input_paths.append(abc)
    hashes=[_sha(p) for p in input_paths]
    reference=lyrics.read_text(encoding="utf-8-sig")
    baseline_raw=read(baseline_asr)
    baseline=assess(reference,_recognition(baseline_raw),language)
    out.mkdir(parents=True,exist_ok=False)
    selection=select(source,lyrics,baseline_asr,language,out/"selection.json",
                     custom=custom,native=native)
    if [selection[k] for k in ("source_sha256","lyrics_sha256","baseline_asr_sha256")]!=hashes[:3]:
        raise ValueError("Selection inputs changed")
    findings=[]
    primary=baseline["primary_metric"]
    if baseline[primary]["edits"]:
        findings.append({"issue":"lyric_disagreement","evidence":"asr_text_only",
                         "metric":primary,"edits":baseline[primary]["edits"],
                         "reference_units":baseline[primary]["reference_units"],
                         "action":"phonetic_alignment_required",
                         "execution":"blocked_missing_verified_alignment"})
    localization=None
    if language=="en":
        # Same frozen ASR in both slots: no second inference. Use A only.
        mapped=review(reference,baseline_raw,baseline_raw)
        lines=[{"section":p["section"],"line_index":p["line_index"],
                "reference_words":p["reference_words"],"edits":p["A_count"]}
               for p in mapped["reference_lines"]]
        localization={"method":"minimum_word_edit_alignment","lines":lines,
                      "unassigned_boundary_insertions":len(mapped["boundary_insertions"]["A"]),
                      "audio_timestamps_verified":False}
    rhythm=None
    if abc is not None:
        if language!="en":
            rhythm={"status":"unsupported_language_for_word_density_diagnostic"}
        else:
            analyzed=analyze(abc.read_text(encoding="utf-8-sig"),reference)
            rhythm={"status":"approximate_score_only","phrases":[],
                    "warnings":analyzed["warnings"]}
            index={(p["section"],p["line_index"]):p for p in localization["lines"]}
            for p in analyzed["phrases"]:
                key=(p["section"],p["line_index"])
                if key not in index or index[key]["reference_words"]!=p["reference_words"]:
                    raise ValueError("Score and ASR reference sequence differs")
                rhythm["phrases"].append({k:p[k] for k in ("section","line_index","bar_start","bar_end",
                     "note_events","words_per_sounding_quarter","review_flags")}|{"asr_edits":index[key]["edits"]})
            if any(p["review_flags"] for p in rhythm["phrases"]):
                findings.append({"issue":"score_allocation_review_cue","evidence":"approximate_bar_partition",
                                 "action":"verify_alignment_before_score_edit","execution":"blocked_missing_verified_alignment"})
    for row in selection["candidates"]:
        if row["eligible"]:
            continue
        reason=row.get("reason")
        action=("consider_bounded_gain_only_continuation" if reason=="insufficient_headroom"
                else "reject_candidate" if reason=="asr_regression" else "verify_existing_evidence")
        findings.append({"issue":reason,"method":row["method"],"evidence":"finishing_selection",
                         "action":action,"execution":"not_submitted"})
    # No evidence here can establish actual vocal naturalness, timing, or note dynamics.
    status=selection["status"]
    chosen=selection["provisional_output"]
    result={"schema":"director-diagnosis-v1","source_sha256":hashes[0],"lyrics_sha256":hashes[1],
            "baseline_asr_sha256":hashes[2],"score_sha256":hashes[3] if abc is not None else None,
            "status":status,"provisional_output":chosen,"baseline":baseline,"findings":findings,
            "lyric_localization":localization,"score_rhythm":rhythm,
            "selection_report":str(out/"selection.json"),
            "next_action":"preserve_provisional_and_stop" if status=="provisional_candidate" else "retain_original_and_stop",
            "execution_budget":{"audio_jobs":0,"native_processing":0,"recognition":0,"score_edits":0},
            "audio_jobs_created":0,"processing_calls":0,"recognition_calls":0,"library_mutations":0,
            "automatic_acceptance":False,"naturalness_verified":False,
            "warnings":["ASR line alignment is not phonetic or time alignment; non-English line localization not supported.",
                        "No causal diagnosis of naturalness, pronunciation, or performance from these reports.",
                        "No forced correction, resubmission, or automatic final acceptance."]}
    if [_sha(p) for p in input_paths]!=hashes:
        raise ValueError("Director inputs changed")
    for row in selection["candidates"]:
        if "sha256" in row and _sha(Path(row["path"]))!=row["sha256"]:
            raise ValueError("Candidate changed after selection")
    _write(out/"report.json",result)
    return result
