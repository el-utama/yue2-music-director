# Hardware and configuration advisor — audited implementation plan

Status: DESIGN / NOT IMPLEMENTED, 2026-11-28. Operator asks for an advisor
that works on a freshly installed Studio PC and can recommend configurations
for different hardware, including RTX 4 GB VRAM / 16 GB RAM, without forcing
the original host's model. This is a continuity checkpoint, not authorization
to install, switch models, change runtime settings, or run a song.

Baseline: main 72ea941 after PR #150 (fresh install documentation; exact-head
Windows/Linux CI 46104180672 passed). Draft Exporter accepted across earlier
targeted live runs. Preserve that evidence; no need to repeat export or prior
synthesis. Creative quality (R02/R03/Reviewer) remains required; portability
is the next infrastructure gap to audit before changing production gates.
Implementation and acceptance of alternative runtimes remain open.

## 1. Audit of existing documentation and code

| Source | Existing evidence / conflict to resolve |
| --- | --- |
| [README](../README.md), [fresh install](FRESH_INSTALL.md), [operator guide](OPERATOR_GUIDE.md) | Separate offline/export/full production. Readiness checks the stock reference only. Fresh host must not inherit old settings. |
| [Local configuration](LOCAL_STUDIO_CONFIGURATION.md) | General policy permits compatible own/community models, but actual production is still strict stock. Reference experiment is not a universal hardware recommendation. |
| [Autonomous CLI](AUTONOMOUS_CLI.md), [native draft](NATIVE_DRAFT.md), [generation control study](GENERATION_CONTROL_STUDY.md) | Historical reference, journals, frozen conditions and intentional stock restore. Do not weaken or reinterpret these contracts. |
| [Architecture](MUSIC_DIRECTOR_ARCHITECTURE.md), [roadmap](AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md), [development](../DEVELOPMENT.md), [project memory](../PROJECT_MEMORY.md) | Capability-aware design already stated; not implemented across production. R04/R08/R12 portability gap. |
| [Studio capabilities](knowledge/STUDIO_CAPABILITIES.md), [MCP index](knowledge/MCP_TOOL_INDEX.md), [native control contract](knowledge/NATIVE_CONTROL_CONTRACT.md), [development audit](knowledge/DEVELOPMENT_AUDIT.md) | Native-first reuse, read-only inventory, installed vs advertised capability, actual effective settings and evidence levels. |
| [LoRA research](knowledge/LORA_RESEARCH.md) | Stock adapters can degrade RS fine-tunes; require verified base/slot/rights; no automatic stacking or model selection by name. |
| [Audio critic](AUDIO_CRITIC.md), [alignment](ALIGNMENT_BACKEND.md) | Separate CPU MOSS managed asset gate; no universal acoustic or phonetic validation. |
| [Native checkpoint](NATIVE_AUDIT_CHECKPOINT.md), [local checkpoint](LOCAL_RELEASE_CHECKPOINT.md), [research handbook](RESEARCH_HANDBOOK.md) | Historical evidence belongs to earlier host/configurations; not prerequisites for new PC. |
| studio_profile.py | 13 existing read-only observations, advertised schema fingerprint, private full report; partial reads explicit. No normalized hardware decision or compatibility proof. |
| readiness.py | FFmpeg, Windows, locks, local provider configuration, optional MOSS files, strict artist_run._preflight. Generic blocker conflates distinct causes. No actual GPU fit or provider auth tested. |
| experiments.py | reference_configuration, stock_profile_checks, confirm_stock_backbone and read_own_model enforce Balanced, backbone-q6, vae-f32, CUDA, configured/effective Q8, flash attention, consistent engine state, no custom binary/flags, one track and no adapters/companion. Keep reference/AB immutable. |
| stock_selection.py | Explicit legacy stock override restoration; native models_own_select write only on authorized path. Advisor must never call it. |
| artist_run.py, native_draft.py, autonomous.py | Plan and synthesis both use strict reference configuration; recovery/continuation and retained evidence depend on frozen configuration. Merely changing readiness would be unsafe and insufficient. |
| native_recognition.py, audio_critic.py | Exact local Whisper/CrisperWhisper Turbo and managed MOSS Q4_K_M CPU requirements; not interchangeable with arbitrary ASR or captioner. |
| mcp.py, music.cmd | Loopback, no redirect/retry, short dispatcher. Proposed advisor must use same safety boundary. |

Audit used known repository entry points and relevant source files, not an
unbounded exhaustive tree enumeration; verify additional references with
git grep when a full local checkout is available. No local hardware or
Studio access from the audit bridge. No new inference.

## 2. Pinned upstream evidence and model tiers

[Models and runtimes guide at ca37d2d](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/guides/en/models-and-runtimes.md)
and [MCP definitions at bfd35a0](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/mcp.rs)
are pinned source evidence, not a guarantee about the installed version.
Refresh source/contracts on version changes. Native CUDA is the primary
tested upstream path; Vulkan and CPU music generation are experimental.
Upstream set tiers at this pin:

| VRAM (upstream recommendation) | Stock set | Total set download (approx.) |
| --- | --- | --- |
| 12 GB or more | Full BF16 | 9.9 GB |
| 8 GB or more | Quality Q8_0 | 5.1 GB |
| 7 GB or more | Balanced Q6_K | 4.3 GB |
| 5.5 GB or more | Light Q5_K_M | 4.0 GB |
| Below 5.5 GB | No recommended stock GPU tier | Unknown |

Download sizes are not VRAM requirements. Optional SheetSage/MERT and
companion are included in the total set size; do not require covers/training
assets for an ordinary song. Light backbone is about 2.44 GB plus stock VAE
about 506 MB on disk; this does not prove a 4 GB GPU can render with runtime,
KV cache, decode buffers and OS/display usage. Q5_K_M is the lightest
published stock quantization at this guide pin. Native training requires
NVIDIA CUDA with at least 11 GB VRAM per this guide; still check actual
compatibility and rights. No unapproved downloads or training.

Native engine options contract: backend auto/cuda/vulkan/cpu; keep_loaded
auto/yes/no; kv_cache auto/f16/q8. Q8 only when NVIDIA CUDA and flash
attention are active. Auto makes memory-dependent choices; effective state
and selected/running GPU can differ. Do not claim identical seed produces
identical audio across cache/backend/model changes.

Use live models_catalog, runtime status and actual installed component
identities as primary observations where schema and handler are verified.
Keep pinned tiers as versioned fallback evidence, not invented model IDs.
Own/community GGUF overrides replace the backbone with selected set's VAE
and other components. Confirm base, licenses, adapter and decoder/companion
compatibility; do not classify all community models as commercially usable.

## 3. Proposed advisor contract

Proposed short launcher: music.cmd --advisor (read-only, NOT available yet).
Optional requested goal: offline, export, production, listening, training;
optional private report and explicit simulated hardware input separated from
measured hardware. Never present simulated inputs as observed. The default
command must work without provider credentials, old jobs, local databases,
models or remote audit bridge. When Studio is unavailable, provide bounded
host-only advice with native details unknown and clear next steps.

Layers:

1. **Host discovery:** bounded local Windows hardware reads (RAM, CPU, OS,
   disk free/total on actual model/media/export volumes, GPU identities,
   dedicated VRAM total/free, driver and available runtime evidence).
   Prefer native observations; optional trusted OS APIs/commands such as
   CIM and NVIDIA query, after testing exact schemas/timeouts. No admin,
   full-drive scans, process killing or shell injection. Do not treat
   shared memory, multiple GPUs' VRAM or disk size as dedicated VRAM.
2. **Native discovery:** reuse studio_profile allowlist and schema checking.
   Existing studio_system -> GET /v1/system/resources; system_gpus ->
   GET /v1/system/gpus (NVIDIA only, chosen and running identities);
   models_status -> GET /setup/status; engine_options_get -> GET /engine/options;
   models_own_list -> GET /setup/own-model; music_pair_status -> GET /v1/music/pair.
   Additional audited read-only candidates: models_catalog -> GET /setup/catalog,
   storage_get -> GET /v1/storage, native_music_runtime_status (inspect
   actual required args and handler before use). Read Whisper and MOSS
   managed-file state only as needed for the goal. Bound payloads, no
   arbitrary tool invocation, no secret-bearing settings_get, no writes.
   Do not interpret missing/truncated/failed values as empty or zero.
3. **Normalize evidence:** versioned schema, per-field source, units,
   timestamp, configured/installed/effective distinction, explicit unknowns.
   Match exact chosen and running GPU IDs; detect ambiguous multi-GPU or
   inconsistent readings. Separate observed total/free memory and hardware
   recommendations from actual load/synthesis validation. Snapshot is not
   reservation; recheck before external submissions.
4. **Deterministic policy:** goal-specific recommendation, alternatives and
   reasons. Use native catalog thresholds plus pinned fallback; no hosted
   LLM necessary. Recommend preserving a compatible current setup first.
   Rank candidate configurations by known compatibility, resource headroom,
   missing assets, estimated downloads/disk, rights and user goal.
   Report unknown memory requirements rather than inventing precise savings.
   No automatic model/LoRA/engine install, download, switch, fallback or
   mutation; provide actionable Studio UI instructions only when verified.
5. **Report:** concise human-readable recommendations and private JSON
   containing observed versus proposed settings, per-goal capability,
   blockers, missing dependencies, evidence level and exact next action.
   Statuses such as supported_by_source, candidate_unverified, blocked,
   unknown, validated_for_profile; none implies artistic acceptance.
   Public/shareable summary redacts raw paths, IDs, credentials and private
   library data; do not log full inventory by default.
6. **Configuration acceptance (later separate PR):** explicit operator-selected
   profile and immutable versioned identity, with adapter/runtime/rights
   checks, read-only readiness and fresh preflight before plan and synthesis.
   Never turn an advisory estimate into execution authorization.

## 4. Example low-memory host (simulation, not validation)

RTX 4 GB dedicated VRAM, RAM 16 GB. Host storage, driver, active GPU and
runtime unknown. Offline indexes, text-only creative via authorized provider,
cover prompt and native export remain independent of stock synthesis gate.
Recommend a conservative no-change inspection first. Existing compatible
model is preferred if supported. Light Q5_K_M is below its documented 5.5 GB
tier and is an experimental candidate only, not an automatic CUDA selection
or promised offload. CPU runtime may be a separate experimental candidate
if supported on the actual host; 16 GB RAM is not proof of enough memory.
Batch one; avoid concurrent synthesis, ASR and captioning. Do not install
optional models for unrelated work. Evaluate native automatic cache/unload
policies and actual fit, not fixed Q8 across devices. Do not train LoRA on
4 GB. If full local production is blocked, continue offline/export/text
work without pretending a full song was generated. No automatic cloud
fallback or remote transfer. Actual acceptance requires independently
authorized bounded validation on the target machine, not a fabricated
benchmark.

## 5. Implementation order and acceptance

A. First PR: normalized read-only hardware/native discovery and fixture
tests, then deterministic report/policy. Add advisor route and help only
when implemented; documentation regression must cover new launcher route.
No change to generation or existing readiness gates. Test fresh empty
machine and no Studio, absent optional tools, malformed/oversized responses,
multiple GPUs, unknown resources, missing models, busy status, no provider.
Mock all side effects and assert zero mutation/inference/network-to-provider.

B. Second PR: recommendation matrix and human/JSON output; fixtures NVIDIA
4/6/8/12+ GB (test boundary 5.5 and 7), AMD/Intel Vulkan, CPU-only, unknown,
multi-GPU, low free VRAM/RAM/disk, active compatible own model, incompatible
LoRA and noncommercial license, missing model/runtime, configured != effective.
Distinguish source-based support, recommendation and tested fit. Report
export/offline independent of generation blockers; verify no private values
in shareable summary. Use Windows/Linux exact-head CI, no GPU needed.
Combine A/B only if coherent and bounded.

C. Later: separate reference policy from supported production profiles.
Keep stock-balanced-cuda-q8-v1 and historic receipts unchanged. Trace all
reference_configuration calls, stock restore, native_plan, native_draft,
autonomous resume/continuation, OOM, retained source and release consumers.
Introduce new versioned production compatibility contract only after
source/schema audit of candidate profile, actual model/decoder identities,
resources, and request fields. Freeze profile per job; reconcile config
drift and ambiguous receipts without resubmission. Do not simply remove
guards or allow arbitrary models/backend. Existing strict path remains
default until alternatives are accepted. Reviewer degradation modes and
other ASR backends require separately defined evidence and explicit policy,
not a silent bypass. Test old journals, drift between planning/synthesis,
crash before/after receipt, concurrent writer, blocked configuration, and
no duplicate submissions.

D. Local verification: begin with one read-only advisor run on original
host and (when available) a genuinely fresh low-VRAM PC. Compare native
and OS reports without exposing private inventory. No synthetic song to
check basic setup. Only if a new production profile is to be supported and
operator separately authorizes: one bounded plan/synthesis validation on
the selected target configuration with predeclared success/stop criteria,
no retry after ambiguity or OOM. Record actual peak memory, completion,
resource limits, retained evidence and technical/artistic distinction.
Do not claim validation for all similar GPUs. Full 3.11/3.13 CI before
release/runtime changes per existing policy. Keep R02/R03 creative work and
other requirements visible.

## 6. Resume in a new session

Read AGENTS.md, PROJECT_MEMORY.md, this document and the active roadmap.
Verify main, pending PRs, exact-head Windows/Linux CI. Finish/merge this
documentation PR first when gates pass. Implement A/B before modifying
production gates; C/D remain separate explicitly tracked work. Inspect
actual native schemas rather than assuming current tool count or old PC
paths. No operator action required for planning/offline fixtures. Ask only
for missing essential decisions or a target host read-only check after
implementation; never assume access to a fresh PC. No new song, model
download, settings change or remote service is authorized by this handover.
