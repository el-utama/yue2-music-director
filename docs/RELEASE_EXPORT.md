# Release Export Specialist

Independent deterministic local module. Uses completed autonomous song jobs (including recovered continuations), verifies retained report/brief/audio provenance and exports the original FLAC plus tagged original lyric TXT. Reads existing native karaoke LRC over loopback GET only. Full exact line order required. Original enhanced LRC is preserved exactly, including word timestamps and section tags. SRT follows the pinned Studio display heuristic (estimated word tail, four seconds for plain lines, next onset cap, last cue at most three seconds), additionally capped at measured audio duration; section labels are not subtitles. This preserves instrumental gaps, not verified word ends. Native timestamps may be interpolated; never fabricate timings from score clock or equal spacing. No new ASR, GPU, LLM, library writes or publishing.

Single: `music.cmd --export JOB --confirm-run`. Album: `music.cmd --export RELEASE --type album --song JOB1 --song JOB2 --title "Album" --confirm-run`. EP: use --type ep. Optional --artist. Without confirmation plan only. Defaults to repo results/exports/songs, albums, eps; release title plus stable ID, numbered track folders for collections. UTF-8 lyrics and metadata. Exact original audio copy, no transcode. Output staged then renamed; hashes recorded in release.json. Repeat verifies existing snapshot without new native reads. Missing/invalid native LRC produces explicit partial_missing_timing and exit 2 while retaining FLAC/TXT; later use a new release ID with --song JOB after timing exists. No empty/fake LRC or SRT. Explicitly authorized karaoke generation and timestamp editing are separate future steps. No automatic finishing/artwork copying yet, no commercial release approval. CI and live timing availability must be checked separately.

Official source audit (pinned v5-compatible source bfd35a0): [nativeLibrary.ts](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/app/services/nativeLibrary.ts#L120) reads metadata.lrc, [lrc-parser.ts](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/app/services/lrc-parser.ts#L63-L102) implements SRT conversion, [MCP](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/mcp.rs#L2025) exposes library_song_get detailed and karaoke_make (#L2154) for generation. Our existing loopback GET avoids MCP text truncation for full metadata. No separate SRT download MCP tool found. karaoke_make can replace existing karaoke and incurs alignment inference; don't invoke it automatically in this export-only increment. Strict parser/coverage checks intentionally reject malformed or incomplete karaoke rather than claiming full synchronized lyrics. Regression reproduces upstream gap example and duration clamp. No live read yet.

### Source identity hardening

For new exports, the timing adapter checks the retained source SHA-256 and uses the existing read-only library_song_files identity check before and after two bounded native GET snapshots. Both snapshots must agree (including any supplied version and metadata fields), and song/job/lyrics must match the retained track. This is a conservative observed-stability screen, not an atomic Studio transaction or proof that imported/edited/interpolated karaoke was created against this recording. Preserve the original LRC UTF-8 bytes and hash. Missing, malformed, changed or unavailable timing yields a partial FLAC/TXT export without LRC/SRT; source audio mutation or output write failure aborts the staged package. Existing matching export snapshots are verified without any new native reads or schema migration. No new recognition or generation. Real operator audio has not been reprocessed for this change.

### Stable release IDs and explicit snapshots

A release ID now binds exact type, title, artist, ordered retained-source
identities and original audio policy, including across songs/albums/eps.
Case aliases cannot create a duplicate. New IDs reserve a private immutable
identity under `results/exports/.release-index/` before writing the package.
Existing pre-index packages are discovered and verified in their original
folders without migration or repeated timing reads. Ambiguous IDs or changed
metadata require a different release ID.

The default v1 package remains immutable, including partial timing exports.
When missing timing becomes available, explicitly request another snapshot:

```powershell
.\music.cmd --export RELEASE --snapshot v2 --confirm-run
```

Use the same ordered song IDs, type, title and artist options as v1. The
revision lives under `results/exports/revisions/RELEASE/v2/`, links to the
verified v1 manifest hash, and never overwrites the original package. A
revision does not generate missing karaoke, approve a release or attach
finished audio. Portable filenames avoid Windows device basenames, bound
Unicode component length and reject unsafe Windows path lengths before
writing. A failed package write leaves only its identity reservation (and
the prior package, if any); retry the identical contract, not a changed ID.


## Production and distribution presets

New exports and new snapshots additionally contain TITLE.clean.txt, a UTF-8
plain lyric view using the existing section grammar. TITLE.txt retains the
original tagged production text (exact bytes for verbatim typed lyrics).
Clean text removes standalone bracketed section/direction labels and groups
sung lines into blank-line-separated stanzas, preserving repeats,
punctuation, sung parentheticals and Unicode. It does not rewrite lyrics,
guess ambiguous inline directions, certify aggregator-specific formatting,
or imply artistic approval. Existing snapshots are unchanged.

```powershell
.\music.cmd --export JOB --confirm-run
.\music.cmd --export NEW-ID --song JOB --preset distribution --confirm-run
```

The default production preset keeps original FLAC, both lyric texts and
native LRC/SRT (when available); use it for archives and video subtitles.
The distribution preset includes original FLAC and both texts but skips all
native timing lookups; absence of LRC/SRT is intentional, not a partial
failure. Single, EP and album use the same preset rules and existing
portable title/ID paths and ordered numbered track folders. Preset is bound
to release identity through timing policy; use a distinct release ID to
change presets and repeat the same preset on snapshots/resume. Missing
artist, cover or aggregator identifiers do not block draft export. Do not
invent ISRC, credits or cover files. Existing optional cover-prompt and
approved release delivery remain independent. Native audio format conversion
and metadata capabilities should be reused after auditing installed route
and output identity, not duplicated. Timestamp editing and more specialized
video presets remain open. No new inference or publication.


## Native playlists and albums

The pinned Studio source exposes playlist_list/playlist_get through the
loopback library routes. The native UI stores albums as playlists with an
album:v1 marker or collection:v2 JSON envelope in description. The reader
uses the same bounded GET transport as existing song metadata, extracts only
ID/name/kind/ordered song IDs, and ignores cover payload and preferred take.
See [native library UI](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/app/services/nativeLibrary.ts#L135)
and [MCP playlist_get](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/mcp.rs#L3653).

```powershell
.\music.cmd --export --list-collections
.\music.cmd --export RELEASE --native-collection ID --confirm-run
.\music.cmd --export RELEASE --type playlist --song JOB1 --song JOB2 --title "Playlist" --confirm-run
```

The native collection supplies its exact title, kind and order; no manual
song/type/title overrides. First increment requires each native song ID to
match exactly one completed autonomous Director result and verifies its full
retained lineage. Studio-only songs or ambiguous identities are rejected,
not silently skipped or synthesized. For Studio-only songs, use the explicit native-library draft source below. Collection identity is frozen in release contract;
changes require a different release ID. Recheck membership before publishing
the local staged package. Existing immutable export is verified without
re-reading timing, though the selected collection is read again. Playlist
supports up to 100 distinct tracks, native albums/manual EPs/albums up to 24.
Playlist output is under results/exports/playlists with relative UTF-8
playlist.m3u8 paths in exact order; no external player test yet. Playlist is
not an aggregator release type; use an album/EP/single for release assembly.
Production/distribution preset and optional metadata rules remain unchanged.
No playlist mutation, generation, new ASR or publishing. Installed native
route and real collection acceptance still need live verification.


## Native library draft sources

Use the explicit draft-only mode for music made directly in Studio or mixed
collections with no Director receipts. This uses current library title,
written lyrics, existing karaoke and exact local audio bytes; never invents
Director or release approval. Source-pinned library_songs_list and
library_song_get plus library_song_files supply native identity. ffprobe
checks actual audio duration and supported codec (FLAC, PCM WAV, MP3); no
encoding or inference. Plain lyrics and instrumentals are accepted; absent
sung text gets no fake clean lyrics or timing. Native metadata and file
identity are checked before and after export; changes abort staging.

```powershell
.\music.cmd --export --list-songs
.\music.cmd --export DRAFT --native-song ID --confirm-run
.\music.cmd --export DRAFT --native-collection ID --library-only --confirm-run
```

Repeat --native-song for a manually ordered album, EP or playlist (provide
type and title). Existing strict --native-collection without --library-only
continues to require completed Director receipts; no silent downgrade.
Native draft source and retained source contracts remain distinct. Drafts
cannot enter the Director-reviewed assembly workflow. Existing packages
stay immutable; a changed source identity requires a new release ID.
Native library-only timing remains advisory; absent timing for vocal text
is an explicit partial result, instrumental text has no timing requirement.
No automatic external release or native mutation. Synthetic tests passed exact-head CI in PR #143; actual installed native library reads and formats remain unverified.


## Video preset and native timing corrections

`music.cmd --export JOB --preset video --confirm-run` adds TITLE.line.lrc
(simple sung-line onsets) to the existing production package. Native LRC is
preserved byte-for-byte; derived line LRC keeps the native onset precision
(two decimals for centiseconds, three for milliseconds). SRT retains the
Studio display-end heuristic, not measured phonetic ends. Enhanced/plain
line counts are recorded; no guessed word timing. Video mode accepts a BOM,
standard non-timing LRC headers and zero offset without rewriting the native
file. Unknown headers, nonzero offsets, missing/reordered words and invalid
clocks remain partial timing, not silently adjusted. No video rendering.

The pinned native MCP karaoke_set supports LRC or imported SRT/ASS/SSA and
replaces saved timings. karaoke_make can generate timing with the native
recognizer. Use the Studio's own authorized timing correction/import UI;
exporter never invokes either mutating tool. To capture corrected timing
without modifying the earlier package, repeat the identical export options
with `--snapshot v2` (or another unused ID). If source audio, lyrics or
collection membership changed, use a new release ID. Corrections must not
alter the original audio identity for a retained Director source. Native
library draft mode remains separate if tags or active version changed.
No claim that native correction is phonetically exact. Installed route and
player/editor acceptance still need a consolidated live check.


## Select by song title or collection name

```powershell
.\music.cmd --export my-song --song-name "My Song" --confirm-run
.\music.cmd --export my-album --collection-name "Evening Sessions" --confirm-run
```

Names are exact, Unicode NFC-normalized and case-insensitive. Duplicate
names are rejected with matching IDs; never choose the first take silently.
Use --native-song or --native-collection for an exact ID. Name selection
uses current native draft sources, not Director approval. Retained job and
strict native collection commands remain unchanged. The output ID is the
operator's stable short label, separate from the song or collection name.
Omit confirmation to preview folder, preset and ordered track titles.

## Consolidated local acceptance

```powershell
.\music.cmd --export --check-library --confirm-run
```

This explicit command selects up to two existing playable songs and one
smallest native album/playlist of at most eight tracks each, exercising
single/video, EP/distribution, album/production and playlist/video. If a
suitable native collection is absent, a manual ordered sample is used and
native acceptance remains incomplete. No collection creation, karaoke
inference, generation or settings changes. Writes only a unique local
results/export-check/run-... directory with sample exports and report.json.
Original packages and source recordings are untouched. Without confirmation
it lists a plan only. Missing timing or absent native collection yields
incomplete (exit 2); missing timing is not an inference request. Inspect
report and sample package files; human subtitle/player and acoustic timing
review remain separate. Do not share private audio or lyrics in transcripts.

### Final acceptance checks

Preview also shows planned audio filenames. New track paths shorten long
names when necessary for Windows, keeping track number and original title
in the manifest; existing packages are not renamed. The acceptance command
checks source audio hashes, original and clean lyrics, timing asset policy,
SRT and line-LRC derivation, exact M3U8 relative paths/order, and the complete
asset set. Collection identity is frozen between acceptance selection and
export. Report lists timing issues; no automatic fix or phonetic claim.

### Live collection follow-up

Studio's pinned import implementation also preserves Ogg/OGA, AAC and
AAC in M4A/MP4. Export these original bytes with codec validation, not a
conversion or extension rename. Missing/unsupported media errors identify
the native track number and ID. Do not skip a track silently. The acceptance
selection uses the smallest collection within normal export limits (24 album,
100 playlist), not the old eight-track cutoff. `music.cmd --export --check-library --collections-only --confirm-run` tests only native collections after the previously successful single/EP/manual album checks. A collection-only pass is not a fresh full-suite pass.

### Native line-only recovery

If native enhanced word timestamps fail ordering or bounds, validate the
original line onsets and exact complete lyric text independently. Only
recognizable word timestamp tags may be discarded; invalid line times or
text mismatches still fail. The source is archived as TITLE.native.lrc,
TITLE.lrc becomes validated plain line LRC, and SRT uses existing line
onsets and the documented display-end heuristic. Manifest marks discarded
word anchors, reason and both hashes; acceptance rederives assets. No
acoustic alignment claim. Retained Director strict policy unchanged.
Native EP/album filenames remove existing numeric dot prefixes only when
all titles form the exact numbered track sequence; original titles remain
in metadata. Previous exports immutable. Retest only album with
`music.cmd --export --check-library --collections-only --collection-kind album --confirm-run`.
