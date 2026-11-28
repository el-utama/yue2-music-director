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

- Main `bd35bc9db5680639852da8e41b72a02816e754ad` after [PR #132](https://github.com/el-utama/yue2-music-director/pull/132). Its final head `41fcb4f4816c73cdccc66e77ffc50446ac656053` passed [four CI jobs](https://github.com/el-utama/yue2-music-director/actions/runs/45971043570). Opt-in brief-derived retrieval uses normalized Unicode and freezes the local match or abstention. Seven historical works, 853 candidate IDs, 147 slots open. Retrieval relevance and artistic quality remain unverified.
- P0 recovery follow-up (R01/R08/R09): a local interruption between saving the Studio acknowledgment and updating the journal can now recover the existing plan or song ID. Regression coverage injects that interruption and checks that planning and synthesis are each submitted once. Windows Studio recovery and independent live artistic acceptance remain open.
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
| R02 | Deep Lyricist knowledge base: many songs, multilingual structure, prosody, rhyme, narrative, imagery, genre and emotional arc | **OPEN; seven historical works indexed by merged PR #120, including two English works; optional text-only role context CI passed.** Explicit historical autonomous context merged/CI (#130); deeper craft metrics merged/CI (#131); corpus expansion and artistic evaluation open | Rights/source audit, actual ingestion, deduplication, searchable structured analysis, counts by language/genre and rights, integration with versioned creative policy, held-out editorial evaluation |
| R03 | Composer knowledge: melody, harmony, arrangement, instruments, vocal phrasing, music theory and production | Native contracts/research docs and symbolic score review available; pilot MusicXML descriptors and automatic harmony search CI passed; melodic descriptors CI passed; opt-in historical text-only context CI passed; explicit original style selection in autonomous Composer merged/CI (#126), no live validation | Source-backed knowledge entries and retrieval, versioned policy integration and meaningful artistic evaluation |
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
| R14 | 100 music styles per specified category, lyrics if available | 1,000 authored presets merged/CI; 853 metadata candidates merged/CI; 147 metadata slots open; optional authored style selection merged/CI (#126). No approved quota. | Rights-reviewed 100 observed records per category; source and lyric availability, deduplication, creative evaluation |

## Corpus and knowledge inventory — explicit gap, not optional to full product

Current bundled inventory (PR #126): 1,000 original style recipes, 853 candidate reference IDs (including 517 annotated clips and eight disclosed AI tracks), seven historical lyric/score works. None of these are interchangeable units. See [offline knowledge workflow](docs/OFFLINE_KNOWLEDGE_WORKFLOW.md) for exact category counts and commands. The following pre-pilot inventory is historical, not the current state.

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

- [Operator guide](docs/OPERATOR_GUIDE.md)
- [Offline knowledge workflow](docs/OFFLINE_KNOWLEDGE_WORKFLOW.md)
- [Developer onboarding](DEVELOPMENT.md)

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

2026-11-27: PR #119 merged after exact-head green CI. Follow-up adds two historical English works with pinned bytes and retains them during the full German source import; expected full count 26, not measured. Explicit text-only knowledge opt-in sends bounded numeric descriptors only, freezes local provenance in job identity, and requires confirmation on resume. No live provider, Studio or quality evidence; still need broader corpus, meaningful technique retrieval and autonomous production integration.

2026-11-27: **NEW operator requirement R14** — collect 100 music styles each for blues, jazz, lofi, pop, indie, folk, backsound (TikTok/social media), hip hop, lofihop, trap; lyrics if available/rights compatible. Total 1,000 category entries. Separate observed song/style references from authored presets. Follow-up branch provides 1,000 unique original unrendered style recipes (100/category), zero new real-track references and zero lyrics; actual corpus quotas remain OPEN. Candidate sources audited, bulk raw retrieval blocked. Offline FTS5 style library separate from real-song index, no GPU or provider calls. See docs/STYLE_LIBRARY.md. R02/R03/R13 remain open; do not count presets as historical songs.

2026-11-27: Observed reference pilot, 203 distinct Incompetech metadata candidates with ISRC and source provenance, blues 11, jazz 74, lofi 0, pop 18, indie 0, folk 0, backsound 100, hiphop 0, lofihop 0, trap 0. Not independently reviewed per-track, no audio or lyrics, not production evidence. MTG-Jamendo raw access now succeeds via Git blob but license prohibits nonresearch use without authorization; excluded. See docs/OBSERVED_STYLES.md. No real reference quota closed.

2026-11-27: MusicCaps annotation dataset CC BY-SA 4.0, source snapshot ecbb5a1f52e52cf09a38dd7698578ccca7cef353. Added 517 unique clip IDs with normalized musical descriptors and category evidence; combined inventory {"blues":100,"jazz":100,"lofi":5,"pop":100,"indie":100,"folk":100,"backsound":100,"hiphop":100,"lofihop":0,"trap":15}. Distinct IDs within each source; cross-source recording overlap unknown. No audio, source captions or lyrics copied; no provider/GPU. Full song identity and recording rights not established. R14 remains open. See data/observed_styles/musiccaps-manifest.json.

2026-11-27: PR #123 merged after CI. Follow-up adds 95 curated Lo-fi track candidates from pinned AgentBBS factual playlist metadata and 8 creator-disclosed Suno v5 Chillhop entries from Open Lo-Fi. Source licensing is reported, not independently verified per track. Combined 823 identifiers (815 excluding AI-disclosed eight), missing 177 category slots including 92 lofihop and 85 trap; no new lyrics. WaivOps CC BY 4.0 drum-loop/chord datasets are useful for technical technique references, not full-track quotas; do not pad with loops. FMA official pages 403 here. R14 remains open.

2026-11-27: PR #124 merged. Direct FMA album catalog metadata: 30 candidates; totals {"blues":100,"jazz":100,"lofi":100,"pop":100,"indie":100,"folk":100,"backsound":100,"hiphop":100,"lofihop":27,"trap":26}. Album-level rights reported, individual tracks not reviewed; duplicate known artist/title pairs excluded, clip-level identity overlap unknown. Direct FMA and Hugging Face bulk API access blocked; dataset cards inspected, annotation/lyric rights not assumed. No new lyrics or audio. Remaining slots 147. No provider calls. R14 open.

2026-11-27: PR #125 initial head failed CI on all four jobs because a stale Trap test assumed every returned reference was a MusicCaps clip. Mixed album/clip indexing itself passed the preceding inventory assertions; Windows log recorded 386 tests with one error. Updated the test to assert both source counts and their distinct rights fields, without relaxing rights validation. Exact new head CI required. Additional source audit: cmd-fma-metadata parquet (532 kB) and Reubencf/music-style-prompts JSONL (58 MB) contain potentially useful track-level metadata, but direct bulk access failed and the latter includes AI-generated prompts/lyrics of uncertain rights; no records imported. Do not claim target completion or copy unverified lyrics.

2026-11-27: PR #125 merged after corrected exact-head CI. PR #126 integrates explicit authored style recipe selection (`--style-id`) into the primary autonomous launcher. Snapshot is versioned and checksum-bound in job identity; exact saved style survives library removal and resume, only Composer receives the bounded authored style as advisory context during explicitly confirmed production. No observed or unreviewed source metadata or raw lyrics passed. Default production and continuation preserve old identity; no automatic genre selection, no live generation, mock tests pending. R02/R03/R14 remain open. Bulk FMA and HF dataset access still blocked in current environment; 147 candidate slots outstanding.

2026-11-27: PR #126 merged after exact-head green CI. Documentation audit identified stale pending-PR claims, historical inventory presented without current context, disconnected entry points, and outdated source-access statements. Consolidated three-index guide, source/rights counts, preview and confirmed resume, recovery, README, roadmap and changelog. No new data, provider calls, Studio jobs or acceptance claims. Documentation audit does not close R02/R03/R13/R14; R12 is continuous.

2026-11-27: PR #127 merged after exact-head green CI. Follow-up documentation audit mapped all 18 special launcher routes to actual guide files; added operator install/adoption, readiness, confirmation scope, recovery, release and developer onboarding entry points. Native and release checkpoints labeled historical. No new corpus, provider calls or Studio jobs. Relative file links in changed docs checked against repository tree; full historical example/anchor audit and live setup validation not established. R12 remains continuous; all open requirements retained.

2026-11-27: PR #128 merged after exact-head green CI. Repository-wide static documentation audit at main 9ab2898: all 66 tracked Markdown files retrieved, 263 inline relative links resolved, 11 heading fragment occurrences checked against seven target headings, all passed. 18 primary special launcher routes mapped. Added offline regression tests for tracked Markdown relative links/heading fragments and primary route coverage; extended actual Windows CI with style/reference build/search and plan-only selected-style preview. External URLs, complete Markdown syntax, historical command behavior and installed-host operation are not certified by this static check. No new data, audio generation, provider calls or local operator work. R12 continuous; return to substantive corpus and creative integration priorities after CI.

2026-11-27: PR #129 merged after exact-head green CI. Follow-up integrates existing historical numeric context into autonomous Composer/Lyricist, opt-in preview and separate --confirm-knowledge-context alongside --confirm-run; snapshot provenance and checksum frozen, resume requires consent and does not reread index. No observed-source data transfer, extra text calls, GPU or new inference. Retained-plan continuation validates already completed creative receipts with frozen context. Tests cover numeric-only payload, consent, frozen resume, no hits, invalid checksum and legacy job. Seven historical works and 853 candidate IDs unchanged; R02/R03/R13/R14 open; independent artistic and hosted/live validation pending.

2026-11-27: New craft analysis derives punctuation group and repeated token-sequence statistics from actual extracted text, melodic event ratios from notation and conservative automatic RomanText token statistics. No stanza/rhyme/hook/narrative/emotion or verified harmonic-function claim. Index v3 requires rebuild; creative payload v2 extends bounded numeric fields while v1 frozen snapshots retain exact previous payload and consent. No data added or provider/Studio inference. Tests use hand-calculated fixtures and actual bundled corpus; exact-head CI pending. R02/R03/R13/R14 open, 147 candidate slots unchanged. Next substantive work: source expansion and held-out artistic evaluation.

2026-11-27: PR #131 merged after exact-head green CI. Added opt-in --knowledge-auto brief-derived local lexical query (bounded unique terms, common English/Indonesian request words filtered). Separate transfer consent; frozen matched selection or explicit no-term/no-match abstention, no provider payload on abstention. Manual query unchanged. No automatic genre inference, translation, semantic retrieval, new sources or inference. Mock CI pending; corpus and artistic validation remain open. Next: actual data expansion, held-out creative evaluation.


2026-11-27: P0 live operator report on main 7d7a81c (PR #133 merged,
workflow 45977889206 successful): an Indonesian natural-language request
failed at Composer semantic validation. Retained rejection contains coherent
ordinary performance prose with opening and vocal descriptors, but no
explicit narrator or rationale. No downstream stages; preserve private
receipt and job unchanged. R01/R08/R09 remain open. New default
reviewed-score-v5-structured separates musical direction fields in the wire
contract and canonicalizes validated responses; v3 and older jobs retain
their existing policy. Synthetic Indonesian regression and old receipt
compatibility tests added; exact-head CI and independent hosted/live
acceptance pending. No new provider or Studio call. Do not count this as
repair of the existing rejected job. Prioritize personal production
readiness over convenience expansion, preserving every R02–R14 requirement.


2026-11-28: PR #134 merged at 7b0a958, exact-head CI 46000945928
passed all four jobs. Live operator report: Indonesian brief completed
Composer, Lyricist and Reviewer, CUDA Q8 Studio ready, native plan submitted
once; score blocked solely on 207.88732394366198 seconds vs 195-second cap,
zero soft flags. No song, ASR, MOSS or Director calls. Preserve all private
receipts. R01/R08/R09 still open. New offline duration-fit preview proposes
a bounded tempo-only candidate with full re-review and unchanged notation
except tempo; no inference, no writes to original or actual recovery.
Exact-head CI pending. Next: inspect candidate, implement provenance-safe
explicit recovery and evaluate native MIDI/audio. No automatic relaxation of
cap, no truncation or unapproved new synthesis. All other requirements retained.

Initial PR #135 CI rejected the synthetic 123-bar fixture because it placed all bars in one native voice group; native ABC requires groups of 1–4 equal bars. Corrected fixture grouping without changing the intended duration, cap or eligibility gate. Exact corrected head CI remains required.


2026-11-28: PR #135 merged at 8abb994 after exact-head CI 46086398042
passed four jobs. Operator's live fit preview returned not_eligible on BPM
text, with zero provider/Studio calls and no render authorization. Git
fast-forward succeeded despite commit-graph metadata maintenance error;
separate Git health item remains deferred. R01/R08/R09: follow-up proposes
simple consistent BPM advice adjustment and explicit exact-BPM approval
for a fixed separate duration continuation, preserving original creative
and native receipts, no additional planning or creative calls. Typed or
tempo-explicit briefs and ambiguous BPM text remain outside scope.
Synthetic tests and docs added; exact-head CI and native MIDI/audio live
acceptance pending. No actual operator score, private creative data or
provider credentials transferred. All requirements retained.
