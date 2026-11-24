# Expression Engine v0.7 — alpha 1

## Baseline decision (2026-11-24)

Use the frozen v0.6.1 B candidate as the provisional working baseline; retain A and the existing A/B journals/audio privately. The user listened to approximately the first minute and preferred B in six of seven categories (naturalness, lyric clarity, melody/phrasing, emotion, arrangement, overall); cleanliness tied. They heard extra unintended words and excessively rapid delivery in A. Full-song listening, blind/level-matched conditions, per-edit listening and causal attribution are not established. The previous MIDI acceptance remains valid. Do not rerender or revalidate the old pair.

## Offline commands

Run from an editable installation. Supply the existing v0.6.1 candidate ABC and the same private lyrics, not the original A.

```powershell
yue2-director expression local/baseline_B.abc --lyrics local/lyrics.txt --out results/expression-001 --max-edits 4
```

Use a fresh output directory. Repeat `--protect-bar N` for one-based bars that must remain intact. No random seed is needed: ranking is deterministic. `--max-edits 0` provides a diagnostic-only report. A no-safe-edits result creates a report but no duplicate ABC. Input is never overwritten, no MCP calls or audio jobs occur. Report contains approximate phrase diagnostics, proposed notes/intervals/chord-at-onset, guard counters and text hashes (UTF-8 decoded text, not raw-file fingerprints). Keep the report private because it includes lyric lines.

### Implemented constraints

- Only isolated contiguous three-note plateaus within a vocal bar; no bar-edge notes, long repeated runs, ties, explicit accidentals or accidental-bearing bars.
- Only verse/pre-chorus/bridge, with user-protected bars, approximate lyric-line bar-group edges and section range extrema excluded.
- Use the active annotated chord at onset, fail closed for unknown chord, stay strictly inside the existing section pitch range, shift at most three semitones.
- Rank smaller pitch shifts, shorter duration, then stable score position; avoid using the same newly proposed signed interval pair twice, adjacent edited bars, or multiple edits per approximate lyric line.
- Reparse and compare all event structure, meter/header, chord annotations, ties and untouched raw/pitch events; only planned vocal pitch changes may differ.
- These are conservative heuristic proxies, not a model of semantic intent. They can yield zero proposals, especially on an already humanized score. Never relax guards just to fill a quota.

### Lyric fidelity (human-reviewed transcript, not ASR)

```powershell
yue2-director lyric-compare --lyrics local/lyrics.txt --transcript local/sung_B.txt --out results/lyric_B.json
```

Provide a plain text transcript of the sung words, including unintended repetitions/insertions. Reference and transcript must cover exactly the same scope; for the first minute only, make a separate reference excerpt with its bracketed section markers. Do not compare a one-minute transcript to full-song lyrics. The reference uses bracketed section labels, which are stripped; the transcript must not include section headings or timestamps. Case/punctuation normalization and Unicode word tokens; standard minimum edit distance with a deterministic tie break, counting insertions, deletions, substitutions and word error rate. This is not phonetic assessment, ASR, or syllable timing analysis. It must not be used to score transcript accuracy if the transcript itself is unreliable. Reports contain private words and must stay local.

## Remaining gates

- CI for synthetic guard tests and legacy regression tests; no GPU/Studio in CI.
- Run the new planner on B only after review; no automatic candidate submission. If proposals are accepted, perform targeted symbolic checks on the new candidate, not the previously accepted pair.
- Full-song listening of existing pair, level matching and focused assessment of edited sections; do not confuse user's initial preference with a completed acceptance gate.
- Future: human-reviewed or independently validated timestamped transcript alignment, phrase duration / rushed delivery diagnostics against intended lyrics, confidence-aware syllable alignment, acoustic analysis and backend capability validation. No timing/velocity/vibrato controls are claimed in alpha 1. Do not add unsupported song_create fields or automatically submit.
- v0.7 release requires evidence from new changes and a deliberate audio acceptance decision. Alpha 1 is an opt-in score preview only.
