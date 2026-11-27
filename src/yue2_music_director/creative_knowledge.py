"""Versioned opt-in, derived-only knowledge context for creative text roles."""
import math
from . import knowledge_bank as kb

LEGACY_VERSION = "creative-knowledge-v1"
VERSION = "creative-knowledge-v2"
LEGACY_FIELDS = {
    "composer": ("vocal_pitch_range_semitones", "notated_measures_max_part",
                 "lyric_bearing_notes", "notated_vocal_rest_events"),
    "lyricist": ("text_words", "unique_text_words", "lexical_type_token_ratio",
                 "lyric_bearing_notes"),
}
GUIDANCE = ("Advisory numerical observations from a small historical corpus, not stylistic "
            "targets. Use only if relevant to the brief. Do not imitate or reconstruct a "
            "reference; prioritize original songwriting and the operator's requirements.")

FIELDS = {
    "composer": LEGACY_FIELDS["composer"] + (
        "melodic_step_fraction", "melodic_leap_fraction", "melodic_repeat_fraction",
        "melodic_ascending_fraction", "auto_harmony_parse_fraction",
        "auto_harmony_slash_symbol_fraction", "auto_harmony_distinct_symbol_fraction"),
    "lyricist": LEGACY_FIELDS["lyricist"] + (
        "repeated_word_trigram_fraction", "punctuation_group_count",
        "mean_words_per_punctuation_group", "repeated_punctuation_group_fraction"),
}
GUIDANCE_V2 = (GUIDANCE + " Punctuation groups are not original lyric lines, stanza boundaries, "
               "rhyme or emotional analysis. Repeated token sequences are lexical proxies, not hook quality. "
               "Melodic fractions describe consecutive notated events, not acoustic phrasing. "
               "Harmony fields describe recognized automatic RomanText annotation tokens, "
               "not verified chords, durations or cadence decisions. Null means unavailable; "
               "do not turn historical averages into mandatory targets.")


def fields_for(version):
    if version == LEGACY_VERSION:
        return LEGACY_FIELDS
    if version == VERSION:
        return FIELDS
    raise ValueError("Unsupported creative knowledge context")


def snapshot(database, query):
    roles = {}
    for role, keys in FIELDS.items():
        hits = kb.retrieve(database, query, role, limit=3)
        roles[role] = [{"work_id": h["work"]["work_id"],
                        "source_revision": h["work"]["source_revision"],
                        "source_asset_hashes": {kind: item["git_blob_sha"]
                                                for kind, item in h["work"]["assets"].items()},
                        "features": {key: h["features"][key] for key in keys}} for h in hits]
    return {"schema": VERSION, "query": query, "roles": roles}


def payload(saved, role):
    fields = fields_for(saved["schema"])
    if role not in fields:
        raise ValueError("Unsupported creative knowledge context")
    rows = saved["roles"][role]
    if not isinstance(rows, list) or len(rows) > 3:
        raise ValueError("Invalid knowledge context length")
    observations = []
    for row in rows:
        features = row["features"]
        if set(features) != set(fields[role]):
            raise ValueError("Unexpected knowledge features")
        for value in features.values():
            if value is not None and (type(value) not in (int, float)
                                      or not math.isfinite(value) or value < 0):
                raise ValueError("Invalid numeric knowledge feature")
        if saved["schema"] == VERSION and any(
                value is not None and key.endswith("_fraction") and value > 1
                for key, value in features.items()):
            raise ValueError("Invalid fractional knowledge feature")
        observations.append(dict(features))
    return {"schema": saved["schema"], "guidance": GUIDANCE if saved["schema"] == LEGACY_VERSION else GUIDANCE_V2,
            "observations": observations}
