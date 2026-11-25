"""Offline diagnosis and planning, without speculative audio or score edits."""
from pathlib import Path

from .finishing_selection import select, read
from .native_recognition import _sha, _write, _recognition, review
from .phrase_rhythm import analyze
from .multilingual_fidelity import assess
from .audiobox_eval import summarize_evidence


def direct(source, lyrics, baseline_asr, language, out, *, custom=None, native=None, abc=None, quality=None):
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
    quality_evidence=summarize_evidence(quality,selection)
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
    # Separate a usable technical candidate from the next musical intervention.
    # Native-first: a file already in hand is preferable to another render.
    selected=next((row for row in selection["candidates"]
                   if row["eligible"] and row.get("path")==chosen),None)
    actions=[{"priority":1,"action":"use_existing_provisional_file" if selected else "retain_source",
              "reason":"existing_evidence","execution":"available_now",
              "method":selected["method"] if selected else "source",
              "requires_new_audio":False}]
    if baseline[primary]["edits"]:
        # Existing lyric evidence may be adequate for localization, not cause.
        # Do not trigger training, a new ASR pass or external alignment by default.
        worst=sorted((localization or {}).get("lines",[]),
                     key=lambda line:-line["edits"])
        actions.append({"priority":2,"action":"inspect_existing_native_timing",
                        "tool_candidates":["library_song_get","library_song_files"],
                        "director_command":"timing-evidence",
                        "requires_new_audio":False,
                        "execution":"requires_matching_library_song_and_existing_lrc",
                        "review_cues":[line for line in worst if line["edits"]][:5],
                        "limitation":"Display anchors are not observed phonemes; no lyric or score mutation"})
    if not selected and any(row.get("reason")=="insufficient_headroom" for row in selection["candidates"]):
        actions.append({"priority":len(actions)+1,"action":"consider_native_export_for_library_source",
                        "tool_candidates":["song_export","song_export_get"],
                        "execution":"requires_explicit_delivery_goal_and_verified_library_source",
                        "limitation":"Fixed gain only; not an export of an uncommitted external candidate",
                        "requires_new_audio":False,"requires_new_export":True})
    if any(row.get("reason")=="evidence_invalid" for row in selection["candidates"]):
        actions.append({"priority":len(actions)+1,"action":"inspect_existing_transaction",
                        "execution":"offline_evidence_recovery_only",
                        "requires_new_audio":False})
    result={"schema":"director-diagnosis-v1","native_first_actions":actions,
            "model_change_recommended":False,"training_recommended":False,
            "quality_evidence":quality_evidence,"custom_dynamics_default":False,
            "artistic_winner":None,"source_sha256":hashes[0],"lyrics_sha256":hashes[1],
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
