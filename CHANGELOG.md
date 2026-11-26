# Changelog and research milestones

## Unreleased — generation-first artistic routing and execution (P2/P3)

- Add a versioned artistic intent companion, explicit budgets, direct/reviewed/explicit routing and documented soft-flag decisions. Reuse native draft and recognition recovery, verify retained planner configuration, native MIDI and saved score/lyric conditioning.
- Add original blues-soul demo and `draft.cmd --artist-demo` / `--artist` modes; offline plan only unless confirmed. No new dependencies, private assets, or automatic retries.
- Synthetic transaction tests; real Studio execution and musical quality remain pending. No autonomous language-model composition claim. See [Artistic Run](docs/ARTISTIC_RUN.md).

## Unreleased — generation-first P1 score review

- Add an opt-in native fixed-grid parser profile for major/minor scores, native paired groups, ties and accidentals, preserving the legacy parser defaults.
- New offline `score-review` reports musical descriptors and versioned hard/soft/unknown constraints; native MIDI remains mandatory before future supplied-score rendering. No generation, edits, aesthetic grade or render authorization.
- See [Musical Review](docs/MUSICAL_REVIEW.md). Integrated routing and artistic validation remain pending.

## Unreleased — generation-first architecture (documentation only)

- Establish [architecture and phased implementation roadmap](docs/MUSIC_DIRECTOR_ARCHITECTURE.md): native composition by default, separate mandatory constraints from artistic preferences and unknowns, selective justified score guidance, independent technical/lyric/artistic evidence, bounded journaled recovery.
- Record completed explicit-score generation and ASR recovery, musical rejection, and preferred stock reference. These are feasibility and preference evidence, not a controlled proof of superior naturalness.
- P1 offline score evidence and versioned review policy is next; no new inference, runtime feature, private reference asset or dependency included.

## Unreleased — director-authored first song

- Opt-in research composition and explicit-score draft path; reuse existing journal, reference preflight and recognition, verify native score compatibility and saved conditioning.
- One full generation maximum, no model change or repair. Live synthesis and resumed ASR verified on one song; musical result rejected, naturalness improvement unverified.

## Unreleased — generation control study

- Add a bounded, journaled comparison of native score planning with and without section-order steering, before full synthesis.
- Compare structural eligibility only; no naturalness, lyric delivery, or live runtime claims until verified. Two score jobs, no full-song generation or automatic repair.
- See [study protocol](docs/GENERATION_CONTROL_STUDY.md).

This is a retrospective index, not a complete record of every historical prototype. Git history and [research issue #4](https://github.com/el-utama/yue2-music-director/issues/4) preserve the underlying decisions. Private artifacts stay on the operator's machine.

| Milestone | Changes / evidence |
|---|---|
| v0.1 / v0.5.x | Earlier standalone prototypes; not imported byte for byte. |
| v0.6 / v0.6.1 | Local-first toolkit, strict ABC, conservative pitch screening, MIDI audit and journaled A/B. Real frozen score: 114 bars, 663 notes, nine vocal pitch edits, no timing/velocity edits. |
| v0.7 alpha 1–3 | Expression preview, phrase rhythm diagnostics, acoustic comparison. [PR #6](https://github.com/el-utama/yue2-music-director/pull/6), [#7](https://github.com/el-utama/yue2-music-director/pull/7), [#8](https://github.com/el-utama/yue2-music-director/pull/8). |
| alpha 4 / post1 | Native recognition and line-level ASR review; terminal stem busy-state fix (#9–10). |
| alpha 5–6 | Fidelity gate and optional native syllable counts (#11–12). |
| alpha 7 | ASR-primary evidence policy (#13), deterministic instrument MIDI velocity (#14), offline render QA (#15). |
| alpha 8 | Bounded stem-delta dynamics (#16); integrated finishing, multilingual text screen (#17). |
| alpha 8.post1 | Embedded FLAC artwork compatibility (#18). |
| alpha 8.post2 | 44.1/48 kHz stem reconciliation (#19). |
| alpha 8.post3 | Adaptive reconstruction budget (#20); CI 200 passed, real existing-song finishing completed. |
| Development after alpha 8.post3 | Initial native preview adapter; explicit one-stage preview with preflight and acoustic gate, no keep/discard or ASR. Initial historical milestone; subsequently validated on one song. |
| Native preview screening | Optional single local ASR call after acoustic pass; exact completed preview status exemption, separate evaluation report. Initial historical milestone; subsequently validated through headroom continuation. |
| Native preview transaction inspection | ASR readiness preflight before processing, observed run identity and input fingerprints, offline inspection of partial/completed transactions, no automatic resubmission. |
| Native headroom continuation | Real native preview capture succeeded; raw true peak -0.45 dBTP blocked ASR. Added bounded gain-only continuation from saved preview, with real FFmpeg synthetic test and mocked recognition. No repeat native effect. |
| Finishing selection | Offline comparison of completed custom and native headroom transactions; common headroom and non-regression gates, no inference. |

## Real-song evidence (2026-11-24)

A/B/C were exploratory, not replicated causal trials. Full-mix native ASR disagreements: A 23/180 (12.78%), B 44/180 (24.44%), C 56/180 (31.11%). Human preference for music and ASR ranking can disagree. B retained as an experimental baseline, not an absolute winner. Isolated vocals did not improve the B ASR result (45 vs 44 edits). Do not repeat these runs merely to recover a report.

Instrument MIDI: fixed per-track velocity; 364 velocity-only changes in accompaniment, with no pitch/timing changes. Generic SoundFont render QA is separate from native YuE2 audio, not proof of naturalness.

B finishing: 398 detected onsets, 155 edits, max attenuation 1.61 dB, reconstruction residual -24.57 dB, both stems resampled 44.1 to 48 kHz and one tail frame removed each. One additional native ASR call, zero song jobs. WER disagreement 44 to 42 edits (24.44% to 23.33%); CER 141 to 140 (19.80% to 19.66%). Candidate non-regression, not verified improvement or final acceptance. Sample peak nearly full scale; headroom needs attention. [Acceptance record](https://github.com/el-utama/yue2-music-director/issues/4#issuecomment-7137257793).

Historical evidence is based on retained experiment reports and recorded issue comments; private source artifacts are not bundled. Claims of perceptual naturalness, universal pronunciation verification, or production readiness are not supported.

Native Naturalize continuation succeeded on real audio: -0.60 dB fixed attenuation, measured -1.05 dBTP, -17.67 LUFS, same duration/rate/channels/LRA; WER 44/180 and CER 141/712 unchanged. One ASR, no additional native processing or library mutation. See [real native acceptance record](https://github.com/el-utama/yue2-music-director/issues/4#issuecomment-7147681438). Naturalness unverified.

- Offline director diagnosis: reuse completed finishing selection, ASR-text localization and optional approximate score cues; explicit stop decision, zero new inference or score edits. Real integrated diagnosis pending.

- Temporal evidence: audited native karaoke interpolation and added read-only existing-LRC inspection, with strict reference and duration checks. No inferred phoneme timing or correction authorization; live metadata lookup pending.

- Optional alignment backend: compare SOFA, HubertFA, SoulX and mVocalToolkit; add loopback read-only backend discovery, no automatic downloads or alignment. Runtime/model/license validation remains open.

- Alignment benchmark: offline HTK sequence and boundary-error metrics; upstream engine license discrepancy and release-language ambiguity recorded. Checkpoint rights, digest, runtime/VRAM and real-song accuracy remain unverified.

- Alignment reference preparation: sample-accurate PCM WAV excerpt and explicit seconds/HTK annotation conversion, source fingerprints, no inference. Documented NUS-48E, GTSinger and PJS reference candidates and restrictions; no dataset or checkpoint bundled.

- Native LoRA audit: discovered optional MMS forced-alignment training stage, base-matched presets disable timing, and separate composition/sound adapter strengths. Native alignment reuse now takes research priority over optional external checkpoint; no training or downloads performed.

- Native-first knowledge audit: indexed 339 static MCP definitions at upstream ca37d2d; consolidated UI/engine/native workflows, official YuE2 agent skill and evaluation protocols, public adapters/fine-tunes, native export and training/voice-conversion reuse. Superseded alignment-first implementation sequence with evidence-gated roadmap. README includes Indonesian overview; all new knowledge docs in English. Source audit only; no runtime installs, generation, ASR or training.

- Added read-only local Studio profile inventory, advertised schema fingerprints, private observations and partial/unknown states. No automatic model switches, inference, or compatibility authorization. Live validation pending.

- Studio profile real local run: 339 advertised tools, 12/13 reads successful, zero operation counters. Fix LoRA inventory to request concise catalog and reject incomplete/truncated results. Live verification of the fix pending.

- Public LoRA research: real concise inventory read succeeded; indexed all 39 public native catalog entries and examined external candidates, stock/RS base mismatch, KTO stage-specific evidence, prosody conditioning and license distinctions. No downloads, training, rendering or model changes. Compatibility gate remains pending.

- Controlled reference A/B now explicitly disables optional adapters and decoder companion, validates live stock Balanced CUDA/Q8 setup and idle state before submit, and fingerprints effective configuration across arms. Old manifests are not eligible for new submission; retained historical evidence remains usable. Regression fixtures only; local gate validation pending.

- Director diagnosis: support screened direct native previews as well as headroom continuations; rank existing provisional output and native timing/export routes ahead of new inference. Regression test uses real preview/recognition writer functions with mocked Studio and acoustic measurements. Real combined retained-song validation remains pending.

- Optional offline AudioBox evaluator path uses the official predictor, pinned verified safetensors, CPU-only local scoring and separate CE/CU/PC/PQ evidence. No automatic acceptance. SongEval/MuQ and SongBench usage restrictions documented. Actual checkpoint inference remains unverified.

- Retained review, AudioBox inference and native HTTP partial timing succeeded on Windows. No artistic winner or phonetic verification. Optional independent phone observation is research only. Added native single-brief draft workflow with one authorized generation and recognition, durable journal and technical QA; actual combined production validation pending.
