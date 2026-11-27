# Approved audio release assembly

This optional offline step uses an already exported original single, album or EP and an exact, independently verified selection of each audio variant. No new Studio requests, synthesis, ASR, MOSS, artwork generation, timing read, FFmpeg render or publishing. Original exports and reference recordings remain immutable.

## Human selection

```powershell
.\music.cmd --feedback JOB --variant gain-v1
.\music.cmd --feedback JOB --variant gain-v1 --confirm-run
.\music.cmd --feedback JOB --variant gain-v1 --approve-release RELEASE --confirm-run
```

Use these only after listening to the displayed candidate. The original (default) feedback receipts remain v1; candidate receipts use v2 and additionally bind the finishing report SHA-256. Approval is specific to the exact audio and release ID. An original's feedback/approval is never inherited. A no-change result is not a separate candidate. Revocation applies to the exact selected variant.

## Assemble

```powershell
.\music.cmd --assemble-release RELEASE --variant JOB=gain-v1
.\music.cmd --assemble-release RELEASE --variant JOB=gain-v1 --confirm-run
```

Omit --variant to select originals; repeat it for different tracks. Use --snapshot to select an existing explicit export revision and --assembly-id for a separate immutable package. Default is package-v1. No candidate is chosen automatically. Every track needs an explicit current audio approval. The plan is read-only; confirmation copies verified files to results/release-assembly/RELEASE/ASSEMBLY-ID. Original export hashes and selected audio/finishing receipt hashes and latest approval receipts are bound to assembly.json. Repeated commands verify the same assembly without rewriting it. Changed selections, new approval receipts or metadata require another assembly ID. Revocation blocks current assembly verification/reuse but does not erase historical output.

Lyrics and existing LRC/SRT are copied byte-for-byte. A finished candidate is eligible because the finishing contract verifies a fixed-gain waveform and unchanged sample timeline; this does not establish acoustic alignment accuracy. Partial timing remains partial with exit 2, never fabricated. A missing approval also exits 2 without writing a package. This is not final publication approval: actual cover attachment, sidecar release metadata and package-level approval are separate steps in [local release delivery](RELEASE_DELIVERY.md). No approval is written by assembly.

Synthetic integration tests exercise actual FFmpeg gain candidate, separate approvals, original export immutability, repeat verification, revocation, ordered multi-track export and tamper rejection. No live reference processing is implied.
