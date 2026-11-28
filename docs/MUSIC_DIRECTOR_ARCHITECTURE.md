# Generation-first Music Director architecture and implementation roadmap

The [Hardware Advisor](HARDWARE_ADVISOR.md) provides goal-specific read-only discovery and deterministic recommendations outside the generation pipeline. Versioned alternate production contracts require separate profile and receipt validation.

> Product sequencing update (2026-11-26): [Autonomous Music Director roadmap](AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md) governs the next product milestones and records live validation since this document was written. This document remains authoritative for native execution, safety, evidence and historical research gates; its original implementation status and phase ordering are historical.

**Decision date:** 2026-11-26. **Status:** approved direction; implementation and validation pending. This is the authoritative sequencing for new-song development; it supersedes the earlier alignment/repair-first sequence and the universal strict section-order premise of Study 1. Existing commands and historical experiment gates are unchanged until implemented and tested. See [research evidence](GENERATION_CONTROL_STUDY.md), [handbook](RESEARCH_HANDBOOK.md), [native capability audit](knowledge/STUDIO_CAPABILITIES.md) and [native draft contract](NATIVE_DRAFT.md).

## 1. Product objective and evidence

Create original, emotionally convincing songs from a user's artistic intent, using native YuE2 composition and synthesis as the default creative engine. The director owns artistic planning, musical reasoning, selective intervention, evaluation, budget and recovery. It does not primarily repair finished audio or replace the engine, DAW, trainer, or Studio UI. A good first take matters more than a perfectly compliant score. A technical pass is necessary for a deliverable but not sufficient for musical acceptance.

| Evidence | Implication | Limit |
|---|---|---|
| Study 1: native section steering improved label adherence; both plans failed the former strict gate | Structural control is available when required | No musical comparison of those plans; do not rerun them |
| Study 2: explicit authored score accepted by live native MIDI and synthesis; saved conditioning verified; recognition recovery completed without a new song | The explicit score route is feasible and useful when composition must be fixed | One authored fixture is not an autonomous composer |
| Study 2: WER disagreement 4.92%; peak +0.03 dBTP; listener found it monotonous and final chorus forced | Technical/ASR metrics cannot decide artistic quality | No established cause of the ending problem |
| Preferred stock reference Twin Flames: native score 62 BPM, D minor, 2/4 despite requested 68 BPM/A minor; second chorus 24 vs 16 bars, 19-semitone vocal range vs 11 in demo; wider full-mix LRA (8.10 vs 4.70 LU) | Creative deviations, contrast and space deserve review rather than blanket rejection | Different brief, duration, style and possibly mastering; actual sung bridge/outro, acoustic register, exact seed/build unknown |

These observations are design hypotheses, not thresholds or causal findings. Do not copy reference melodies, lyrics, voices or raw private assets. The operator likes emotional singer-songwriter material as well as dark blues/jazz; do not hardcode a genre, fixed vocal range, chorus ratio, LU target for emotion, or obligatory key change.

## 2. Target architecture (not yet implemented)

```text
Artistic intent + local reference observations + compute budget
  -> director brief and performance/section intent
  -> capability/configuration preflight
  -> route decision: direct native / reviewed native plan / explicit score
  -> optional native score planning -> offline musical review
  -> retain plan OR justified bounded guidance OR stop
  -> verified single native synthesis
  -> retained audio + independent technical/lyric/artistic evidence
  -> provisional / technical review / artistic review / accepted by listener
  -> stop; preserve source and journal
```

| Responsibility | Proposed contract | Reuse / gap |
|---|---|---|
| Intent | Versioned local brief, original lyrics, style, emotional arc, desired musical contrasts, must/prefer/free constraints, reference observations, budget | Adapt six-field brief in `native_draft.py`; no breaking migration of existing briefs |
| Native gateway | Discover installed schema, pin effective settings, loopback only | `mcp.py`, `experiments.reference_configuration`, existing status/receipt code |
| Planner | Native score when pre-review is useful, otherwise direct native; optional section steering only for explicit requirements | `generation_control.py`, native score_compose/song_create; verify actual supported schemas |
| Score review | Preserve raw plan, meter-aware descriptors, separate hard violations, soft flags, unknowns and rationale | Extend `music.py` and `inspect_plan` via new versioned policy; current major-only subset is insufficient |
| Selective guidance | Named, bounded musical rationale and expected effect; preserve hook and other constraints; native controls first | Explicit score/native MIDI path in `native_draft.py`; no universal note-randomization or unsupported microtiming controls |
| Synthesis and evaluation | One verified song, independent evidence, resumable local recognition | Existing draft, acoustic, native recognition and multilingual text screen; extend evidence without duplicating inference |
| Decision | Separate artistic, lyrical, technical, provenance and operational outcomes; human preference is not an ASR metric | New orchestration/report contract; existing finishing selector is not an artistic judge |

The director's language-model reasoning can propose an original brief and evaluate artistic intent, but it cannot silently become an autonomous external API service. Start with local deterministic contracts and a director-authored plan; any model integration must be separately specified, permissioned, versioned and tested. No required external network/model download.

## 3. Artistic brief and constraints

Proposed v2 intent record is an additive local companion to the existing six-field brief, not an accepted CLI schema today. Store schema version, brief fingerprint, original title/style/lyrics/language, target duration and separately an absolute resource cap, requested model reference, artistic concept, narrative arc, section purposes, vocal delivery, instrument palette, contrast/climax/cadence intent, and observations from references with provenance and uncertainties. Record generation and planner seeds separately where supported. Classify each constraint as:

- **Must:** explicitly non-negotiable user requirement, native format/validity, rights, resource/safety/identity limit. If infeasible, stop with reason; do not quietly relax it.
- **Prefer:** key/tempo, section order/length, range, sound palette, expressive pacing or cadence unless explicitly made mandatory. Explain meaningful deviations; allow musical alternatives.
- **Free:** details delegated to native composition, such as exact notes, rhythm or harmony where unspecified.

Preserve user-authored lyrics. Keep performance cues and sung reference text separately when identifiable (parenthetical instrumental directions are not automatically words to sing); explicit ambiguous cues remain unknown rather than silently removed. The actual native conditioning must be preserved unchanged in provenance. A missing score label is a risk for native lyric scheduling, not proof that words were omitted; review sung text independently after synthesis. A preferred stock example is not a requirement to repeat its unusual deviations. No fabricated user taste or arrangement decisions.

## 4. Route and review policy

1. **Direct native**: default low-cost artistic route when no mandatory score exists and no pre-review is necessary. One song_create with original style/lyrics and recorded options. Review saved score afterwards. This is the existing stock draft path; do not claim a pre-reviewed score.
2. **Reviewed native**: when the intended constraints warrant pre-review, authorize one score_compose, preserve its actual plan, review it offline. Render the unchanged native score via the verified explicit-ABC path if it passes hard checks and the review decision authorizes it. Explicitly record that this differs from direct end-to-end native generation. Native planning internally uses a short synthesis budget; it is not a zero-GPU operation.
3. **Selective intervention**: use native section steering, a validated opening/other compatible native control, or a targeted score edit only when evidence justifies it. Each intervention has a named hypothesis, exact input/output diff and budget. No automatic edit to fill a quota, no mandatory follow_lyrics, no blanket chorus rewrite. A new planning job or another full song needs separate authorization outside the approved budget.
4. **Explicit authored score**: opt-in only when the melody/arrangement is actually prescribed or for a controlled research arm. Retain the proven native MIDI gate and saved-score semantic verification. Do not make the demo a default.

| Hard pre-synthesis gate | Musical review flag (not automatic failure) | Unknown / escalation |
|---|---|---|
| Supported request, idle/known job ownership, immutable inputs, budget and verified compatible model; no uncertain duplicate | Exact requested key/tempo mismatch, label order changes, unplanned rest space | Unsupported local parser syntax: retain raw, report unassessable, do not label native invalid |
| For supplied ABC: native compatible dialect, aligned voice grid, valid notes/durations/ties/chords, no malformed meter; mandatory MIDI conversion | Rest-only expected sung section, extra sung section, very narrow/large register, repetitive contour, crowded or empty phrases | Native MIDI rejection blocks supplied-score render; local analysis alone cannot override it |
| Explicit mandatory user constraints; actual absolute resource cap, not aspirational length | Score clock differs from target; repeated chorus, harmonic stasis, short ending | Unknown duration when enforcing cap or unknown mandatory constraint: stop; check native contract |
| Known consent and provenance; safe local paths | Possible incomplete lyric scheduling, intro/bridge/outro deviations, insufficient contrast | No proven syllable timing, vocal register or actual arrangement from ABC; evaluate separately |

A soft flag requires an explicit review outcome (retain with rationale, bounded intervention, or stop). Never bypass a hard gate because a score is appealing. Do not demote the existing experiment's historical gates in place; version the new policy and retain old reports. Distinguish intentionally absent vocals from missing sung material; preserve repeated section occurrences, not merely names. Native score is a limited two-voice melody/chord representation, not a complete acoustic arrangement.

## 5. Musical evidence and decision contract

For a supported score, compute meter/unit-aware duration, range in MIDI semitones, onset counts/density, tie-aware sounding time and rest spans, phrase-length proxies, repeated-note/leap distributions, section contrast, chorus overlap for shared measures plus changed length, chord/tonal context, instrumental response space and ending/cadence cues. Handle minor and major keys, accidentals, 2/4, 4/4, L:1/16 and 1/32, Z/Z2–Z4, native paired groups and ties. Do not infer phonetic stress, vocal timbre or actual instrumentation from this data. Avoid aesthetic pass thresholds from one positive and one negative example.

After rendering retain original audio and measured duration/rate/channels, LUFS/LRA/true peak, clipping evidence, intensity trajectory and tail. Headroom ceiling remains a technical screening policy (-1 dBTP for current draft), not a naturalness score. Do not automatically normalize, repair, splice or regenerate. ASR disagreement (language-appropriate WER/CER, reference/cue handling and optional localized evidence) is diagnostic, not verified pronunciation. Optional AudioBox or other validated independent evidence is separate. No detector optimization, no fake human authorship claims.

Report separate axes: execution/provenance (verified/unknown/blocked), technical (pass/review), lyric evidence (screened/disagreement/unknown), artistic intent (reviewed/unknown), listening verdict (preferred/acceptable/rejected/unrated). Status vocabulary and schema are proposed; retain `automatic_acceptance=false` and no claim of naturalness until evidence. A listener can reject a technical pass; a musically liked reference can still need headroom review. Prefer short, loudness-controlled, blinded comparisons when practical; do not demand repeated listening for mechanical QA. An unrated take is provisional, not accepted. Keep a reasoned stop decision and next optional experiment, not a self-triggered loop.

## 6. Execution and recovery contract

Reuse the existing durable local transaction pattern. Proposed states are PLAN_ONLY -> PREFLIGHT -> optional PLAN_ATTEMPTED/SUBMITTED/COMPLETED -> REVIEWED -> SONG_ATTEMPTED/SUBMITTED/COMPLETED -> EVIDENCE_PENDING -> REVIEWED/STOPPED. Separate blocked-before-submit from ambiguous-after-submit. Persist request identity and configuration, stage journal before each mutation, receipt and known job ID, retained score/response hashes, saved song/audio identity and evidence. Use one shared local lock, bounded polling, no blind retries; resume only exact known identities, never recreate completed inference. If ASR is blocked before its submission marker (as in Study 2), resume evaluation when idle without resynthesis; unknown ASR submission remains blocked. Preserve immutable source audio and all old experiment journals. A plan-only command must be zero inference and zero mutation to Studio.

Default budget for next directed experiment: at most one native score planning job, one full-song job, one authorized local ASR call; direct route uses zero separate planning jobs. Budget counts external submissions, not internal engine retries. Stop when blocked or evidence is sufficient; extra take/model/config change, training, download or publication needs explicit permission. Reference Balanced Q6_K/CUDA/Q8/stock VAE, optional adapters off and companion off for the 8 GB research tier; recheck actual settings. No training on this machine without new verified feasibility. Record exact upstream revision and installed capabilities rather than assuming they match.

The Windows operator should need one short launcher per approved run and a single TXT transcript with status, reason, retained audio path and report location; no manually typed long commands, no commands that repeat finished work. Private manifests, reference assets, logs and credentials stay in ignored local paths. Do not send raw audio to third parties without authorization.

## 7. Implementation roadmap and exit criteria

Phases are sequential evidence gates; no new inference authorized by this document.

| Phase | Deliverable | Exit criteria |
|---|---|---|
| P0 — documentation (this change) | Current architecture, evidence and roadmap aligned | Cross-links, historical status separated, no private source assets |
| P1 — offline score evidence and policy | Extend supported native grammar, versioned hard/soft/unknown review, musical descriptors, fixture suite | Minor-key/2/4/1/32, rests/ties/grouping and repeated sections tested; valid creative deviation stays reviewable; mandatory mismatch/invalid native score cannot render; unsupported input not mislabeled; old study unchanged |
| P2 — intent and route decision | Backwards-compatible private intent record, explicit route and budget, reasoned review decision | Existing brief works; mandatory/prefer/free differentiated; invalid budget and unsupported controls rejected; deterministic plan-only report; zero calls when plan-only |
| P3 — integrated runner | Reuse native planning, validated supplied-score render, direct draft and evidence recovery under one local entry point | Mocked tool responses plus failure injection: lost receipt, timeout, busy before recognition, mismatched score/audio/seed, resumed completed song, no duplicate work; real native schema audit before live test; Windows/Linux CI green |
| P4 — one original live song | New emotional blues/singer-songwriter brief with purposeful pauses, contrast, sufficient resolution and native creative freedom; choose direct or reviewed route with rationale | Explicit authorization, one song max and bounded planning/ASR, exact job/score provenance, complete log/report and audio, independent technical and lyric screen, operator's listening verdict; no automatic retry on rejection |
| P5 — controlled validation | Compare a matched direct-native vs reviewed-native route or another single named variable on same brief and configuration; reuse existing matched arm if available | Separately approved compute; fix style, lyrics, seed(s), duration cap and model/decoder/sampler as far as possible; record route difference and actual score/conditioning. Loudness-controlled randomized listening where practical; measure first-take acceptance, technical/lyric non-regression, cost/stop rate. Single pair exploratory; replicate on held-out songs before claiming improvement |
| P6 — cross-song readiness | Robustness across multiple songs, languages, meters, failure paths and user preferences | Predeclared evaluation protocol, repeatable evidence, permissioned resources, recovery/no duplicate jobs, honest provenance; no production release on CI or a single liked song |

P1 implementation introduces [offline score review](MUSICAL_REVIEW.md) with the opt-in native fixed-grid parser and versioned constraint review. It is a bounded subset, with key/meter changes reported unassessable; no render authorization is issued. P2/P3 introduce the [artistic runner](ARTISTIC_RUN.md), a bounded deterministic intent/routing and execution implementation reusing the native draft. It supports direct, reviewed-native and explicit-score routes and predeclared soft-flag rationales, but no autonomous LLM or automatic corrective editing. Live validation is pending (P4); custom cue-aware ASR reference separation is an outstanding gap. Do not launch another demo render. Before implementation inspect the pinned native parser and current local score code; use small original synthetic fixtures that cover the relevant grammar, not the operator's reference ABC. Reuse existing helpers and avoid building competing score engines. Preserve previous experimental scripts and closed V1–V3 repair evidence; no revival or seed sweep. Training, voice conversion, phoneme alignment and post-production remain separate research tracks triggered only by a demonstrated need and verified capability/rights.

## 8. Evidence limits and governance

Current verified milestones: one explicit-score full generation and resumed local ASR, live native planning comparison, and a preferred operator-supplied stock-generated reference. No demonstrated superior naturalness, autonomous artistic reasoning, or reliable cross-song first-pass quality yet. No fully controlled comparison isolates the effects of prompt, lyrics, score or mastering. Source inspection and offline tests do not replace local Studio validation. Each phase must update the command guide, changelog, evidence status, tests and this roadmap where policy changes. Keep historical negative results; distinguish design proposals from shipped features.
