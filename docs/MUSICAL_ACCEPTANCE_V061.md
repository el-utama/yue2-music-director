# Musical acceptance: v0.6.1 -> v0.7

Status: protocol ready; musical and audio outcomes pending local evaluation.
Tracking: [Issue #4](https://github.com/el-utama/yue2-music-director/issues/4).

## Frozen baseline

The real-score v0.6.1 MIDI acceptance already passed. Preserve the accepted original/candidate pair (114 bars, 663 notes, four tracks, nine vocal pitch changes, no timing/velocity/instrument changes). Do not regenerate, re-run MIDI conversion or re-audit MIDI as part of this listening phase. Three deferred changes remain deferred. The historical three-edit audio experiment is not evidence about the current nine-edit pair.

## Gate M1: musical review (no Studio calls)

Read the existing local `score_report.json`. Inspect `humanization.changes`, `humanization.deferred_changes`, `diagnostics`, and warnings. For every accepted edit record the bar/section, before/after pitch, chord function, incoming/outgoing interval and melodic contour, phrase purpose, and likely lyric-stress concern. Review bar 52 explicitly. Check chord at the actual note onset where possible; the current heuristic uses the first annotated chord in a bar. Approximate lyric line allocation is not note/syllable alignment. If the score or lyric evidence is insufficient, mark uncertain, not pass. Do not change the frozen candidate silently; if it is unsuitable, retain it as a rejected baseline and create a distinct later candidate.

## Gate M2: controlled audio (local Studio only)

Reuse the existing run's `ab/manifest.json` and request files, not a new manifest, if the input hashes match the frozen pair. Check both request files match except for ABC, seed and lm_seed are identical, and lyric timing is enabled. Confirm Studio is idle and settings/model versions are unchanged. Existing source/request fingerprints are checked by the submit command. Keep all data local.

Run only after M1 is reviewed and the user deliberately approves resource use. In the local checkout, set PowerShell variables `$ab` to the existing run's ab directory and `$url` to the local MCP endpoint. Inspect existing journals before doing anything.

```powershell
Get-ChildItem -LiteralPath $ab -Filter 'journal_*.json'
py -3 -m yue2_music_director.cli studio-check --url $url
# Only if Studio is idle AND no journal for A exists:
py -3 -m yue2_music_director.cli ab-submit --arm A --out $ab --url $url --confirm-idle
py -3 -m yue2_music_director.cli ab-status --arm A --out $ab --url $url
# After personally verifying A completed successfully and its audio is saved:
py -3 -m yue2_music_director.cli ab-recover --arm A --out $ab --confirm-complete
# Only if Studio is idle AND no journal for B exists:
py -3 -m yue2_music_director.cli ab-submit --arm B --out $ab --url $url --confirm-idle --confirm-a-complete
py -3 -m yue2_music_director.cli ab-status --arm B --out $ab --url $url
# After personally verifying B completed successfully and its audio is saved:
py -3 -m yue2_music_director.cli ab-recover --arm B --out $ab --confirm-complete
```

No retries on uncertain submission; inspect Studio and reconcile only verified completion of the corresponding job. Never delete a journal to bypass a submission lock. If an existing journal is present, inspect/status it instead of submitting. Do not reuse old three-edit arm audio. Do not upload private scores, lyrics, audio, manifests, journals or endpoints to the public repository.

## Gate M3: listening and decision

Use local lossless renders, level-matched for playback (preserve originals). Randomize/obscure arm identity; compare entire song, then edited phrases, then protected chorus and instruments. Locate phrases from actual audio/lyric timing, not bar numbers converted to guessed timestamps. Record timestamps locally. Rate both arms 1–5 (1 poor, 3 acceptable, 5 excellent) for:

| Criterion | What to listen for |
|---|---|
| Vocal prosody | Syllable clarity, stress, intelligibility |
| Melody/contour | Direction, interval naturalness, phrase resolution |
| Expressiveness | Intentional dynamics, emotional delivery, phrasing |
| Harmonic fit | Tension/release, clashes |
| Artifacts | Breaks, slurs, glitches, unintended changes (5 = clean) |
| Hook/arrangement | Chorus identity, accompaniment consistency |

Record per-edit preference A/B/tie/uncertain plus rationale; explicitly review bar 52. Decide before unblinding: prefer B only if vocal prosody and melodic contour do not regress, meaningful expression or melodic benefit is heard, and no critical artifact or hook regression is found. Prefer A if B regresses on critical criteria; otherwise inconclusive. A single matched-seed pair is exploratory, not causal proof: Studio inference can vary even with the same seed. Do not launch replication automatically. Report only aggregate non-private findings on Issue #4.

## v0.7 Expression Engine — proposed design, not implemented

Proceed after documenting M1–M3 outcomes, including a negative or inconclusive result. Use the preferred baseline; retain all original and candidate artifacts. Design from observed weaknesses rather than maximizing edit count.

- E1: read-only phrase/contour diagnostics with evidence and uncertainty; no arbitrary syllable mapping.
- E2: ranked, explainable vocal pitch proposals with local chord-at-onset, melodic anchors, range, interval and conservative rejection rules. Preserve hook, instruments, score structure and ties. Separate candidate output; deterministic seed; no forced edit quota.
- E3: explicit lyric-to-note alignment representation (provenance and confidence); no timing changes before reliable alignment and notation/backend capability are demonstrated.
- E4: expression capability research (velocity, articulation, microtiming, vibrato, dynamics); distinguish ABC/MIDI capability from actual YuE2 audio control. No invented song_create fields. Enable only demonstrated controls, separately opt-in, with bounded changes and independent audits.
- E5: offline synthetic unit tests, regression coverage, no network/GPU by default; then deliberate real-score verification only for new changes. Audio A/B must isolate each new supported expression intervention and preserve the frozen v0.6.1 control.

Do not release v0.7 or call the engine production-ready on the basis of MIDI or synthetic tests alone.
