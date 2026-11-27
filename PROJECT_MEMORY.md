# Project memory — requirements, evidence and outstanding work

Last verified: 2026-11-27. This is the durable, editable project memory for
all development agents. Read before proposing or implementing work; update
with each change. It records requirements and evidence, not automatic
authorization for new inference, publication or external data transfer.
Keep private material in Git-ignored local storage; do not put credentials,
unpublished lyrics, audio, private paths or personal preferences here.

## Mandatory operating procedure

1. Reopen this file, AGENTS.md and the active roadmap at session start;
   verify main, exact PR head and current CI rather than trust chat history.
2. Map the new request to requirement IDs below. Add newly stated
   requirements with date/context; distinguish operator requirements from
   developer proposals. Never silently drop a requirement, change its scope
   or mark it complete merely because a different milestone passed.
3. Audit actual implementation, real data counts, rights, evidence and
   end-user journey. Include realistic input (multiword/Unicode names,
   paths with spaces, existing jobs, resume, empty/malformed data and
   errors). Prefer short commands and human-facing names over internal IDs.
   The operator uses separate Mac and Windows hosts; avoid repeated manual
   testing and long commands.
4. Implement, test, review and correct. Check exact-head CI on Windows and
   Linux before merge. Preserve historical receipts, reference audio and
   safety gates. Update this file and relevant docs in the same PR.
5. Before claiming readiness, compare every relevant row below against
   actual evidence. Distinguish implemented, CI-tested, live-validated,
   artistically assessed and blocked. Report unverified data as unknown;
   do not invent counts. P0 local alpha is not full product acceptance.
   Only ask the operator when a meaningful decision or unavailable local
   action is essential. No background work claims.
6. Each future agent should leave a current checkpoint (commit, pending PR,
   evidence, next action, blocker) here. Supersede stale statuses explicitly,
   preserve history in Git. No separate chat handover is required for basic
   continuity.

## Current baseline and work in progress

- Main `58d16138f39e3fb6b4c6b99cad6d79622f1af0ca` after PR #118. Exact head `343444a51134da2bf8f5f0caefe25b4fa184109f` passed [all four CI jobs](https://github.com/el-utama/yue2-music-director/actions/runs/45954453751); three actual works indexed in CI. Windows operator host not checked.
- Follow-up: five bundled works, full 24-work pinned offline checkout manifest and additional descriptors, pending CI. R02/R03/R13 remain open.
- Preserve retained reference Unreachable and its separate gain-only
  candidate. No new generation, ASR, MOSS, cover or export rerun required.
  See [local release checkpoint](docs/LOCAL_RELEASE_CHECKPOINT.md) and
  [native audit checkpoint](docs/NATIVE_AUDIT_CHECKPOINT.md).
- Installed restricted bridge previously verified music-server 5.0.0;
  not a production remote endpoint. See [bridge runbook](docs/RESTRICTED_AUDIT_BRIDGE.md).

## Product acceptance register

| ID | Requirement / deliverable | Current verified state | Remaining acceptance work |
|---|---|---|---|
| R01 | Original song from natural-language brief; distinct Composer, Lyricist, reviewer, Director; native YuE2 first | Local alpha implemented, prior live workflow and retained reference succeeded; latest CI green | Independent generalization, artistic quality and usability; do not repeat successful reference |
| R02 | Deep Lyricist knowledge base: many songs, multilingual structure, prosody, rhyme, narrative, imagery, genre and emotional arc | **OPEN; three German art songs indexed by merged PR #118; follow-up bundles five and supports an offline full-cycle import of 24 (not yet tested on all 24).** No creative integration yet | Rights/source audit, actual ingestion, deduplication, searchable structured analysis, counts by language/genre and rights, integration with versioned creative policy, held-out editorial evaluation |
| R03 | Composer knowledge: melody, harmony, arrangement, instruments, vocal phrasing, music theory and production | Native contracts/research docs and symbolic score review available; pilot MusicXML descriptors and automatic harmony search CI passed; new melodic descriptors pending CI; no creative integration | Source-backed knowledge entries and retrieval, versioned policy integration and meaningful artistic evaluation |
| R04 | Native controls, actual installed capability and limitations | Source-pinned audit and live velocity fixture; velocity not retained in ABC, schedule coverage advisory only | Complete remaining melody/harmony/arrangement/replay/cover/adapter audit; installed binary identity not verified; no fake controls |
| R05 | Human feedback, persistent artist profiles, confirmed vs inferred preference | Local immutable feedback and opt-in Artist Memory implemented/CI; explicit typed job selection | Live hosted typed-schema validation; usable profile management, no inferred preferences silently applied; artist naming PR115 merged; live usage pending |
| R06 | Audio finishing, original preserved, separate variant | Gain-only finishing passed live technical check on retained reference | General mastering, repair and artistic comparison are not established; no automatic acceptance |
| R07 | Cover art direction, release export and complete release package | Cover prompt/original single-song export live; approved variant assembly/delivery CI only | Actual authorized cover and metadata, human review, multi-track release verification; no publishing without approval |
| R08 | One short launcher, intuitive human-readable names and safe recovery | Readiness and multiple specialist launchers CI; previous launcher help failure fixed | Usability audit with real multiword/Unicode names, quoted paths, realistic input and minimal commands; actual Windows readiness not live checked |
| R09 | Robust journals, failure isolation, no duplicate calls | Local locks, receipts, explicit recovery and CI | Supervised workers/process isolation, cross-client durable queue, startup/reconnect/ambiguous failures |
| R10 | Private multi-device operation from Mac and Windows | Audit bridge only | Authenticated production service, queue, status, playback, approvals, reconnect, local host startup; no public exposure |
| R11 | Multi-track/album creative scheduling and consistent artist direction | Release snapshots/assembly; no creative scheduling | Explicit track-level plans/budgets, deterministic resume, independent evidence and approval |
| R12 | Project documentation, continuity and complete requirement coverage | This register plus native/release docs | Maintain on every substantive change, verify all outstanding rows before readiness |
| R13 | Privacy, licensing, safe external use | Local private storage and explicit provider boundary | Validate every reference corpus source/rights, permitted use and hosted transfer; preserve originals and no unsupported claims |

## Corpus and knowledge inventory — explicit gap, not optional to full product

Historical pre-pilot inventory from main tree and Lyricist source: no committed .db/.sqlite/.csv/
.jsonl/.parquet/.tsv corpus, no corpus importer/retrieval module. Private
Windows corpus contents are unknown; zero independently verified entries.
No claim of thousands of lyrics based on model training or documentation.
Existing knowledge Markdown is research/reference documentation, not a
populated lyric dataset. Source [Lyricist](src/yue2_music_director/lyricist.py)
and [roadmap](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md).

Proposed scale from discussion (planning targets, not operator-confirmed
minimums or actual counts):

| Category | Initial proposal | Mature proposal |
|---|---:|---:|
| Unique song metadata and verified structure | 10,000 | 100,000+ |
| Songwriting technique analyses | 1,000 | 10,000+ |
| Full lyric references with explicit usable rights | 1,000 | 10,000+ |
| Structured rhyme/prosody/narrative patterns | 5,000 | 50,000+ |

Counts have different units; never sum them as songs. Metadata-only,
bag-of-words, analyses and full text must be separate. Public availability
is not license permission. Use owned/licensed/public-domain materials,
verified permitted derived features and source-specific terms. Do not
download/redistribute copyrighted lyrics indiscriminately or generate fake
records to reach targets. No arbitrary external raw lyric transfer.
Prioritize source/license manifest and actual inspectable data, then
deterministic analysis/retrieval, integration, deduplication and evaluation.
Track unique counts, rights status, languages, genre coverage, missing
data, source versions and checksums. A schema or empty SQLite is not a bank.

## Prioritization after current pending PR

Named-artist PR #115 merged after exact-head green CI. Prioritize R02 and R03
(artistic knowledge, actual corpus evidence), before further convenience
CLI expansion or remote service architecture. Audit source/license
candidates and report concrete usable data volumes, not speculative
scraping targets. Keep prompt/job identities versioned. Existing alpha
can remain usable while the full product requirements are open.

## Links and decision history

- [Active roadmap](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md)
- [Native control contract](docs/knowledge/NATIVE_CONTROL_CONTRACT.md)
- [Native audit checkpoint](docs/NATIVE_AUDIT_CHECKPOINT.md)
- [Local release checkpoint](docs/LOCAL_RELEASE_CHECKPOINT.md)
- [Artist Memory](docs/ARTIST_MEMORY.md)
- [Autonomous CLI](docs/AUTONOMOUS_CLI.md)
- [Agent instructions](AGENTS.md)

2026-11-27: operator identified two missed requirements: natural multiword
artist names and the missing lyric knowledge bank. User explicitly requested
persistent, read/write project memory to avoid omissions in later sessions.
The memory requirement is implemented via PR #116; PR #115 merged after integrated CI; the lyric bank remains open. Do not require user to
repeat prior requirements.


2026-11-27: Operator agreed offline-first SQLite + FTS5/BM25; optional CPU semantic retrieval only if needed. No GPU or hosted embedding dependency. See [offline knowledge bank](docs/KNOWLEDGE_BANK.md). PR #118 indexed three unique historical works with nine pinned assets in CI. Expand rights-reviewed multilingual coverage, support local import, freeze retrieval in a versioned creative policy and evaluate before acceptance. No new synthesis or provider calls.

2026-11-27: Follow-up adds two actual works and pinned full-cycle manifest (24 works, 72 assets, not bundled or imported in full). Offline import from an already obtained OpenScore checkout; checksum verification, atomic replacement, and lexical diversity plus score interval descriptors. No genre/language diversity yet. No transfer to provider; actual creative retrieval and held-out artistic evaluation remain open.
