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
prevents final package approval. A changed title/artist requires a new
release identity; an updated cover requires a new delivery ID.

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
