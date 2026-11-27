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
