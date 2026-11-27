# Human listening evidence (local only)

The original autonomous result remains immutable with its historical pending
verdict. Human judgments are separate append-only receipts under
`results/feedback/JOB/`. Each record binds the exact original audio SHA-256
and retained result SHA-256. It has a sequence number, UTC timestamp and hash
of the preceding record; this detects inconsistent evidence, not coordinated
local tampering. All data stays local and Git-ignored.

```powershell
.\music.cmd --feedback JOB
.\music.cmd --feedback JOB --confirm-run
.\music.cmd --feedback JOB --record path-to-local-feedback.json --confirm-run
.\music.cmd --feedback JOB --approve-release RELEASE --confirm-run
.\music.cmd --feedback JOB --revoke-release RELEASE --confirm-run
```

Without confirmation the command verifies the retained source and reports
existing feedback; it makes no provider, Studio or recognition calls.
Interactive feedback asks for lyrics, vocals, melody, arrangement and ending,
each good, needs_work or not_assessed, and optional observations. An import
must contain exactly source (the source object displayed by the status
command) and payload (kind listening, ratings keyed by those five dimensions,
observations, confirmed_preferences and inferred_preferences arrays).
Only actual human-provided judgments may be entered. Inferred preferences
remain explicitly distinct from confirmed preferences.

Approval is a separate explicit decision scoped to the original audio and
release ID, with a typed APPROVE or REVOKE confirmation. A listening receipt
for that exact source is required before approval. Ratings, model observations,
technical passes and exit codes do not imply approval. A different result or
audio hash cannot inherit these records. The approval is an operator decision
about that source for the named release, not proof of a finished package,
commercial readiness, copyright clearance or permission to publish. Export
manifests retain their existing non-approved state. Candidate-specific
approval and release orchestration are later extensions.

No historical verdict is backfilled without the exact local audio identity.
An interruption leaves evidence to inspect; do not delete ledger receipts.
