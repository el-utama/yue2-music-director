"""Advisory post-generation judgment. No tool access or acceptance authority."""
from .creative_contracts import fields, object_schema

PROMPT = ("You are the music director reviewing a completed provisional take. Use only supplied creative intent, "
          "technical screens and unverified audio observations. Distinguish subjective interpretation from measurement. "
          "An excerpt boundary is not proof of a truncated song; ASR disagreement is not verified pronunciation. "
          "Identify strengths and a specific uncertainty or issue; never claim you listened to audio directly. "
          "Do not request or trigger more inference. Return JSON only: decision ('retain_provisional' or "
          "'review_required'), rationale and suggested_next_step strings. Do not declare artistic acceptance.")


LIMITS = {"decision":30,"rationale":2000,"suggested_next_step":1000}
SCHEMA = object_schema(LIMITS, {"decision":["retain_provisional","review_required"]})


def validate(value):
    fields(value, LIMITS)
    if value["decision"] not in ("retain_provisional","review_required"):
        raise ValueError("Unsupported director decision")
    return value


def context(request, brief, intent, report, packet):
    acoustic = report["acoustic"]
    screen = report["lyric_screen"]
    metric = screen.get("primary_metric")
    result={"request":request,"brief":brief,"intent":intent,
            "technical":{"headroom_pass":report["headroom_pass"],
                         "duration_cap_screen_pass":report["duration_cap_screen_pass"],
                         **{k:acoustic.get(k) for k in ("duration_seconds","integrated_lufs","true_peak_dbtp","lra_lu")}},
            "lyric_screen":{"metric":metric,"disagreement_rate":screen.get(metric,{}).get("disagreement_rate")},
            "observations":[{k:item[k] for k in ("start_seconds","end_seconds","contains_recording_end",
                                                  "format_status","checks")} for item in packet["observations"]]}
    if "native_completion" in report:
        result["technical"]["native_completion"]=report["native_completion"]
    if any(key in intent.get("constraints",{}) for key in ("opening","opening_timing")):
        saved=report.get("saved_score_review",{})
        metrics=saved.get("metrics") or {}
        result["score_evidence"]={"opening":metrics.get("opening"),"score_seconds":metrics.get("score_seconds"),
            "section_order":metrics.get("section_order"),"limits":"Notated opening is not acoustic vocal onset."}
        result["observation_policy"]="MOSS descriptions are advisory, not independent proof of bad arrangement or unfinished ending. Native truncation evidence and human listening have distinct roles. Never equate no fade with an incomplete song. Report disagreement as uncertainty; headroom failure is not proven clipping."
    if "opening_timing" in intent.get("constraints",{}):
        # v3 only: do not change the identity of earlier Director receipts.
        result["context_schema"]="director-context-v3"
        result["technical"].pop("lra_lu",None)
        result["technical"]["loudness_range_lu"]=acoustic.get("loudness_range_lu")
        result["score_evidence"]["opening_evidence"]=metrics.get("opening_evidence")
    if intent.get("schema")=="artist-intent-v2":
        result["context_schema"]="director-context-v4-typed"
    return result
