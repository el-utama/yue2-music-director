# Autonomous Music Director — active product roadmap

Decision: 2026-11-26. This is the active product-level roadmap, superseding the sequencing of the earlier generation-first research phases, not their safety contracts. The [generation-first architecture](MUSIC_DIRECTOR_ARCHITECTURE.md) remains the native execution and evidence reference. Freeze this direction until an explicit product decision or demonstrated blocker justifies a change.

The [project memory and acceptance register](../PROJECT_MEMORY.md) is mandatory for every session. P0 sequencing does not waive later product requirements. In particular, a lyric corpus and artistic knowledge base remain explicit incomplete deliverables, not an implied feature of the Lyricist prompt.

## Current engineering checkpoint — 2026-11-27

The live reference take and original release assets remain immutable. PRs #88–#92 hardened semantic stage acceptance, versioned opening/Director metrics, timing-source identity, historical provenance and human feedback. The standalone [Audio Finishing Specialist](AUDIO_FINISHING.md) adds only verified fixed attenuation and a separate candidate; no new generation, ASR, MOSS, cover or export rerun. Its real synthetic-audio tests require FFmpeg on both Windows and Linux. The authorized Windows reference run at main cef7858 passed the technical live finishing gate; see [live acceptance evidence](LOCAL_RELEASE_CHECKPOINT.md#live-finishing-acceptance--2026-11-27). The original remains preferred; no additional inference or live repeat is needed. The prior evidence and phased implementation sections below are historical context, not a request to rerun earlier demos. PR #94 adds stable release IDs and explicitly versioned immutable snapshots. The owned-lock and continuation recovery change adds local process-birth inspection, explicit stale-marker archival and child-scoped Director retry; live Studio recovery is not validated by these offline tests. A completed historic source is read under frozen evidence, not replayed through current production validators. Opt-in [typed creative requirements](TYPED_CREATIVE_SPEC.md) and verbatim operator-supplied lyrics now have a separate versioned contract, preserving the v3 default and legacy receipts; hosted typed-schema live compatibility remains unvalidated. Remaining product work: multi-track creative scheduling and supervised external stage orchestration. The bounded local `music.cmd --release` workflow coordinates existing approved audio assembly and artwork delivery/package review with immutable plan and stage receipts (see [Release Assembly](RELEASE_ASSEMBLY.md) and [Release Delivery](RELEASE_DELIVERY.md)), later private authenticated service/artist memory. No new live output or approval is implied. A separate Windows Git health audit remains deferred; do not repeat pulls just to suppress warnings.

The later [native audit checkpoint](NATIVE_AUDIT_CHECKPOINT.md) records PRs #104–109, completed live conversion and guide reads, current CI evidence, and ordered artistic work. Remote audit access is documented separately; it does not complete the private production service milestone.

## Offline knowledge checkpoint (PRs 118–126)

The [offline knowledge workflow](OFFLINE_KNOWLEDGE_WORKFLOW.md) records current data and exact commands. Seven historical lyric/score works, 1,000 original style recipes and 853 observed-reference candidate IDs are bundled and CI-tested. Explicit selected-style context reaches the autonomous Composer only on confirmed runs; historical numerical context is separately opt-in in autonomous production and the text-only CLI (no automatic retrieval). The autonomous integration is implemented pending exact-head CI and live/artistic validation. No observed-corpus transfer. Local artist profiles are implemented and CI-tested, not live validated with hosted typed-schema production. R02/R03/R13/R14 remain open: 147 candidate slots, recording identity/rights/genre verification, broader legal lyrics, deeper technique analysis, versioned creative retrieval and independent artistic evaluation. P0 alpha is not full acceptance. No new live work authorized. Use [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) for current state; earlier snapshots below are historical.

## Native control audit gate

The operator identified the score editor's Velocity/CC controls. Source tracing and live synthetic conversion confirm that Apply's MIDI-to-ABC route discards velocity; the operator reports the corresponding UI edits are not retained. Fixed exported MIDI velocities are not acoustic conditioning. See [native control contract](knowledge/NATIVE_CONTROL_CONTRACT.md). Before adding performance/humanization or changing generation policies, complete relevant UI/schema/handler/engine data-flow audits. The prior feature inventory is not an exhaustive engine audit. Keep the successful reference and its gain-only candidate unchanged; no repeat synthesis or mandatory release experiment.

## Goal and deployment

One natural-language instruction produces one original, listenable song and a traceable artistic report without repeated operator commands. The operator uses multiple PCs, principally a MacBook via Tailscale and MCP. Run the autonomous orchestration on the Windows host where YuE2 Studio is installed (i7-14700F, RTX 5060 8 GB, 32 GB RAM); keep Studio calls loopback-only, sequential GPU work, CPU MOSS, local Whisper, local files and durable job state. No new large local LLM or duplicate model downloads. Browser/MCP clients are later interfaces to this same backend, not required for first operation. A client disconnect must not cancel a submitted durable job. No public exposure; later private Tailscale HTTPS, authenticated application/MCP, access control and origin validation. Windows host, Studio and required provider connectivity must remain available.

Use a configurable text LLM provider, with the operator's free Nemotron service as the preferred starting point. Do not assume its exact API endpoint, authentication, model ID, quotas or support for structured output until verified. Use a provider interface, role-specific model configuration and bounded calls, not multiple large local models. Explicitly configure authorized external text transfer; credentials and unpublished work stay out of Git. No raw audio sent externally. No claim of background execution in ChatGPT; autonomy belongs to the installed Windows service/runner.

## Current evidence (not release claims)

- Direct-native synthesis, acoustic measurement, one explicit local ASR and two neutral MOSS CPU excerpts completed in the live The Last Train Home run (188.48 s, exit 0; PR #73). Human subjective report: good vocals, monotonous instrumentation, ending not cut off. MOSS agreed broadly on limited arrangement evolution but misjudged the final boundary. This is one example, not evaluator accuracy or professional-quality evidence. Preserve original; no automatic ending repair.
- PR #74 merged at 51a5ed5; 4/4 CI jobs passed for the bounded style-only arrangement revision. It remains untested on the operator's Studio. No required rerender of that demo.
- Main 53c73a5: first actual autonomous user-authored original-song workflow completed on Windows with hosted Nemotron, one native song, one explicit local ASR, two local CPU MOSS excerpts and Director judgment (exit 0, review_required). Operator subjective verdict: lyrics good, vocals good, melody ordinary, arrangement ordinary, ending poor and cut before completion. Reported measured duration 194.998667 s against 195 s cap, true peak -0.09 dBTP, ASR WER disagreement ~0.328. Operator screenshot confirms Studio's CUT SHORT badge; exact native reason (length or memory) is still unverified. Near-cap duration strongly suggests length. MOSS mono stereo claims invalid. See PR #79 live evidence. Preserve original and lyrics; do not mask incomplete composition with fade or rerender automatically.
- Modular creative core, provider, native draft and listening pipeline are implemented; one normal live workflow succeeded, not full P0 acceptance. Persistent supervised service, knowledge databases, Artist Memory, remote dashboard and live recovery remain incomplete. Retained audit confirmed engine_truncated=true and a 312.195 s score against a 195 s cap, 54 lyric lines and missing notated verse#3. Use existing reviewed-native pre-synthesis gate for new jobs; a rejected plan consumes no song/ASR/MOSS budget. No automatic replan or repair. Second live run stopped on unsupported variable meter/key notation; PR #82 recheck passed on the retained score (188.333 s vs 195 s, 58 bars, no flags). Native MIDI and rendering remain unverified. Add explicitly authorized continuation of the exact retained plan; preserve prior stop evidence. No new inference authorized by this record.

## P0 — autonomous CLI MVP (next implementation)

1. Inspect actual YuE2 Studio v5.0 writing guides, examples, supported native request schema and current provider contract before coding. Use a small versioned YuE2-specific knowledge starter (source, license, engine/version, evidence, limits). No unverified capability claims.
2. Implement provider abstraction, explicit local configuration and secret handling; test with a deterministic fake provider, malformed output, timeout, rate limit and bounded budgets. No mandatory external calls during offline tests. Real provider smoke check before GPU submission. Never silently fall back to a paid model.
3. Composer specializes in style conditioning, not merely a persona: musical vocabulary, arrangement role/contrast, vocal delivery, emotional arc, appropriate YuE2 cues and supported syntax. Native engine owns melody unless explicitly constrained. Lyricist independently authors original, specific, coherent and singable lyrics, with narrative, imagery, prosody, rhyme and editorial checks. Preserve supplied lyrics. Avoid generic filler, forced rhyme, imitation/copying and detector optimization; no guarantee of human-like quality. Creative review reconciles both outputs into validated brief/intent, with bounded corrective text calls.
4. Persist jobs and stage identities before external mutations. Reuse native draft, verified reference configuration, idle locks, receipt recovery, acoustic/ASR and neutral listening code; never replay uncertain or completed inference. Default budget: one approved song, one explicit ASR, two CPU listening excerpts; revisions only within separately approved limits. No training, downloads, settings changes, publication, or destructive operations without permission. Preflight readiness including Whisper before expensive generation. A confirmed job can run end-to-end without mid-stage human intervention, but ambiguous submission or required new authorization stops safely.
5. Director compares creative intent with separate technical, lyric, and advisory audio evidence; retains original, explains retain/provisional/stop or proposes bounded revision. Finishing only when justified and permitted; a playable provisional result is not automatic artistic acceptance. Human preference remains authoritative for the listener's taste. Store output and concise transcript. One short Windows launcher; no manual multi-command QA.

### P0 acceptance gate (all required)

- A real natural-language instruction (not a bundled prewritten demo) reaches the configured provider, produces a concept, style and original lyrics through distinct Composer/Lyricist responsibilities, and passes creative review.
- One explicitly approved run reaches actual Windows Studio, generates one playable local song, measures it, runs local ASR and MOSS, records reasoned decision and final status/report. No manual intervention between normal stages.
- Fake-provider and Studio contract/integration tests cover malformed replies, busy/not-ready Whisper, lost receipts, resume of completed stages, concurrent ownership and no duplicate generation. Windows/Linux CI passes on the exact code. Retain journal/evidence and verify actual live result; do not call CI alone completion.
- Operator uses a single short launch command and optionally gives a subjective listening verdict. Quality is a distinct dimension; a technically successful but artistically poor song is not a quality pass. No repeated experiments unless they answer a specific unresolved question.

## P1 — artistic intelligence and local catalog

Grow Composer knowledge from documented musical theory, arrangement, production and YuE2-specific empirical conditioning, labeled by version and confidence. Add searchable SQLite/FTS index and optional CPU embeddings only when useful. Lyricist knowledge base should ultimately cover thousands of songs through legally usable sources: metadata, narrative/section patterns, prosody, rhyme and craft annotations; full lyrics only with appropriate rights (owned/licensed/public-domain). Record provenance, licenses, permitted use and data limitations; metadata or bag-of-words is not full lyric structure. No scraping or redistributing copyrighted lyrics without rights. Develop editorial tests, original held-out briefs and cross-model evaluation of Nemotron versus alternatives on identical tasks; measure cost, reliability, and listener preference rather than claim guaranteed no AI-slop. Do not block P0 on corpus acquisition.

## P1 — persistent Artist Memory

The local, explicit profile store and typed-spec compiler are described in [Artist Memory](ARTIST_MEMORY.md). This is a first bounded implementation: no autonomous preference extraction, automatic application, voice identity guarantee or live hosted typed-schema validation.

Versioned, local per-artist profiles, editable by operator; confirmed preferences separate from inferred observations, track provenance and overrides. Example: for the user's own artist profile, a raspy vocal direction may be selected when requested, unless explicitly overridden. Avoid hardcoding an artist, copying private reference lyrics/melody, or treating a style adjective as a guaranteed persistent voice identity. Voice conditioning or LoRA is a separate rights/capability/compute-gated track. Do not publish private profiles in this public repository.

## P2 — private multi-device server

Reuse one backend and local state for persistent worker/service, authenticated web app and MCP. Job queue/status, cancel semantics, approval, audio streaming/range access, comparison, feedback and recovery; Windows startup and user-session compatibility must be tested. Tailscale-only deployment, Studio loopback, no cloud hosting requirement. Validate actual browser UI, authentication, multi-client state, media playback, and reconnect from Mac/other PCs, not just source inspection. Separate remote app authorization from authority to submit GPU jobs. No broad remote file access.

## Engineering rules

Research and audit before code; reuse existing native capabilities and runners; one bounded PR per coherent change; regression and failure-injection tests before live work; merge executable changes only after green CI. Do not rewrite history, delete journals, change user settings, or rerun completed work to compensate for code bugs. Preserve earlier research as evidence, not mandatory repeated tests. Avoid making UI, corpus size or artist memory a P0 blocker. Update this roadmap and changelog/evidence when a milestone actually changes. Report four separate states: implemented, CI-tested, live-validated, artistically assessed. No calendar promises or professional-quality guarantees. Treat operator as musician, not a manual software tester.

Next actionable work: provider and creative-role contract + small YuE2 knowledge starter, then persistent orchestration reusing live-tested native/listening stages. The arrangement revision is an optional experiment, not the critical path. Documentation does not authorize new inference.

### Live score-first milestone and next artistic increment

PR #84 live recovery completed without new synthesis/ASR; duration 184.358667 s, score 188.333333 s, native completion not_flagged, WER disagreement 0.0405, true peak -0.19 dBTP. Operator rated lyrics/vocals/melody/arrangement/ending all good; noted immediate vocal entry, confirmed female vocalist. MOSS judged static arrangement and incomplete ending, conflicting with operator's artistic judgment. Preserve take, no regeneration. Next use versioned intentional opening and separate vocalist/narrator direction with a local opening gate; MOSS remains advisory. One favorable take does not establish general quality. Non-destructive finishing subsequently passed its technical live gate; persistent profiles are now an opt-in local feature, not autonomous learning.

### Optional release artwork (P0 adjunct, not a music acceptance blocker)

Add an independent Cover Art Specialist for single or ordered album projects, using existing text provider with a separate visual-direction contract and durable receipts. Export a square artwork prompt for Google Flow and editable typography direction. No Flow credentials or image generation by default; optional audited adapters later. See [cover art](COVER_ART.md). Audio finishing, knowledge bases and Artist Memory remain separate priorities.

### Release Export Specialist

Independent deterministic export of completed single/album/EP jobs, original lossless audio, plain lyrics and existing native timed lyric display anchors as LRC/SRT. No fabricated timings, no new inference, no publishing; missing timing yields explicit partial export. See [release export](RELEASE_EXPORT.md). Finishing and artwork attachment are future independently verified variants.

Export refinement: preserve Studio native enhanced LRC verbatim, derive SRT using the pinned UI display heuristic with duration cap. No separate SRT export MCP required. Missing/invalid timing remains a partial export, not a fabricated subtitle.

### Audit hardening sequence

The retained score-first reference passed all five human listening dimensions; cover prompt and single-song original FLAC/TXT/LRC/SRT export completed on the operator host. Opening/vocal policy v2 and multi-track export have fixture coverage, not live acceptance. The next engineering priority is creative semantic acceptance, opening evidence, retained-source provenance and hash-bound human feedback before any mix-only finishing implementation.

Creative-stage hardening: Composer opening/vocal headers and Lyricist opening structure are checked before a successful v2 role receipt. Returned invalid responses are kept in separate local rejection evidence; the existing explicit one-time text recovery remains bounded to the unresolved role. Existing valid receipt identities are preserved. Previously frozen invalid receipts are not automatically rewritten or replayed. No new live inference is required for these regression tests.

Opening evidence (reviewed-score-v3): new jobs additionally require first notated vocal attack within two seconds for direct vocal, or within two seconds after an explicitly vocal-free intro with observable Ins activity. Two seconds is a conservative default for a breath or pickup, not a universal artistic rule; longer intentional silence needs separate policy/review. An all-rest Ins part does not establish that generated accompaniment is silent; it leaves instrumental intro evidence unassessed and the mandatory gate stops before synthesis. Record intro duration, vocal/Ins onset and accompaniment evidence without claiming acoustic verification. Existing v1/v2 job identities, prompts and review outputs are unchanged. The v3 Director context also passes the actual measured loudness_range_lu instead of a missing key. Fixture and CI validation are separate from live musical acceptance. No repeat inference on the reference is authorized.

Completed-source retrieval now has a shared historical verifier for Cover Art, Export and Ending Audit. It resolves exactly one result (parent or continuation), validates byte-linked creative attempts and receipts, native and listening evidence, and the continuation's original source files without replaying current provider prompts or score analysis. The historical native review schema is checked and frozen; live production retains its original current-parser verification. Hash linkage is not protection against coordinated local tampering. No previously successful production is repeated.

Human feedback is now a separate local, append-only exact-source ledger ([usage](HUMAN_FEEDBACK.md)). Explicit listening and release decisions remain distinct from technical or model judgments, and neither an altered take nor a finished candidate inherits original approval. Historical results remain untouched; recording a known listening verdict requires the actual local hash.

The non-destructive finishing milestone is implemented as a separate plan/confirm command, with exact sample-count and fixed-gain PCM equality checks, finite acoustic limits, immutable source/candidate hashes, no automatic preference or release approval, and safe local interruption handling. See the dedicated finishing contract. CI and live validation are reported separately.


### P0 personal production acceptance follow-up

Operator-reported Composer format rejection on PR #133 main is a concrete
P0 blocker, despite earlier successful reference production. A new
versioned structured default Composer contract is proposed; preserve the
old rejected job, its policy and all evidence. Require exact-head CI and
fresh authorized end-to-end natural-language acceptance before declaring
personal production ready. All corpus, artist memory, remote and album
requirements remain open as recorded in project memory.


2026-11-28 P0 live follow-up: structured creative stages passed; duration-only
native plan stop (207.887 seconds vs 195 cap). Add advisory bounded local
fit preview; actual recovery, native MIDI and live acceptance remain open.
Preserve original evidence and approved budget; do not weaken the cap.


P0 follow-up: live duration preview stopped on literal BPM advice. Add explicit
exact-BPM approval with immutable revised child and existing native synthesis
gates. No automatic fit, regeneration or relaxation of explicit tempo
constraints. Verify exact-head CI and real retained-job acceptance.


Live P0 duration recovery passed native MIDI and one native song synthesis,
with saved score/lyrics verification; QA stopped on differing audio hashes.
Current file matches the acoustic receipt; cause is unknown. Explicit
one-time current-hash recovery before ASR retains original journal and
requires technical review. Live QA/recovery and artistic acceptance open.


2026-11-28: operator-reported approved audio-identity recovery succeeded
on main 5d0fd91 (PR #138, two green CI jobs). Existing Indonesian song
completed all remaining QA stages and Director with review_required/exit 0;
no repeated creative or synthesis work. Original waveform equivalence,
headroom, pronunciation and ending remain subject to review. Prioritize
listening and optional separate fixed-gain candidate of this existing take;
do not rerun generation or criticism. This establishes supervised recovery,
not unattended personal-production acceptance. Remaining product and corpus
requirements unchanged.


Operator acceptance checkpoint: fixed-gain candidate verified live, but
Indonesian lyric quality explicitly rejected. Keep English as the default
independent of idea language; Indonesian is opt-in. Prioritize narrative
coherence, idiomatic and singable English, concrete imagery, and meaningful
editorial gates before native generation. Multilingual research remains an
open requirement; technical success does not erase negative human feedback.


### Operator priority: draft Exporter first (2026-11-28)

Finish R07 draft exports before improving creative roles. Provide clean lyric
text and immutable original tagged text, native timing, purpose-based
presets and portable ordered Single/EP/Album packages. Metadata minimal and
optional; actual cover optional, cover prompt sufficient. Do not duplicate
verified native format conversion, cover, metadata or timing features.
Production and distribution presets are the first bounded increment;
additional video preset and timing/naming/live acceptance remain open.
After exporter acceptance return to English-first Composer/Lyricist/Reviewer
quality, without dropping other requirements or artistic rejection evidence.

Operator added native Playlist export. Reuse native album/playlist membership
and order, add relative M3U8. Initial adapter matches completed autonomous
jobs; general Studio-only library export and live acceptance remain open.

Native-library draft adapter: explicit current native song/collection source
for music without Director receipts, byte-preserved formats and native
written lyrics/karaoke. Strict retained-source workflow stays independent.
CI and live acceptance pending; no new inference.
