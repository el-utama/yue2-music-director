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

This is a limited source-specific pilot: five unique works, five score files,
five lyric files and five automatic harmony files. The counts are bundled
inventory; PR #118 verified three in CI; the five-work follow-up requires fresh CI. German art song is not a
representative sample of modern multilingual songwriting. This is lexical
retrieval, not semantic RAG. The creative role integration is intentionally
not enabled yet: it needs explicit versioned policy, frozen evidence and
authorization before any derived context is sent to a hosted provider.
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
without replacing the existing index. The full 24-work index is not yet
verified; only the bundled subset is tested. This does not import arbitrary
new corpus sources. V2 adds lexical type/token ratio (not rhyme or semantic
quality), notated vocal rests, key signatures and consecutive pitch interval
counts (not acoustic phrasing or a verified voice-separated polyphonic analysis).
Rebuild the disposable v1 index to use v2. No hosted transfer or creative calls.
