# Offline knowledge workflow — user and maintainer guide

Current evidence: PR #126 merged, main `44c49599c13d30472e1f36136f12d0266a5dfe75`;
[exact-head Windows/Linux CI](https://github.com/el-utama/yue2-music-director/actions/runs/45962926812) passed (Python 3.11 and 3.13).
This is an alpha feature set, not full artistic or rights acceptance.
Use [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) for the live acceptance register.

## 1. Know which database you are using

| Library | Actual bundled inventory | Local derived index | Provider use |
|---|---|---|---|
| Original style recipes | 1,000 unrendered recipes, 100 per category | `local/style-library.sqlite` | Selected recipe only, Composer, explicitly confirmed autonomous job |
| Observed references | 853 candidate IDs across four source batches | `local/observed-style.sqlite` | Local browsing only; not approved for creative provider transfer |
| Historical knowledge | 7 works (5 German, 2 English), 21 assets: lyrics, scores, automatic harmony | `local/knowledge-bank.sqlite` | Optional bounded numeric descriptors via autonomous or separate text-only CLI with explicit confirmation |

These numbers are different units and must not be summed as songs.
The 853 candidates include 203 Incompetech track metadata records, 517
MusicCaps annotated clip IDs, 95 curated playlist track candidates, eight
explicitly disclosed Suno-generated Chillhop tracks, and 30 FMA album
track candidates. The last three groups are separate additions; cross-source
recording identity and individual rights are not established. No new lyrics
in the observed-reference corpus. No claim that all other tracks are human-made.

| Category | Candidate IDs | Missing to 100 |
|---|---:|---:|
| blues | 100 | 0 |
| jazz | 100 | 0 |
| lofi | 100 | 0 |
| pop | 100 | 0 |
| indie | 100 | 0 |
| folk | 100 | 0 |
| backsound | 100 | 0 |
| hiphop | 100 | 0 |
| lofihop | 27 | 73 |
| trap | 26 | 74 |
| Total | 853 | 147 |

Eight categories meet a candidate-count target, **none is accepted as a
fully reviewed 100-reference corpus**. Lo-fi Hop is 27/100 including eight
disclosed AI tracks; Trap is 26/100. R02/R03/R13/R14 remain open.
See [source batches and rights](OBSERVED_STYLES.md), [MusicCaps attribution](../data/observed_styles/MUSICCAPS_LICENSE.md),
[curated Lo-fi](CURATED_LOFI.md), [FMA candidates](FMA_ALBUM_CANDIDATES.md),
and [historical knowledge bank](KNOWLEDGE_BANK.md).
The complete 24-work Winterreise import plus two English works (26 expected)
has not been verified. Seven works are the tested bundled inventory.

## 2. First use on Windows

From the existing repository checkout, in Command Prompt:

```cmd
music.cmd --styles --build
music.cmd --references --build
music.cmd --knowledge --build
```

Each command is independent. These build disposable indexes from bundled
data; no network, credentials, Studio, GPU, embedding API or generation
is needed. Python 3.10+ with SQLite FTS5 is required. CI covers 3.11/3.13.
The indexes are Git-ignored. Rebuild after a dataset/schema update;
do not delete the source files, job receipts or prior generated audio.
Run these commands once per needed library or update, not per song.

Browse without inference:

```cmd
music.cmd --styles --genre folk --limit 10
music.cmd --references --genre trap --limit 100
music.cmd --references --genre jazz --search piano
music.cmd --knowledge --search "Schubert" --role composer
music.cmd --knowledge --search "home" --role lyricist
```

The first two indexes use quoted lexical AND matching, the historical
knowledge index uses lexical OR matching and role-specific search columns.
These are not semantic retrieval or automatic genre detection. An empty
result is valid; use a shorter term or omit the style/reference search term.
No automatic online fallback. For all genre codes, see the table above.

## 3. Use a style in a new autonomous song

```cmd
music.cmd --job folk-song --request "A quiet goodbye" --style-id folk-001
```

This is preview-only; no text completion or Studio call. Style selection reads
the bundled recipe directly, so building the style index is optional if the
ID is already known. To actually produce a new song, add `--confirm-run`
to the same command only when you want the normal production budget
described in [Autonomous CLI](AUTONOMOUS_CLI.md). A preview alone does not
create a job receipt; supply the request and selected style again on the
first confirmed run. The selected authored recipe is frozen in the saved
job identity and advisory input to Composer. It is not a native BPM or
arrangement guarantee. Explicit creative requirements take precedence.

Resume a confirmed job using `music.cmd --job folk-song --confirm-run`
only when needed. Existing job identity retains the exact selected style,
even if the library changes. Changing the style or adding one to an existing
job requires a new job. No extra inference is authorized by this guide.
The main production CLI never automatically uses observed references or historical numeric context. Explicit historical context is available using `--knowledge-query` and separate confirmation; see [Autonomous CLI](AUTONOMOUS_CLI.md#historical-knowledge-in-autonomous-production-explicit-opt-in). The separate text-only path remains available in [Knowledge Bank](KNOWLEDGE_BANK.md#english-pilot-and-opt-in-text-only-creative-context).

## 4. Recovery and common errors

| Symptom | Action |
|---|---|
| Python launcher missing | Check `py -3 --version`; follow [Setup](../README.md#setup). |
| SQLite FTS5 unavailable | Use a Python distribution with FTS5 support; no online fallback or GPU needed. |
| Database missing or unsupported schema | Run the corresponding `--build` above; retry browsing. |
| Missing source or checksum mismatch | Retain existing index; verify the checkout and pinned source files. Do not change hashes to bypass checks. |
| Database locked or replacement fails | Close other readers and retry the build; do not remove job files. |
| Invalid genre, ID, query or limit | Use the documented genre code, listed recipe ID, and a short query. `--help` is available on all three routes. |
| No matching record | Inspect category without a query (style/reference) or choose shorter search terms (knowledge). |
| Provider unavailable / rejected / unresolved text stage | Follow [Autonomous CLI](AUTONOMOUS_CLI.md#provider-authentication-troubleshooting) and [lock recovery](LOCAL_LOCK_RECOVERY.md). Do not blindly repeat confirmed production. |
| Reference rights unclear | Keep it a candidate, not an approved source; do not copy raw lyrics/audio or send it to the hosted provider. |

## 5. Maintainer checklist and outstanding work

- Review AGENTS.md, the active roadmap, PROJECT_MEMORY.md, and native/local release checkpoints before changing code.
- Reconcile actual manifest counts, source revisions, licenses, unique identities, AI-origin disclosure and genre evidence before claiming progress. Keep candidate, approved, rendered and evaluated counts distinct.
- For a new corpus source, document scope, source version and stable IDs, license evidence and permitted use, selection rules, overlap, missing lyrics, provenance, review status and exact-head CI. No scraping copyrighted lyrics, no inferred rights approval.
- For a change to a launcher, test the documented flags, quoted paths, empty inputs and retained-job behavior; include no-call and no-duplicate checks.
- Update README and relevant user/technical docs, changelog and PROJECT_MEMORY.md in the same PR. Historical checkpoints must be labeled as historical.
- Remaining: 147 metadata slots; individual rights/genre/identity review; broader legitimate lyrics and deeper linguistic/musical features; live and artistic evaluation of explicit historical context, integration of approved observed data; independent artistic evaluation; live validation of the new preset option. No repeat of retained Unreachable, ASR, MOSS, cover or export.

The historical index now uses v3 descriptive craft metrics; rebuild before a new historical query. Existing v1 context jobs resume from frozen receipts. See [craft analysis](KNOWLEDGE_BANK.md#descriptive-craft-analysis-v3) for limitations.

Optional brief-derived retrieval: `--knowledge-auto` uses a bounded local lexical query and freezes an explicit match or abstention; see [automatic retrieval](AUTONOMOUS_CLI.md#automatic-lexical-retrieval-from-the-song-brief). Separate transfer consent remains mandatory. Not semantic retrieval.
