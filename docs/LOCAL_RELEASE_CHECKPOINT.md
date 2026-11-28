# Local music production and release checkpoint — 2026-11-27

Scope: high-impact autonomous handover findings, the non-destructive
Audio Finishing Specialist, and bounded local release preparation. Existing
reference music, provider configuration, native jobs and earlier experiments
are not replayed. This is an engineering checkpoint, not a live mastering
or release-quality certification.

| Audit | Current implementation | Evidence / boundary |
|---|---|---|
| A01 | Validate stage semantics before successful receipt; explicit one retry | PR 88; old invalid success receipts are not silently migrated |
| A02 | Versioned score-clock opening evidence and first-vocal/Ins onset | PR 89; uncertain accompaniment stops mandatory gate, no acoustic claim |
| A03 | Match active native library audio before/after timing read | PR 90; matching hash and stable snapshot do not prove acoustic anchors |
| A04 | Append-only local human feedback and exact-source approvals | PRs 92, 97; original and candidate records distinct |
| A05 | Shared retained root/continuation source | PR 91; preserve bytes and historical score evidence |
| A06 | Completed-source reads use frozen receipts; active retries retain exact policy | PRs 91, 96; no blind migration of incomplete legacy jobs |
| A07 | Actual loudness range in versioned Director context | PR 89 |
| A08 | Creative, native and listening lineage independent of cover/export role | PR 91 |
| A09 | Stable release ID, portable names and explicit snapshot revisions | PR 94 |
| A10 | Expected timing failures become partial; write failures stop | PR 90 |
| A11 | Local owned mutex, inspected stale recovery, child-scoped Director retry | PR 96; no global Studio lock or persistent worker |
| A12 | Optional typed creative spec, typed section direction and exact supplied lyrics | PR 100; v3 remains default, hosted typed schema not live-validated |
| A13 | Verified finishing variant, explicit EP artwork direction, actual cover import, immutable assembly/delivery, package review and local coordinator | PRs 97–99; multi-track creative scheduling and supervised external stages remain future work |
| A14 | Existing local privacy boundary retained, no external raw audio or secrets in release tasks | Private authenticated remote service not shipped; design/authentication required before exposure |
| A15 | Updated active docs, real FFmpeg tests mandatory on Windows/Linux | PR 93 and subsequent regression suites |
| A16 | Git commit-graph warnings | Deferred per audit; no destructive maintenance or unnecessary pull |

The finishing implementation (PR 93) verifies finite LUFS/TP/LRA,
original and candidate hashes, exact decoded sample count and fixed-gain
PCM identity, output bit depth, true peak <= -1 dBTP and expected loudness
delta. Only attenuation is permitted; no blind EQ, compression, repair,
fade, resampling, recognition, native generation or automatic preference.
Real synthetic FLAC tests execute on both runner OSes. See
[AUDIO_FINISHING.md](AUDIO_FINISHING.md).

## Operator paths

The [operator guide](OPERATOR_GUIDE.md) is the consolidated current entry point; this file retains specialist acceptance evidence, not the latest repository head. See [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) for current baseline.

- `music.cmd --finish JOB` is plan/status; explicit confirmation creates only a separate candidate if appropriate.
- `music.cmd --feedback JOB --variant VARIANT` reads exact human evidence; writing/release decisions require explicit confirmation.
- `music.cmd --release RELEASE --artwork PATH` plans preparation from an existing verified export and current explicit audio approvals. Confirmation copies assets into separate immutable assembly/delivery stages, never regenerates music or artwork.
- `music.cmd --release-delivery RELEASE --assembly-id release-v1 --delivery-id release-v1 --approve --confirm-run` is a separate whole-package rights, typography and credits attestation for the default workflow. No publication is authorized.

No candidate or final approval is inferred from favorable prior human
ratings, a synthetic test, or exit code. Artwork profile (3000 square,
opaque, 8-bit JPEG/PNG) and gain target are internal conservative defaults,
not universal distributor/mastering requirements. Metadata remains a
sidecar to preserve exact selected audio bytes. Partial timing is
explicit and never fabricated.

## Live finishing acceptance — 2026-11-27

The operator ran the confirmed gain-only command on Windows at main
`cef7858` against the already retained reference. The supplied console
transcript reported exit 0 and `candidate_verified`; the supplied JSON
report was reviewed separately. No repeat run is needed.

| Measure | Original | Candidate |
|---|---:|---:|
| True peak (dBTP) | -0.19 | -1.05 |
| Integrated loudness (LUFS) | -14.60 | -15.46 |
| Loudness range (LU) | 9.2 | 9.3 |
| Duration (s) | 184.358667 | 184.358667 |
| Samples per channel | 8849216 | 8849216 |
| Sample rate (Hz) | 48000 | 48000 |
| Channels / bit depth | 2 / 24 | 2 / 24 |

Applied gain -0.86 dB; actual loudness and peak deltas match the plan.
LRA changed only 0.1 LU. The report records separate original/candidate
SHA-256 values, a candidate PCM hash, timeline preserved, zero Studio jobs,
recognition, MOSS, provider calls and library mutations. This satisfies the
technical live finishing gate on this one reference. The audio and original
report, full hashes and local paths remain private. The auditor reviewed
operator-provided evidence, not the underlying local FLAC files independently.
No candidate listening, clipping repair, artistic improvement, release
approval or publishing is established. The preferred variant remains original.

PR #102 additionally permits explicit completion of an omitted legacy
artist credit during delivery without re-exporting or changing established
credits. Exact-head CI run 45926576136 passed all four configurations:
360 tests per configuration, with one expected Windows-only DPAPI skip
on each Ubuntu job.

## Remaining verification boundary

All executable changes require exact-head four-job Windows/Linux CI.
Real local audio/artwork fixture tests are not access to the operator's
files. The actual retained reference source and prior export remain on the
Windows host. The authorized local finishing check is complete; do not repeat it or the
earlier native song, ASR, MOSS, cover prompt or export. Existing human
feedback can be associated only with the exact local original hash; a private
operator-confirmed ledger import is still separate from this technical result.
The finished candidate needs its own listening assessment before selection.
Actual cover art, artist credit and package approval are operator inputs for
live release delivery; assembly/delivery integration has CI evidence only. No release package may be approved on behalf of
the operator. Do not require another live check merely to validate historical known successes. No production-ready remote service claim.


## Live draft exporter acceptance — 2026-11-28

Operator-reported Windows acceptance at main b7cb968 (PR #148), following
the earlier partial runs at PRs #146 and #147. Exact-head Windows/Linux
Python 3.11 CI for #148 passed (46103441059).

| Sample | Result |
| --- | --- |
| Single / video | Complete; semantic asset checks passed |
| EP / distribution | Complete; two tracks, timing intentionally omitted |
| Manual album / production | Complete; two tracks, timing exported |
| Native playlist / video | Complete; one M4A instrumental, timing not applicable |
| Native album / production | Complete; all 11 tracks; asset checks passed; exit 0 |

Library discovery returned 255 playable songs and 15 collections (one
album, 14 playlists). The last album-only run returned
`album_checks_passed`, no timing issues, four word-timing fallbacks
(tracks 3, 8, 9, 11), and correctly numbered portable filenames.
The four fallbacks preserve original LRC separately and use validated
native line onsets, not repaired word alignment. No native mutations
or inference calls in any acceptance run.

This closes the agreed draft-packaging sample acceptance across all
requested release types and three presets, accumulated across targeted
runs; not a single fresh full-suite run or validation of every library
track. Human player/subtitle review and acoustic alignment are unverified.
Final approved release, rights and publishing remain separate.
Do not repeat successful acceptance or regenerate music solely for this
checkpoint. Native format conversion remains a Studio feature.
