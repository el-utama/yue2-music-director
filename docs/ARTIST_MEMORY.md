# Artist Memory (local, explicit)

A first persistent per-artist profile store, separate from human audio
feedback and the production job identity. The operator owns the defaults.
No inference, remote access, model updates or automatic preference extraction.
Profiles and compiled specs live in Git-ignored `local/`.

## Profile format

Create a private JSON file (for example `local/artist-profile.json`):

```json
{
  "schema": "artist-profile-v2",
  "display_name": "The Midnight Echo",
  "defaults": {
    "vocal": "female",
    "opening": "direct_vocal",
    "score_constraints": {"tempo_bpm": {"mode": "prefer", "value": 90}}
  },
  "confirmed_preferences": ["Warm acoustic textures"],
  "inferred_observations": [],
  "provenance": "Explicit operator choices for this artist"
}
```

This is synthetic example data, not actual user preferences. Defaults can
include opening, vocal, narrator, exact style, key and tempo. They use
the existing typed spec validator: only choose defaults intended as typed
requirements (style, vocal and opening are exact requests, not soft cues).
Do not store individual song lyrics or section plans in the artist profile.
Confirmed preference notes and inferred observations remain separate,
local, and **neither is automatically applied**. The operator may choose
to translate a confirmed preference into a supported typed default.

## Artist names and identity

Use the actual display name in quotes, for example `"The Midnight Echo"`.
Names retain capitalization, spaces, accents and Unicode; a separate portable
internal ID is generated on first named save. Name lookup is NFC/casefold
normalized; ambiguous names stop rather than silently picking a profile.
Existing v1 profiles remain readable by their original ID; saving by that ID
can add a display name without rewriting history. A rename is an explicit
new profile revision selected by internal ID; prior jobs keep their frozen
name and revision. Profile names do not automatically change release credits;
those remain separate explicit metadata.

## Use a profile directly in a new song

Run `music.cmd --artist-profile "The Midnight Echo"` to preview a new job, or add
`--confirm-run` to authorize the existing bounded production flow. Optional
`--profile-revision N` pins a revision; `--creative-spec PATH` supplies partial
song overrides. The job freezes the compiled spec and artist ID, revision
and profile SHA-256 before provider work. Resume with `--job JOB --confirm-run`;
no current profile lookup or new preference application. An existing job
rejects another profile selection. Private notes are not sent to the
provider. This uses the existing opt-in typed policy, whose hosted schema
has not been live validated.

## Commands (Windows repository)

- Inspect: `music.cmd --artist-memory "The Midnight Echo"`
- Save first revision: `music.cmd --artist-memory "The Midnight Echo" --save local/artist-profile.json --expected-revision 0 --confirm-run`
- Update by supplying a full replacement profile and the current expected revision.
- Preview a compiled spec: `music.cmd --artist-memory "The Midnight Echo" --compile`
- Export locally: `music.cmd --artist-memory "The Midnight Echo" --compile --confirm-run`
- Optional: `--revision N` pins an earlier revision; `--overrides PATH`
  supplies a partial creative-spec-v1 JSON for the new song. Missing fields
  inherit; explicit null clears scalar fields. A supplied score_constraints
  mapping replaces the whole inherited mapping (empty clears it). The
  complete combined spec is independently validated; conflicts stop.

The export prints the exact local spec path; pass it to the existing
`music.cmd --creative-spec PATH` workflow. Review before a separately
confirmed production run. The resulting job freezes the spec itself; a
later profile update does not change that job. The private export receipt
records profile revision and SHA-256. Only the compiled typed spec enters
the existing authorized creative workflow, not private notes or provenance.

Append-only revisions use exclusive creation and a previous-file hash
chain; an unexpected entry, incomplete write or changed historical chain
stops rather than overwriting. Compiled specs are content-addressed and
verified on reuse. Do not manually edit ledgers. This is integrity checking,
not cryptographic authentication or protection against a malicious local
administrator. Keep private backups. No automatic import from listening
feedback or automatic artist identity/voice training. Hosted typed-schema
live support remains unverified.
