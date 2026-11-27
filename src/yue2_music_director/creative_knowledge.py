"""Versioned opt-in, derived-only knowledge context for creative text roles."""
import math
from . import knowledge_bank as kb

VERSION = "creative-knowledge-v1"
FIELDS = {
    "composer": ("vocal_pitch_range_semitones", "notated_measures_max_part",
                 "lyric_bearing_notes", "notated_vocal_rest_events"),
    "lyricist": ("text_words", "unique_text_words", "lexical_type_token_ratio",
                 "lyric_bearing_notes"),
}
GUIDANCE = ("Advisory numerical observations from a small historical corpus, not stylistic "
            "targets. Use only if relevant to the brief. Do not imitate or reconstruct a "
            "reference; prioritize original songwriting and the operator's requirements.")


def snapshot(database, query):
    roles = {}
    for role, keys in FIELDS.items():
        hits = kb.retrieve(database, query, role, limit=3)
        roles[role] = [{"work_id": h["work"]["work_id"],
                        "source_revision": h["work"]["source_revision"],
                        "features": {key: h["features"][key] for key in keys}} for h in hits]
    return {"schema": VERSION, "query": query, "roles": roles}


def payload(saved, role):
    if saved["schema"] != VERSION or role not in FIELDS:
        raise ValueError("Unsupported creative knowledge context")
    rows = saved["roles"][role]
    if not isinstance(rows, list) or len(rows) > 3:
        raise ValueError("Invalid knowledge context length")
    observations = []
    for row in rows:
        features = row["features"]
        if set(features) != set(FIELDS[role]):
            raise ValueError("Unexpected knowledge features")
        for value in features.values():
            if value is not None and (type(value) not in (int, float)
                                      or not math.isfinite(value) or value < 0):
                raise ValueError("Invalid numeric knowledge feature")
        observations.append(dict(features))
    return {"schema": VERSION, "guidance": GUIDANCE, "observations": observations}
