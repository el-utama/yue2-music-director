# v0.7 alpha 2: phrase rhythm diagnostics

Alpha 1 real-score result: frozen B produced zero eligible options and zero edits; no audio jobs, unchanged pitch repetition. This is safe abstention within a narrow heuristic, not proof of optimal expression. Keep B as provisional working baseline. Do not change or rerender the accepted A/B pair.

```powershell
py -3 -m yue2_music_director.cli phrase-rhythm local/baseline_B.abc --lyrics local/lyrics.txt --out results/phrase_rhythm.json
```

The report lists approximate lyric-line bar allocations, note events, allocated/sounding/nonsounding quarter-note units, reference word counts and density (words per sounding quarter note). These are score proxies, not real sung duration or syllable alignment. Rests include silent multirest bars. Empty allocations and zero sounding time are explicit. Review dense lines; there is no universal rushed-delivery threshold.

Optional: use existing A/B FLACs, mark start/end times independently for the same intended line in both recordings. Use exact section occurrence and one-based lyric line index from the score report. Example (fictional times and words):

```json
[
  {
    "section": "verse#1", "line_index": 1,
    "A": {"start": 12.1, "end": 13.8, "transcript": "I sing sing tonight"},
    "B": {"start": 11.9, "end": 14.2, "transcript": "I sing tonight"}
  }
]
```

Omit transcript if unreviewed; empty string means reviewed silence/no words. Times in seconds must be finite, positive-duration, non-overlapping within each arm and follow lyric order. Validate times against actual local audio duration yourself; the command does not open audio. Partial coverage is allowed and explicitly counted. Do not assume score bar position corresponds to audio timestamp. Only compare matching intended lines. Keep reference, transcript, timing JSON and report private.

Run with `--timings local/reviewed_pairs.json` and a new output path. The report includes A/B durations, reference-word rate, optional observed-word rate and edit-distance counts, and B/A duration ratio. These are annotation-derived measurements, not automatic transcription, forced alignment, pronunciation scoring or causal attribution. The CLI is read-only with respect to score/lyrics/timings and creates no audio jobs; it refuses overwriting output. Timing and pitch editing remain disabled in this command.
