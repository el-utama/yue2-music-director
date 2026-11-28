# Project memory — requirements, evidence and outstanding work

Last verified: 2026-11-28. This is the durable, editable project memory for
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
4. Implement, test, review and correct. Check both exact-head Python 3.11 PR CI jobs on Windows and
   Linux before merge; manually run the full 3.11/3.13 matrix before release
   or runtime/dependency changes. Preserve historical receipts, reference audio and
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

- R01/R03/R08: native planning twice stopped before synthesis because a requested instrumental intro had notated vocal activity. One stopped score was inside the new cap and showed instrumental notation in the intro. `--review-plan JOB --preview-intro` checks a vocal-free candidate offline, keeping the original plan and applying the existing opening gate to the next vocal entry. Live candidate acceptance and any approved recovery to synthesis remain open.

- R01/R02/R03: new autonomous jobs use a 180-second target with a 190-second hard cap and a flexible eight-section form. Editorial inputs include concrete lyric craft guidance and outro line matches against the final chorus. Offline regression cases exercise new and retained inputs and notated wordless sections. New jobs also stop before listening review when the measured take exceeds its cap. Independent listening and lyric-quality acceptance remain open.

- Verified baseline main `0c20e7c2a60ffe24877d3726831764e5c3b63f7b` after PR #153. Head `a334db7` passed [Windows/Linux 3.11 CI](https://github.com/el-utama/yue2-music-director/actions/runs/46110159738). Fresh-host live validation remains open.
- R04 (2026-11-28): The operator confirmed one native Balanced Q6_K replay on the existing 8 GB Windows host succeeded with model retention set to No after a VAE decode OOM. See [VAE decode recovery](docs/HARDWARE_ADVISOR.md#vae-decode-runs-out-of-gpu-memory). Playback of the ending and alternate-host fit remain unverified.
- R04/R08/R12: `--advisor` implements read-only discovery and goal-specific advice, with simulation and private opt-in reporting. Existing Windows host read-only check passed on 2026-11-28. The Advisor now reports Light CPU as an experimental candidate for low-VRAM hardware. Fresh target-host evidence and production compatibility for the candidate remain open. Preserve the production gate and receipts. Retain the parallel creative quality and corpus requirements.
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
| R01 | Original song from natural-language brief; distinct Composer, Lyricist, reviewer, Director; native YuE2 first | Local alpha; previous reference and a second Indonesian natural-language song completed through Director with explicit duration/audio-identity recovery; review_required; operator rejected Indonesian lyric quality | Independent one-command generalization, English-first lyric craft and human musical acceptance; do not repeat this take |
| R02 | Deep Lyricist knowledge base: many songs, multilingual structure, prosody, rhyme, narrative, imagery, genre and emotional arc | **OPEN; seven historical works indexed by merged PR #120, including two English works; optional text-only role context CI passed.** Explicit historical autonomous context merged/CI (#130); deeper craft metrics merged/CI (#131); corpus expansion and artistic evaluation open | Rights/source audit, actual ingestion, deduplication, searchable structured analysis, counts by language/genre and rights, integration with versioned creative policy, held-out editorial evaluation |
| R03 | Composer knowledge: melody, harmony, arrangement, instruments, vocal phrasing, music theory and production | Native contracts/research docs and symbolic score review available; pilot MusicXML descriptors and automatic harmony search CI passed; melodic descriptors CI passed; opt-in historical text-only context CI passed; explicit original style selection in autonomous Composer merged/CI (#126), no live validation | Source-backed knowledge entries and retrieval, versioned policy integration and meaningful artistic evaluation |
| R04 | Native controls, actual installed capability and limitations; hardware/model/runtime portability | Source-pinned audit, capability inventory and stock reference; [Hardware Advisor](docs/HARDWARE_ADVISOR.md) adds read-only goal-specific discovery/advice and offline fixtures | Existing-host read-only Advisor check passed. Fresh low-VRAM Windows acceptance, proof of effective backend where unavailable, versioned alternate production profiles and separate actual synthesis fit evidence remain open, along with the native control audit |
| R05 | Human feedback, persistent artist profiles, confirmed vs inferred preference | Local immutable feedback and opt-in Artist Memory implemented/CI; explicit typed job selection | Live hosted typed-schema validation; usable profile management, no inferred preferences silently applied; artist naming PR115 merged; live usage pending |
| R06 | Audio finishing, original preserved, separate variant | Gain-only finishing passed live technical check on retained reference | General mastering, repair and artistic comparison are not established; no automatic acceptance |
| R07 | Cover art direction, draft export and complete release package | Draft packaging sample acceptance **PASS** across #146–148 live Windows reports: Single, EP, manual/native Album, native Playlist, three presets, clean/original lyrics, LRC/SRT, fallback with native archive, numbered filenames and asset verification. Cover prompt live. | Human player/subtitle review, phonetic alignment, broader library coverage, native conversion outside Exporter, separate approved assembly/delivery and rights/approval remain open; no publication |
| R08 | One short launcher, intuitive human-readable names and safe recovery | Readiness and specialist launcher routes. Advisor launch and JSON report live-checked on the existing Windows host | Usability audit with real multiword/Unicode names, quoted paths, realistic input and minimal commands; actual Windows readiness not live checked |
| R09 | Robust journals, failure isolation, no duplicate calls | Local locks, receipts, explicit recovery and CI | Supervised workers/process isolation, cross-client durable queue, startup/reconnect/ambiguous failures |
| R10 | Private multi-device operation from Mac and Windows | Audit bridge only | Authenticated production service, queue, status, playback, approvals, reconnect, local host startup; no public exposure |
| R11 | Multi-track/album creative scheduling and consistent artist direction | Release snapshots/assembly; no creative scheduling | Explicit track-level plans/budgets, deterministic resume, independent evidence and approval |
| R12 | Project documentation, continuity and complete requirement coverage | This register plus native/release, first-run and Advisor docs | Maintain on every substantive change, verify all outstanding rows before readiness |
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


2026-11-28: PR #136 merged at bc735c6 after all four exact-head jobs
passed (run 46086895832). Approved duration continuation remains pending
live validation. Operator explicitly requested two routine CI jobs to
reduce latency and duplicate push/PR executions. R12: use Windows and
Ubuntu Python 3.11 for PRs, cancel superseded PR runs, no push-triggered
workflow. Retain manual full Python 3.11/3.13 compatibility checks for
release and runtime/dependency changes. No tests removed, no change to
production inference or other requirements. New workflow validation
and repository branch-rule compatibility must be checked before merge.


2026-11-28: PR #137 merged at 25aaa50 after exact-head CI 46087150990
passed both Linux and Windows 3.11 jobs; manual release matrix not run.
Live PR #136 duration continuation: 71 BPM source score 207.887s, 77 BPM
candidate 191.688s, style BPM text synchronized; original creative receipts
reused, native MIDI passed, one song completed/imported, saved score and
lyric conditioning verified, native completion not_flagged. Acoustic
measurement 191.359s, 48 kHz stereo 24-bit FLAC, -13.85 LUFS, approximately
0 dBTP. Original journal file hash differs from measurement and independently
re-read current file hash, which match one another. Cause and waveform
equivalence unknown; no ASR attempt reported. R01/R08/R09: one-time explicit
hash approval can bind the current verified native song to retained acoustic
evidence without altering original journal or resubmitting. Technical
review required. Exact-head CI and live recovery pending. All other
requirements retained; no private song IDs, full hashes, lyrics or audio
committed.


2026-11-28: PR #138 merged at 5d0fd91, exact-head CI 46088068656
passed two jobs. Operator reported successful live approved hash recovery:
same completed native job and verified saved score/lyrics; original journal
preserved, one outstanding ASR, two CPU excerpts, one Director completion,
review_required, exit 0. No new composition or synthesis. Actual duration
191.359s, notated early vocal onset approximately 1.17s, six scheduled
sung blocks, ASR WER disagreement approximately 12.6%, true peak near 0 dBTP.
Original waveform equivalence and cause of file hash change remain unknown.
MOSS gave advisory intimate male-vocal descriptions but also unsupported
stereo claims and ambiguous excerpt endings; Director correctly kept
truncation and pronunciation unverified. R01/R08/R09 advance to second
end-to-end live workflow with supervised recovery; unattended generation,
future prevention of identity drift and process supervision remain open.
Next: human listening of the existing audio, read-only completed-source
checks and optional separately approved fixed-gain finishing (R06), not
another synthesis or critic replay. No automatic artistic/release approval.
Add offline historical-source regression for the recovery sidecar, including
mutation rejection. All other requirements remain open as applicable. No
private song IDs, hashes, lyrics, audio or operator filesystem paths committed.


2026-11-28: PR #139 merged at 7b41d74 after two exact-head green jobs
(46089129650). Operator reported live fixed-gain finishing candidate_verified,
-1.05 dB attenuation, exit 0; original preserved. No new inference. Operator
explicitly rejected the Indonesian lyrics as unnatural, embarrassing and
artistically unusable. This is a negative lyric-quality result (R01/R02),
not an artistic success. Keep English as the default even for Indonesian
briefs; Indonesian only by explicit selection. Preserve frozen languages
on resume. Do not regenerate this take automatically or silently remove
multilingual support. Prioritize English lyric craft: coherent narrative,
natural idiom, singable phrasing, concrete imagery, non-forced rhyme and
editorial evaluation before expensive native generation. These are quality
targets, not implemented acceptance guarantees. No new private lyrics,
local IDs or paths committed. Existing English CLI default verified in code;
regression tests guard it. CI pending for this checkpoint.


2026-11-28: Operator explicitly reprioritized R07 draft Exporter before
Composer, Lyricist and Reviewer improvements. Focus clean aggregator lyric
text alongside tagged source, native LRC/SRT, presets, naming/layout and
Single/EP/Album. Do not require full metadata or actual artwork for draft
export; optional cover prompt suffices. Prefer verified native YuE2 cover,
format conversion, metadata and timestamp functions over duplication.
Existing native song_export source audit identifies WAV/FLAC/MP3 route;
installed capability and actual output still need verification. First
increment adds section-stripped clean TXT alongside preserved original,
production and distribution presets (distribution explicitly skips timing),
maintains existing path/identity and ordered-track rules, and validates
clean asset in downstream assembly. Old snapshots remain unchanged.
Native timing correction, specialized video presets, real naming/usability
and multi-track live acceptance remain open. No inference or new song.
Exact-head two-job CI pending. All deferred R01/R02/R03 and other
requirements retained; English lyric default unchanged.


2026-11-28: PR #141 merged at a957443 after two green CI jobs (46091585013).
Operator added playlist export and requested reuse of native playlist/album
membership. Pinned source confirms playlist_list/playlist_get and albums
encoded in native description envelope. R07 adds read-only collection
listing/selection and ordered playlist M3U8, without collection writes or
new inference. Initial scope: completed retained autonomous jobs only;
Studio-only library songs require a separate source adapter, not fabricated
Director receipts. Native collection/track limits, unchanged membership,
relative M3U8 path and immutable package covered by synthetic tests. Actual
installed collection reads and player acceptance remain unverified.
Playlist is not final release type. Exact-head CI pending. Exporter remains
priority before deferred creative work; preserve all other requirements.


2026-11-28: PR #142 merged at 04ee99e after two exact-head green jobs
(46091872058). Native playlist/album export now implemented for retained
Director songs; installed live acceptance remains pending. R07 next
increment adds explicit native-library-only draft source, list songs,
manual native song IDs or native collection membership, byte-preserving
FLAC/PCM WAV/MP3, local duration probe, native plain lyrics/instrumental
handling, existing karaoke and mixed-format relative playlist. No new
encoding, inference, release approval or library writes. Strict retained
source unchanged; no silent downgrade. Native-only drafts excluded from
reviewed assembly. Tests and docs added; exact-head CI pending. Need
installed route live acceptance, specialized presets, native timing
correction and naming/usability audit before Exporter acceptance. No
operator commands or new songs required at this development step.


2026-11-28: PR #143 merged at fbf9576 after two exact-head green jobs
(46092440615). R07 next increment adds video preset with preserved native
LRC, derived line LRC and SRT, source line counts, known non-timing header
handling and strict rejection of nonzero offset. Native source audit confirms
karaoke_set supports LRC or SRT/ASS/SSA import, and karaoke_make generates
native timing. Use Studio rather than duplicate an editor; export an explicit
snapshot after correction. No library mutation or inference. Real synthetic
FLAC/WAV/MP3 ffprobe duration tests, assembly video asset preservation and
snapshot tests added. Exact-head CI pending. Next: practical naming/path
and selection usability audit, then one consolidated live acceptance on
existing library tracks. Native format conversion remains distinct from
byte-preserving export. No operator commands required yet.

PR #144 initial CI 46093609468 failed on both OSes: invalid escaped quotes
in the new line-LRC f-string caused 10 module import errors. Corrected
format construction, no test relaxation. Exact corrected-head CI required.


2026-11-28: PR #144 merged at 68ad377 after corrected exact-head green
Windows/Linux CI 46094915707. R07/R08 usability increment provides exact
Unicode name selection (ambiguous matches explicitly rejected), ordered
track preview and one-command native export acceptance, preserving prior
packages. Source-only audit: native format conversion available but not
invoked; existing byte formats copied; timing correction remains Studio
UI; complete credits and cover image not required for draft. No duplication
of native collections or karaoke. Restricted audit bridge does not expose
library reads; installed acceptance must run locally on Windows. Samples
cover three presets and four export types; absent native collection or
missing timing is incomplete, not a fabricated pass. Synthetic tests and
docs added; exact-head CI pending. No inference. Human player/subtitle
inspection remains separate. Return to creative improvements after
exporter acceptance; R01–R14 retained.

2026-11-28: PR #145 merged at 6ac40f0 after both green exact-head jobs
46095438953 (429 Windows tests, new acceptance tests discovered). Final
source audit found long nested Windows paths and an acceptance checker
that only verified manifest hashes. This follow-up budgets actual track
paths before staging, preserves existing names when short, verifies staged
package hashes, records relative audio file paths, verifies semantic sample
assets/order/status and rejects native collection drift between selection
and export. Tests and documentation updated; exact-head CI pending.
Installed library unavailable via restricted bridge; one local acceptance
run remains essential. No new inference or Studio mutations authorized.

2026-11-28 live operator report at PR #146 baseline: native reads returned
255 playable songs and 15 collections. Single/video, EP/distribution and
manual album/production completed with semantic asset checks passed. Native
playlist blocked by generic source-file/format error; actual extension or
missing path not established. No eligible native album under old eight-track
sample limit; not proof no albums exist. No inference or Studio mutation.
Do not repeat successful samples. Pinned upstream audio_pcm::plays_in_window
and library import handler confirm native Ogg/OGA, AAC, AAC M4A/MP4 alongside
FLAC/MP3/PCM WAV. Extend byte-preserving format validation, source-specific
track diagnostics and collection-only acceptance using normal size limits.
Exact-head CI pending. Native collection retest and human playback review
still required; no forced karaoke or conversion.

2026-11-28: PR #147 merged at 19f7357, both exact-head CI jobs green.
Operator collection retest: 255 songs, one album and 14 playlists.
Native M4A instrumental playlist completed, all asset checks passed.
11-track native album copied audio and lyric assets; 7 timing tracks passed,
4 rejected with unordered/malformed enhanced word anchors. Asset checks
passed, overall partial. Actual raw word clocks not inspected. Preserve
prior live passes. R07 follow-up independently validates exact lyric text
and native line onsets, archives raw LRC and derives line-only LRC/SRT only
when safe; invalid lines/text remain partial, no fake word alignment.
Remove duplicate filename numbering only for exact fully numbered native
album/EP sequence, preserve full title. Album-only targeted acceptance.
Exact-head CI pending; no new inference or native mutation.


## Live draft exporter acceptance — 2026-11-28

Operator-reported Windows acceptance at main b7cb968 (PR #148), following
the earlier partial runs at PRs #146 and #147. Exact-head Windows/Linux
Python 3.11 CI for #148 passed (46103441059).

| Sample | Result |
| --- | --- |
| Single / video | Complete; semantic asset checks passed |
| EP / distribution | Complete; two tracks, timing intentionally omitted |
| Manual album / production | Complete; two tracks, timing exported |
| Native playlist / video | Complete; one M4A instrumental, timing not applicable |
| Native album / production | Complete; all 11 tracks; asset checks passed; exit 0 |

Library discovery returned 255 playable songs and 15 collections (one
album, 14 playlists). The last album-only run returned
`album_checks_passed`, no timing issues, four word-timing fallbacks
(tracks 3, 8, 9, 11), and correctly numbered portable filenames.
The four fallbacks preserve original LRC separately and use validated
native line onsets, not repaired word alignment. No native mutations
or inference calls in any acceptance run.

This closes the agreed draft-packaging sample acceptance across all
requested release types and three presets, accumulated across targeted
runs; not a single fresh full-suite run or validation of every library
track. Human player/subtitle review and acoustic alignment are unverified.
Final approved release, rights and publishing remain separate.
Do not repeat successful acceptance or regenerate music solely for this
checkpoint. Native format conversion remains a Studio feature.

Next: improve English-first creative craft before synthesis. Audit current
Lyricist/Composer/Reviewer evidence and prompts, strengthen narrative,
natural idiom, imagery, emotional progression, singability, and musical
intent, and add editorial evaluation fixtures. Technical QA is not artistic
approval. No new live inference without authorization; preserve historical
contracts and all deferred requirements.


2026-11-28: Operator explicitly requires all current documentation to cover
new PC with newly installed YuE2 and zero previous Director/agent runs.
R08/R12 fresh-host runbook separates offline, existing-native export and
full production; local MCP discovery, exact actual paths, prerequisites,
provider/DPAPI, stock CUDA/Q8/Whisper/MOSS gate, preview and confirmation,
empty library, optional indexes, recovery and new-agent handover. No
assumed old host artifacts or remote bridge. Cross-linked current entry
points and historical checkpoints. Fresh-host actual live validation not
performed; documentation/CI gate pending. No generation or model change.


2026-11-28: Operator asks how to make Hardware Advisor work well on different
PCs (example RTX 4 GB VRAM / 16 GB RAM) and requests documentation audit
before a new session. [Hardware Advisor](docs/HARDWARE_ADVISOR.md) records
source/guide audit, current hard-coded gate, native read candidates, tier
thresholds, discovery/recommendation/report contracts, test matrix, and
staged implementation with no historical receipt changes. Discovery and
advice preceded the separate work on alternate profiles and real host
validation. Draft export acceptance, R02/R03 creative improvements and all
other open requirements remained tracked.

2026-11-28: PR #151 merged after both Python 3.11 jobs passed on the
documentation head. [PR #152](https://github.com/el-utama/yue2-music-director/pull/152)
implements the read-only Advisor and audits MCP schemas
and handlers against `bfd35a0`, uses the existing loopback transport and
audited read list plus catalog, and checks bounded local volumes without
calling the recursive storage tool. Offline cases cover tier and low-memory
boundaries, partial observations, exact GPU identity, current settings
drift, stale effective cache, native catalog and rights evidence, and
private output. Check the [PR CI](https://github.com/el-utama/yue2-music-director/pull/152/checks)
for the exact implementation head and both Windows/Linux Python 3.11 jobs.
A synthetic loopback MCP smoke confirmed the exact allowlist, reply size
limit and disconnected fallback. No synthesis, settings change, model
download, hosted provider call or repeat export was performed. The
restricted audit bridge cannot execute this local command.

2026-11-28: R04/R08/R12 existing-host Advisor acceptance passed via the
operator's shareable `music.cmd --advisor --json` report after checkout sync.
All ten production reads succeeded, Studio was idle, and the selected stock
Balanced Q6_K pair matched the engine. About 7.96 GiB total and 6.30 GiB free
dedicated VRAM were observed. CUDA was configured, Q8 was effective, flash
attention was on, and effective backend was unknown. Balanced required no
additional set files. The follow-up distinguishes unknown comparisons from
confirmed sufficient resources and ties the VRAM warning to the preserved
tier. No provider, MOSS or new synthesis result was established by this run.
Keep the current configuration. Do not repeat this host check for the same
milestone. Fresh low-VRAM acceptance, the separate alternate profile
decision, and actual synthesis fit remain open.

2026-11-28: R04/R08/R12 follow-up audited alternate profile boundaries in
the native launcher, model resolver, planned and synthesis receipts,
continuation, and the retained-source reader. At Studio pin `bfd35a0`,
Windows Auto may still prefer CUDA on a 4 GiB NVIDIA GPU. For that target
the read-only Advisor can display Light Q5_K_M with explicit processor,
F16 cache, keep loaded off and a one-track limit. The pinned estimate
is about 8.94 GiB total system RAM, including model weights, system and
work memory. This is a candidate for separately authorized target-host
evaluation. No settings change, inference, new model installation or
production profile was introduced. Existing Windows acceptance stands.
Fresh low-VRAM inventory, actual load and synthesis data, exact installed
backend evidence and the opt-in production contract remain open.
