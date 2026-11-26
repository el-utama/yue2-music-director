# Research handbook

Status: experimental alpha 8.post3, 2026-11-25. This handbook consolidates the accessible project record; not a verbatim archive of all conversations or older local prototypes.

## Current authoritative roadmap

The 2026-11-25 [native-first development audit](knowledge/DEVELOPMENT_AUDIT.md) supersedes the sequencing of earlier plans below. Review [Studio capabilities](knowledge/STUDIO_CAPABILITIES.md), [MCP inventory](knowledge/MCP_TOOL_INDEX.md) and [community/evaluation research](knowledge/COMMUNITY_AND_EVALUATION.md) before proposing new implementation. The installed runtime inventory was read locally; stock configuration must still be checked before a new generation. Historical experimental evidence remains valid within its original scope.

## Goal and scope

Build a local-first music director that diagnoses score, lyric, performance and audio issues, chooses supported interventions, creates bounded candidates, evaluates evidence and keeps or rejects candidates without mandatory routine manual listening. Respect the user's intended melody, hook, arrangement, lyrics and style. Never claim that a text score or successful MIDI conversion proves natural performance. Human musical preference remains separate from automatic lyric screening. ASR is the default diagnostic for languages the operator may not speak; it is fallible and does not measure phonemes or verified sung errors.

## Primary research objective: musical humanization (2026-11-26)

The Music Director exists to improve YuE2 musical naturalness and expressiveness under human creative direction, not merely to fix song defects. Correct lyrics, coherent form, natural cadence and preservation of accepted performance are prerequisites for humanization, not its complete definition. Assess vocal phrasing, pronunciation, stress, breath placement, dynamics, pitch transitions and expressive timing; instrumental articulation, groove, interaction and musical balance; and overall emotional coherence. Prefer intentional musical changes and documented human decisions over random perturbations. Preserve source audio, compare bounded candidates, and reject changes that impair lyric fidelity, artistic intent or technical quality.

Human contribution and AI generation are distinct dimensions. Record actual human-written or edited material, arrangement decisions, performance contributions, dataset rights/provenance, fine-tuning and model configuration when applicable, without claiming a numerical human-authorship share. A custom-trained model still produces AI-generated synthesis. The stock development baseline does not establish that a custom model was used. Maintain accurate AI-use disclosure and applicable platform provenance/labeling; never strip provenance or represent generated performances as human recordings.

If an independent music-AI detector is available, its reported result may be recorded as a secondary observational research metric, with detector identity, version/date, input format and frozen comparison conditions. A detector score is not a percentage of AI creative contribution, a calibrated probability unless established by that detector, a musical quality score, or evidence of human authorship. Do not optimize against a detector or select processing solely to reduce its score. No claim of reduced detection without measured evidence, and no guarantee of a particular classification. No third-party audio upload without explicit consent. Use matched, loudness-controlled blinded listening where practical, lyric fidelity and technical non-regression, human reference recordings with appropriate rights, and held-out songs distinct from training material for eventual cross-song validation. Existing stock repair, pitch, dynamics and AudioBox experiments remain scoped evidence; no repeat merely to populate a dashboard.

Research ordering: complete the current bounded lyric-conditioning experiment without automatic retries; then audit already available native expressive controls and retained A/B evidence, establish a humanization evaluation protocol, and separately evaluate compatible custom-trained models/adapters when their provenance and local configuration are verified. No training, inference, model change or detector upload is authorized by this roadmap update.

## Architecture and operating paths

| Layer | Current implementation | Evidence |
|---|---|---|
| Score | music, prosody, pipeline, expression, phrase_rhythm | Strict tested ABC subset, conservative pitch proposals; approximate phrase allocation only |
| Symbolic performance | midi, midi_events, instrument_velocity, instrument_render | Actual 663-note score audit; fixed accompaniment velocities corrected without editing timing/pitch. SoundFont path is not native generated arrangement |
| Studio gateway | mcp, experiments, job_receipt, native_recognition | Explicit loopback, bounded calls, preflight, journal before submit, no blind retries |
| Lyric evidence | lyric_fidelity, native_recognition, fidelity_gate, human_selection, multilingual_fidelity | ASR-primary text disagreement; line alignment not timestamps; basic WER/CER, not phonetic alignment |
| Audio finishing | acoustic, instrument_dynamics, finish | FFmpeg measurements, stem-delta gain, one bounded ASR check; completed real B run |
| Native effects | native_process, native_headroom | One real Naturalize preview, fixed gain continuation, ASR with matching pending run; other stages unverified |
| Candidate decisions | finishing_selection, director | Real Windows combined provisional selection with saved AudioBox evidence; no artistic winner |
| Timing evidence | temporal_evidence | Real Windows read-only partial LRC mapping through native HTTP; display anchors only |
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
- Completed real combined review, AudioBox and native timing validation. Do not repeat.
- [Native song draft](NATIVE_DRAFT.md): one bounded production path, awaiting combined live validation.
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

### Preliminary external detector observation (2026-11-26)

Operator-supplied screenshots from aimusicchecker.org/id report 73.31% AI probability for the original stock YuE2 FLAC (displayed duration 3.50 min) and 71.84% for its sample-preserving hybrid audition (3.04 min). Both are classified "Pure AI Generated" and attributed to Suno, although the actual synthesis engine was YuE2. Absolute difference -1.47 percentage points. These are single reported observations, detector version/calibration/repeatability unknown, not an independent execution by Music Director. Duration and ending material differ; the hybrid retains the incorrect repeated verse and is not an accepted lyric repair. No causal inference about naturalness, human authorship or detector performance follows from this pair. Record only as secondary evidence; do not optimize processing against the score. No audio uploaded by the agent, no extra inference or detector testing authorized. Keep unpublished assets and screenshot evidence private.
