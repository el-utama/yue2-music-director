"""Transparent descriptive craft metrics, not a musical quality score."""
from collections import Counter
import re


def ratio(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def repeated_occurrence_fraction(items):
    counts = Counter(items)
    return ratio(sum(n for n in counts.values() if n > 1), len(items))


def lyric_features(text):
    # Score-extracted text is not a reliable stanza/line transcription.
    # Punctuation groups and repeated token sequences are textual proxies.
    tokens = re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.casefold())
    trigrams = list(zip(tokens, tokens[1:], tokens[2:]))
    groups = []
    for chunk in re.split(r"[.!?;:,]+|\n+", text.casefold()):
        words = re.findall(r"[^\W_]+(?:['’][^\W_]+)*", chunk)
        if words:
            groups.append(tuple(words))
    return {
        "repeated_word_trigram_fraction": repeated_occurrence_fraction(trigrams),
        "punctuation_group_count": len(groups),
        "mean_words_per_punctuation_group": ratio(sum(map(len, groups)), len(groups)),
        "repeated_punctuation_group_fraction": repeated_occurrence_fraction(groups),
    }


def melody_features(intervals):
    total = sum(intervals.get(k, 0) for k in ("repeat", "step", "leap"))
    return {
        "melodic_step_fraction": ratio(intervals.get("step", 0), total),
        "melodic_leap_fraction": ratio(intervals.get("leap", 0), total),
        "melodic_repeat_fraction": ratio(intervals.get("repeat", 0), total),
        "melodic_ascending_fraction": ratio(intervals.get("ascending", 0), total),
    }


# Recognize a conservative subset of RomanText chord symbols. Unknown
# notation is counted as unparsed, rather than silently asserting harmony.
CHORD = re.compile(r"^(?:[b#-]*[ivIV]+[oø+°]?[0-9]*(?:/[b#-]*[ivIV]+[oø+°]?[0-9]*)*|(?:Ger|Fr|It|Sw)[+o]?[0-9]*|N[0-9]*)$")
MEASURE = re.compile(r"^m\d+[a-z]?(?:-m?\d+[a-z]?)?$")
BEAT = re.compile(r"^b\d+(?:\.\d+)?$")
KEY = re.compile(r"^[A-Ga-g][b#-]*:$")


def harmony_features(text):
    chords = []
    unknown = 0
    for line in text.splitlines():
        tokens = line.split()
        if not tokens or not MEASURE.fullmatch(tokens[0]):
            continue
        for token in tokens[1:]:
            if BEAT.fullmatch(token) or KEY.fullmatch(token):
                continue
            if CHORD.fullmatch(token):
                chords.append(token)
            else:
                unknown += 1
    # These are automatic annotation token counts, not measured chord
    # durations or reliable harmonic functions/cadence identification.
    return {
        "auto_harmony_recognized_tokens": len(chords),
        "auto_harmony_parse_fraction": ratio(len(chords), len(chords) + unknown),
        "auto_harmony_slash_symbol_fraction": ratio(sum("/" in x for x in chords), len(chords)),
        "auto_harmony_distinct_symbol_fraction": ratio(len(set(chords)), len(chords)),
    }
