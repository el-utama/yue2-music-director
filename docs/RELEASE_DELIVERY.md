# Local release delivery and review

After [approved audio assembly](RELEASE_ASSEMBLY.md), import an actual cover image
and prepare the exact delivery package. The image is supplied by the operator;
there is no external image service, generation, account access or new music job.
Cover direction remains optional. Explicit EP direction uses `music.cmd --cover
RELEASE --type ep --title TITLE --song JOB ...`; old cover defaults are preserved.

```powershell
.\music.cmd --release-delivery RELEASE
.\music.cmd --release-delivery RELEASE --artwork "C:\path\cover.jpg" --confirm-run
.\music.cmd --release-delivery RELEASE --approve --confirm-run
.\music.cmd --release-delivery RELEASE --revoke --confirm-run
```

Status/plan is read-only. The second command imports exact JPEG/PNG bytes
after local FFmpeg/ffprobe decode, signature, dimensions and pixel-format
checks. The local profile is 3000 × 3000, one opaque 8-bit image, at most
25 MiB. Animated/transparent PNG, malformed images, and mismatched extensions
are rejected. This deliberately conservative profile is not a claim of
compliance with every distributor, color-profile accuracy or rights clearance.
No automatic resize, conversion, typography, or image generation. The
operator supplies the finished visual including any intended typography.

Use --assembly-id to choose an existing approved-audio assembly and
--delivery-id for a separate immutable package (defaults package-v1,
delivery-v1). Output under results/release-delivery/RELEASE/DELIVERY-ID
includes original selected FLAC bytes, lyrics, any existing LRC/SRT,
cover.jpg or cover.png, metadata.json (exact title, artist, release type and
ordered tracks), and delivery.json with all file hashes, artwork validation
and assembly hash. Metadata is a sidecar, not rewritten FLAC tags. No new
transcoding. Partial timing remains partial, and an empty artist credit
prevents final package approval. A changed title or established artist requires a new release identity; an
updated cover requires a new delivery ID. An omitted artist may be filled
explicitly at delivery with --artist, without changing the original export.

The separate approve/revoke commands display package identity and require
typed confirmation of actual human review of contents, typography, exact
credits and usage rights. They append a private hash-linked receipt under
results/release-review, not a rewrite of delivery.json. Approval cannot be
inferred from tests or technical passes. Current exact audio approval is
rechecked for every delivery/status/review. If revoked, downstream
validation fails closed while historical files and receipts remain. No
publication permission, commercial clearance, automatic upload or external
service is inferred. Local hash links are not authentication against
coordinated local tampering. No source audio or artwork is sent externally.

Existing deliveries verify without re-decoding artwork or rendering audio.
Regression uses real synthetic JPEG/PNG and exact audio-approval fixtures;
operator artwork and music are not reprocessed in CI.

## One-command local preparation

If the original export and separate human audio approvals already exist, use
`music.cmd --release RELEASE --artwork "C:\path\cover.jpg" --confirm-run`.
Repeat explicit --variant JOB=VARIANT if needed, select --snapshot for an
existing export revision and --workflow-id for an independent immutable plan
(default release-v1). The coordinator freezes all ordered audio identities,
approvals, release metadata, source manifest and exact cover hash with zero
external stage budgets. It invokes assembly and delivery only, retaining both
stage manifests and recording the completed/partial result. It does not
invoke finishing or another export. On interruption, retry with the same
cover bytes and workflow ID; completed stage outputs are verified, not
copied again. A completed workflow is verified with `music.cmd --release RELEASE`.
Review the resulting package using `music.cmd --release-delivery RELEASE --assembly-id release-v1 --delivery-id release-v1 --approve --confirm-run`
(or the selected workflow ID in both positions). This remains a separate human
rights/credits/typography and package decision, not publishing. Multi-track
creative scheduling and automatic external stage execution remain future work.

## Complete a missing artist credit without re-exporting

For an existing export with no artist credit, add `--artist "Artist Name"` to
`music.cmd --release RELEASE --artwork PATH --confirm-run` (or directly to
`--release-delivery`). The exact explicit credit is frozen in the delivery
contract and, for a coordinated run, in its workflow plan. The original
export, audio, lyrics, timing, and assembly remain unchanged. This does not
approve the package or assert rights. A prior nonblank artist cannot be
replaced. A different credit after a delivery/workflow has been frozen
requires a distinct delivery/workflow ID. On status, resume and review the
retained credit is restored automatically; it need not be retyped. Existing
contracts without a credit-completion field remain valid. No automatic
artist name is inferred from a filename, repository owner or music prompt.
