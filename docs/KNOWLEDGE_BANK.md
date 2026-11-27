# Offline artistic knowledge bank — pilot

Operator decision 2026-11-27: offline-first SQLite + FTS5/BM25. Optional
CPU semantic retrieval later only if measured useful; no GPU or embedding
API dependency. Hosted creative providers remain a separate explicit boundary.

## Run from the repository checkout (Windows)

```cmd
music.cmd --knowledge --build
music.cmd --knowledge --search "Schnee" --role lyricist
music.cmd --knowledge --search "Schubert" --role composer
```

Build uses only bundled bytes and creates a disposable local/knowledge-bank.sqlite
index. Repeat build replaces the derived index only after all records validate.
Search opens read-only and returns bounded metadata and measured descriptors,
not raw lyrics. No provider or Studio calls, no network, no model download.
A missing FTS5 module is an explicit failure; no online fallback.

## Source and evidence

Five historical German Lieder from Schubert/Müller's Winterreise are bundled
from OpenScore Lieder at a pinned revision. The manifest records exact upstream
Git blob checksums and per-work identifiers, authors, rights and source paths.
CC0 covers the corpus contribution; the underlying 1827 works are historical
public-domain originals. No recording rights claimed. See manifest and license.
Automatic Roman-text annotations are model estimates, not verified harmony.
The lyric files are automatically extracted score text, not guaranteed original
poem order or stanza boundaries. MusicXML descriptors are not acoustic evidence.
No contemporary lyrics or private operator data are included.

This is a limited source-specific pilot: seven unique works (five German, two English), seven score files,
seven lyric files and seven automatic harmony files. The counts are bundled
inventory; PR #119 verified five in CI; PR #120 verified seven in Windows/Linux CI. German art song is not a
representative sample of modern multilingual songwriting. This is lexical
retrieval, not semantic RAG. The text-only creative CLI now offers an opt-in versioned numeric context;
historical numeric context remains opt-in in autonomous production; see [Autonomous CLI](AUTONOMOUS_CLI.md#historical-knowledge-in-autonomous-production-explicit-opt-in). PR #126 adds a separate explicit authored-style option.
Raw text must remain local by default. No open-ended corpus importer or
editorial quality claim. R02/R03/R13 remain open (issue #117).

## Larger offline import (same reviewed source)

The full Winterreise manifest pins 24 works and 72 assets at the exact source
revision. Obtain that source checkout/archive once on any connected machine,
then copy the extracted directory to the Windows host. No network is used by:

```cmd
music.cmd --knowledge --build --source-dir "D:\\OpenScore Lieder"
```

All required files must match the manifest; partial or changed inputs fail
without replacing the existing index. The full external import (24 German plus two bundled English works = 26 expected) is not yet verified; only the bundled subset and failure paths are tested. This does not import arbitrary
new corpus sources. V2 adds lexical type/token ratio (not rhyme or semantic
quality), notated vocal rests, key signatures and consecutive pitch interval
counts (not acoustic phrasing or a verified voice-separated polyphonic analysis).
Rebuild the disposable v1 index to use v2. No hosted transfer or creative calls during import.

## English pilot and opt-in text-only creative context

Haydn/Shakespeare's She never told her love (1795) and Bishop/Payne's
Home, Sweet Home (1823) add historical English song. The underlying authors
died more than 170 years ago; the pinned OpenScore transcriptions are CC0.
The full external Winterreise import retains these two bundled English works
(26 total expected if the full source is present). No modern genre coverage.

From a checkout with an editable install, run the text-only CLI with
`python -m yue2_music_director.creative_core --repo . --job sample --request "A quiet goodbye" --knowledge-query home`.
This previews local evidence, no provider calls. Adding both `--confirm-text`
and `--confirm-knowledge-context` permits sending bounded numerical observations
only to Composer and Lyricist; no reference titles, query, raw text, melody,
source paths or IDs in the added provider context. Query and provenance remain
in local job identity, and resume uses frozen evidence even if the index changes.
The opt-in must be repeated on resume. No actual provider or Studio calls were
made by this PR; mock tests only. The production launcher now supports explicit historical numeric selection with separate confirmation; it does not retrieve historical knowledge automatically. The separate text-only path above retains its own confirmation flags.
Numerical descriptors are not proof of artistic usefulness; no semantic or
multilingual query translation is implemented.
