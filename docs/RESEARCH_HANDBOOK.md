# Research handbook

Status: experimental alpha 8.post3, 2026-11-25. This handbook consolidates the accessible project record; not a verbatim archive of all conversations or older local prototypes.

## Goal and scope

Build a local-first music director that diagnoses score, lyric, performance and audio issues, chooses supported interventions, creates bounded candidates, evaluates evidence and keeps or rejects candidates without mandatory routine manual listening. Respect the user's intended melody, hook, arrangement, lyrics and style. Never claim that a text score or successful MIDI conversion proves natural performance. Human musical preference remains separate from automatic lyric screening. ASR is the default diagnostic for languages the operator may not speak; it is fallible and does not measure phonemes or verified sung errors.

## Architecture and operating paths

| Layer | Current implementation | Evidence |
|---|---|---|
| Score | music, prosody, pipeline, expression, phrase_rhythm | Strict tested ABC subset, conservative pitch proposals; approximate phrase allocation only |
| Symbolic performance | midi, midi_events, instrument_velocity, instrument_render | Actual 663-note score audit; fixed accompaniment velocities corrected without editing timing/pitch. SoundFont path is not native generated arrangement |
| Studio gateway | mcp, experiments, job_receipt, native_recognition | Explicit loopback, bounded calls, preflight, journal before submit, no blind retries |
| Lyric evidence | lyric_fidelity, native_recognition, fidelity_gate, human_selection, multilingual_fidelity | ASR-primary text disagreement; line alignment not timestamps; basic WER/CER, not phonetic alignment |
| Audio finishing | acoustic, instrument_dynamics, finish | FFmpeg measurements, stem-delta gain, one bounded ASR check; completed real B run |
| Native effects | native_process, native_headroom | One real Naturalize preview, fixed gain continuation, ASR with matching pending run; other stages unverified |
| Candidate decisions | finishing_selection, director | Fixture-tested offline provisional selection, diagnosis and stop policy; combined real-song run pending |
| Timing evidence | temporal_evidence | Fixture-tested read-only LRC inspection; interpolation uncertainty; live lookup pending |
| Optional alignment | alignment_backend | Discovery only; external runtime/model/license/accuracy unvalidated |

### Entry points

Use `py -3 -m yue2_music_director.cli --help` and each subcommand's `--help` for the authoritative interface. `run` prepares score/AB artifacts without audio generation, optionally MIDI. `audit`, `humanize`, `expression`, `phrase-rhythm` are score-side. `midi-probe`, `midi-audit`, `instrument-velocity`, `instrument-render-qa` are symbolic/rendered accompaniment. `ab-prepare`, `ab-submit`, `ab-status`, `ab-recover` manage deliberate experiments. `native-recognise`, `asr-review`, `lyric-compare`, `multilingual-score`, `fidelity-audit`, `human-select` address distinct evidence scopes; legacy human observation workflows are optional for routine ASR-led evaluation. `acoustic-compare`, `instrument-dynamics`, `finish-existing` operate on finished audio. `studio-check` is read-only. `native-process-preview` defaults to read-only preflight; explicit confirmation enables a single bounded native preview. `native-process-continue` reuses a captured peak-only blocked preview; `native-process-inspect` inspects journals offline. `finishing-select` and `director-diagnose` use existing reports without inference. `timing-evidence` reads existing LRC metadata. `alignment-preflight` discovers an optional local aligner without installation.

## Evidence and acceptance

Read [changelog](../CHANGELOG.md) and [Issue #4](https://github.com/el-utama/yue2-music-director/issues/4). Keep frozen inputs and journals locally. CI proves software behavior on fixtures, not real inference or musical quality. Linux runs FFmpeg integration tests; Windows can skip them if tools are absent. Real B finishing passed the current technical guards and ASR non-regression but is not a validated naturalness improvement. Do not repeatedly recreate A/B/C, resplit stems or ask for routine listening. A is still the lowest observed ASR-disagreement comparator. Custom audio finishing may leave inadequate peak headroom. Real native continuation measured -1.05 dBTP and unchanged WER/CER. No universal ASR/phoneme coverage.

## Design decisions

1. Prefer native capabilities over duplicating effects. The pinned upstream source revision ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25 is the reference for previous audits, not a claim about the installed version. Discover local tools/schema before integration.
2. Native Naturalize operates on vocal-associated bands of the full mix; it includes amplitude modulation, spectral variation, metallic attenuation and smoothing, not note-level pitch or lyric correction. Spectral Lifter already has percussive/spectral dynamics. Custom stem-delta is a separate experiment, not proven superior.
3. Native backing_song_id requires a matching Chord Bed; generating vocals can rewrite melody. Do not substitute generic MIDI/SoundFont accompaniment for the original arrangement.
4. Keep mix as base, only apply bounded instrumental delta. Resample stems only, preserve source frames, allow bounded tail rounding, reject gross reconstruction mismatch. Residual proxy is not a leakage guarantee.
5. Use ASR as a diagnostic, not a ground truth transcript. Explicit language metric; no unsupported language ranking. No forced regeneration solely on an ASR score.
6. One candidate and explicit resource budget at a time. No blind retries; on ambiguous submission preserve receipt and stop. No overwrite, source mutations, changes to installed model/global settings, or remote service calls. Never expose personal data in public repo.

## Roadmap and exit criteria

- Native Process Audio: one Naturalize preview and continuation verified locally; preserve its evidence. Other effects and installed versions remain unverified. No automatic keep/discard until ownership and semantics are verified.
- Validate combined offline director diagnosis on existing evidence without repeating inference.
- Improve provenance and calibrated signal metrics; explicitly distinguish technical pass, lyric non-regression and unverified musical outcome.
- Verified phoneme/time alignment and safe correction planner; no guessed mapping or invented model controls.
- Unified local agent orchestration: budgeted, resumable decisions across score, generation, recognition, finishing; stop when blocked, no loop of repeated user manual checks.
- Production release requires real local end-to-end evidence across multiple songs, languages and failure cases; no release claim on synthetic CI alone.

## Documentation rule

For each new PR, update the applicable command guide, changelog, status/limitations, regression test and evidence record. Retain negative results. Separate observed facts from hypotheses. Do not publish private lyrics, ABC, audio, job IDs, source hashes, manifests, journals, local paths/endpoints, model weights or credentials. Older prototypes not in this repo remain a historical gap; avoid reconstructing missing artifacts as facts.


Native preview development: optional ASR and read-only `native-process-inspect` are implemented; preserve interrupted journals. Inspection never submits or resumes work.


Native Naturalize preview retrieval has now been verified on one real song (same duration/rate/channels); headroom gate stopped ASR. Gain-only continuation reuses captured preview rather than rerendering the native effect. The subsequent continuation completed native ASR successfully (see below).

Real native continuation and ASR with matching pending preview succeeded. See [offline finishing selection](FINISHING_SELECTION.md) for evidence-based provisional ranking; not a final quality or naturalness decision.

[Offline director diagnosis](DIRECTOR_DIAGNOSIS.md) consolidates selection, text disagreement localization and optional score-rhythm cues into one report and bounded stop decision. Phonetic alignment and autonomous correction execution remain open. Real integrated diagnosis not yet verified.

[Temporal evidence](TEMPORAL_EVIDENCE.md): native karaoke timing is partly interpolated. Read existing metadata only and keep display anchors separate from measured phonetic evidence. Phonetic/temporal correction remains blocked pending suitable raw timing contract.

[Optional singing alignment backend](ALIGNMENT_BACKEND.md): mVocalToolkit + HubertFA research preference with bounded read-only preflight. Model-specific language support, provenance, license, accuracy and runtime are not yet validated. No new model downloads or audio inference.

Alignment research: [pinned candidate audit and offline benchmark](ALIGNMENT_BACKEND.md) document the exact source revision, catalog/engine license discrepancy and HTK boundary metrics. No automatic model installation or verified phonetic correction. Real annotated benchmark pending.

Alignment evaluation now includes bounded reference-excerpt preparation from preannotated PCM WAV, with explicit label units and source fingerprints. Public research corpus candidates avoid repeated operator listening; rights and train/test independence must be checked. Real model benchmark remains pending.

Native LoRA capability discovered: [training and MMS alignment audit](NATIVE_LORA_TRAINING.md). Investigate native alignment output before external backend installation; training is a separate possible cross-song improvement path, not frozen-audio correction. No training or alignment inference validated.
