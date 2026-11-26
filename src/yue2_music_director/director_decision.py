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
    return {"request":request,"brief":brief,"intent":intent,
            "technical":{"headroom_pass":report["headroom_pass"],
                         "duration_cap_screen_pass":report["duration_cap_screen_pass"],
                         **{k:acoustic.get(k) for k in ("duration_seconds","integrated_lufs","true_peak_dbtp","lra_lu")}},
            "lyric_screen":{"metric":metric,"disagreement_rate":screen.get(metric,{}).get("disagreement_rate")},
            "observations":[{k:item[k] for k in ("start_seconds","end_seconds","contains_recording_end",
                                                  "format_status","checks")} for item in packet["observations"]]}
