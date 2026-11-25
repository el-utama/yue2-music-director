# Changelog and research milestones

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

| Development after alpha 8.post3 | Initial native preview adapter; explicit one-stage preview with preflight and acoustic gate, no keep/discard or ASR. Live acceptance pending. |

| Native preview screening | Optional single local ASR call after acoustic pass; exact completed preview status exemption, separate evaluation report. Live pending-preview recognition remains unverified. |

| Native preview transaction inspection | ASR readiness preflight before processing, observed run identity and input fingerprints, offline inspection of partial/completed transactions, no automatic resubmission. |

| Native headroom continuation | Real native preview capture succeeded; raw true peak -0.45 dBTP blocked ASR. Added bounded gain-only continuation from saved preview, with real FFmpeg synthetic test and mocked recognition. No repeat native effect. |

| Finishing selection | Offline comparison of completed custom and native headroom transactions; common headroom and non-regression gates, no inference. |

## Real-song evidence (2026-11-24)

A/B/C were exploratory, not replicated causal trials. Full-mix native ASR disagreements: A 23/180 (12.78%), B 44/180 (24.44%), C 56/180 (31.11%). Human preference for music and ASR ranking can disagree. B retained as an experimental baseline, not an absolute winner. Isolated vocals did not improve the B ASR result (45 vs 44 edits). Do not repeat these runs merely to recover a report.

Instrument MIDI: fixed per-track velocity; 364 velocity-only changes in accompaniment, with no pitch/timing changes. Generic SoundFont render QA is separate from native YuE2 audio, not proof of naturalness.

B finishing: 398 detected onsets, 155 edits, max attenuation 1.61 dB, reconstruction residual -24.57 dB, both stems resampled 44.1 to 48 kHz and one tail frame removed each. One additional native ASR call, zero song jobs. WER disagreement 44 to 42 edits (24.44% to 23.33%); CER 141 to 140 (19.80% to 19.66%). Candidate non-regression, not verified improvement or final acceptance. Sample peak nearly full scale; headroom needs attention. [Acceptance record](https://github.com/el-utama/yue2-music-director/issues/4#issuecomment-7137257793).

Historical evidence is based on retained experiment reports and recorded issue comments; private source artifacts are not bundled. Claims of perceptual naturalness, universal pronunciation verification, or production readiness are not supported.

Native Naturalize continuation succeeded on real audio: -0.60 dB fixed attenuation, measured -1.05 dBTP, -17.67 LUFS, same duration/rate/channels/LRA; WER 44/180 and CER 141/712 unchanged. One ASR, no additional native processing or library mutation. See Issue #4. Naturalness unverified.

- Offline director diagnosis: reuse completed finishing selection, ASR-text localization and optional approximate score cues; explicit stop decision, zero new inference or score edits. Real integrated diagnosis pending.

- Temporal evidence: audited native karaoke interpolation and added read-only existing-LRC inspection, with strict reference and duration checks. No inferred phoneme timing or correction authorization; live metadata lookup pending.
