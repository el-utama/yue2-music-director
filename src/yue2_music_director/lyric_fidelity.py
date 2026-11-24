"""Compare a human-reviewed sung transcript with the intended lyric text."""
import re
import unicodedata
from .prosody import parse_lyrics

def _tokens(text):
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*", text, flags=re.UNICODE)

def compare_lyrics(lyrics: str, transcript: str) -> dict:
    """Minimum word edit distance; no ASR, timing or acoustic inference."""
    expected = _tokens(" ".join(line for s in parse_lyrics(lyrics) for line in s["lines"]))
    observed = _tokens(transcript)
    n, m = len(expected), len(observed)
    if not n or not m:
        raise ValueError("reference and reviewed transcript must contain words")
    if max(n, m) > 2000:
        raise ValueError("compare at most 2000 words per input; split long songs")
    # 0 diagonal, 1 delete reference, 2 insert observed. Ties favor diagonal.
    trace = [bytearray(m + 1) for _ in range(n + 1)]
    trace[0][1:] = bytes([2]) * m
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        row = [i] + [0] * m
        trace[i][0] = 1
        for j in range(1, m + 1):
            choices = (prev[j-1] + (expected[i-1] != observed[j-1]),
                       prev[j] + 1, row[j-1] + 1)
            direction = min(range(3), key=choices.__getitem__)
            row[j] = choices[direction]
            trace[i][j] = direction
        prev = row
    counts = {"insertions": 0, "deletions": 0, "substitutions": 0}
    edits = []
    i, j = n, m
    while i or j:
        direction = trace[i][j]
        if direction == 0:
            if expected[i-1] != observed[j-1]:
                counts["substitutions"] += 1
                edits.append({"kind": "substitution", "reference_index": i,
                              "expected": expected[i-1], "observed": observed[j-1]})
            i -= 1
            j -= 1
        elif direction == 1:
            counts["deletions"] += 1
            edits.append({"kind": "deletion", "reference_index": i,
                          "expected": expected[i-1]})
            i -= 1
        else:
            counts["insertions"] += 1
            edits.append({"kind": "insertion", "after_reference_index": i,
                          "observed": observed[j-1]})
            j -= 1
    return {"reference_words": n, "transcript_words": m, **counts,
            "word_error_rate": prev[m] / n, "edits": edits[::-1],
            "warnings": ["Requires a complete human-reviewed transcript for the same scope.",
                         "Transcript accuracy is not independently verified.",
                         "Word errors do not measure pronunciation, stress or rhythm."]}
