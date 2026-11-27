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

## Remaining verification boundary

All executable changes require exact-head four-job Windows/Linux CI.
Real local audio/artwork fixture tests are not access to the operator's
files. The actual retained reference source and prior export remain on the
Windows host. A single new, explicitly authorized local finishing check
can validate the retained reference without re-running the earlier native
song, ASR, MOSS, cover prompt or export. Existing human feedback can only
be associated with the exact local original hash; the finished candidate
needs its own assessment. No release package may be approved on behalf of
the operator. Do not require that live check merely to validate historical
known successes. No production-ready remote service claim.
