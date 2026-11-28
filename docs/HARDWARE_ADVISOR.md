# Hardware and Configuration Advisor

The Advisor inspects local hardware and, when available, the loopback YuE2
Studio MCP endpoint. It provides goal-specific configuration advice for a
new or existing installation. Run it without model weights, provider
credentials, previous agent jobs, a populated library or a remote bridge.
Use [fresh-host onboarding](FRESH_INSTALL.md) for installation and Studio
connection setup.

## Run on Windows

```cmd
music.cmd --advisor
music.cmd --advisor --goal export
music.cmd --advisor --goal offline
music.cmd --advisor --goal listening --media-dir "D:\Studio Data\media"
music.cmd --advisor --goal training
```

| Option | Effect |
|---|---|
| `--goal production` | Default. Inspect Studio activity, GPU/model selection, engine configuration, stock catalog and the existing local Whisper prerequisite. |
| `--goal offline` | Show offline index entry points without a Studio connection. |
| `--goal export` | Advise on exporting retained or existing native audio without a generation prerequisite. No library data is opened by the Advisor. The exporter performs its own checks. |
| `--goal listening` | Show local Whisper asset evidence and, with an explicit managed media directory on Windows, managed MOSS file presence. Human playback and actual ASR/captioner execution are separate. |
| `--goal training` | Screen the documented CUDA/11 GiB guidance and report Studio's trainer-installation flag when available. |
| `--no-studio` | Inspect the host without connecting to Studio. Model and engine evidence will be unknown. |
| `--url URL` | Override the launcher's default `http://127.0.0.1:8791/mcp` or `YUE2_MCP_URL`. The existing explicit loopback client handles protocol negotiation. |
| `--media-dir PATH` / `--export-dir PATH` | Check space on an explicit local volume. The default export directory is `results/exports`. On Windows, volume readings are limited to fixed local drives. An explicit managed media directory also enables a read-only MOSS file check for listening or production. |
| `--json` | Print normalized, shareable JSON. The default is a concise text summary. |
| `--report NAME.json` | Also save a new private snapshot at `results/advisor/advisor-NAME.json`. The directory is Git-ignored. Choose a new name for each capture. |

The command returns exit 0 for a completed advisory report, including
`blocked`, `unknown`, or Studio offline. Invalid arguments or an unwritable
report path return an error. The shareable output excludes raw paths, GPU
names and UUIDs, unknown component IDs, private library data and credentials.
The optional private snapshot includes normalized GPU identifiers and local
component IDs. It omits full MCP responses and should stay on the host.

### Simulate RTX 4 GB VRAM and 16 GB RAM

```cmd
music.cmd --advisor --simulate nvidia --vram-gib 4 --ram-gib 16
```

Simulation uses only the supplied hardware capacities. It does not inspect
Studio, disk, drivers, providers or local runtime state. `--simulate vulkan`,
`--simulate cpu` and `--simulate unknown` also accept `--ram-gib`.

4 GiB dedicated VRAM falls below the documented 5.5 GiB Light stock GPU
tier. Offline indexes, existing-audio export, cover direction and separately
authorized text work can still be evaluated on their own prerequisites.
CPU and Vulkan paths need their own validation. A 16 GiB RAM figure or the
size of a GGUF file does not establish actual synthesis fit.

## Interpret the evidence

| Status | Meaning |
|---|---|
| `independent_workflow` | The workflow does not depend on the stock production gate. Verify that workflow's own prerequisites. |
| `supported_by_source` | A documented tier or native hardware requirement matches available evidence. Verify assets, effective settings and actual load separately. |
| `candidate_unverified` | A current or alternative configuration warrants inspection. No production acceptance is inferred. |
| `blocked` | An observed condition, such as a busy Studio, insufficient capacity or missing selected model, blocks the proposed path. |
| `unknown` | Required evidence is absent or sources conflict. Check the relevant screen or read again after Studio settles. |

Check Studio's **Settings → Local engine** for the selected and running
device and launch options. Compare the configured and effective cache and
model selection before considering a change. Keep a working existing
configuration while inspecting it. For an own/community model, check exact
base and decoder identity, AR/NAR adapter compatibility and license terms.
Installed adapters are inventory evidence. An installed or engine-reported
pair may still defer weight loading until creation.

The Advisor neither applies an option nor starts a model download, provider
request, recognition, training or generation. For the existing Director
production path use [the separate readiness check](AUTONOMOUS_CLI.md#read-only-readiness-check).
Its strict stock Balanced, CUDA/Q8, flash attention and Whisper checks, along
with managed CPU MOSS and the existing plan and synthesis safeguards, still
apply. Retained outputs and historical experiment journals keep their
original identities.

## Audited sources and policy

[Upstream model/runtime guide at ca37d2d](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/guides/en/models-and-runtimes.md)
and [hardware selection at bfd35a0](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/hardware.rs)
are pinned source evidence. Studio's source uses GiB units for these tiers.

| Total dedicated VRAM | Stock set | Approximate full set download |
|---|---|---|
| 12 GiB | Full BF16 | 9.9 GiB |
| 8 GiB | Quality Q8_0 | 5.1 GiB |
| 7 GiB | Balanced Q6_K | 4.3 GiB |
| 5.5 GiB | Light Q5_K_M | 4.0 GiB |
| Below 5.5 GiB | No documented stock NVIDIA GPU tier | Unknown |

The ranking follows the pinned chooser's preference for Q8_0 over BF16.
It retains a matching installed stock configuration first. Display and
runtime allocations affect free VRAM, and a free VRAM reading is neither a
reservation nor proof of fit. The per-host RAM estimate comes from the live
catalog only when its hardware summary matches the selected NVIDIA card.
The catalog exposes component sizes, partial bytes and installability. It
does not provide generic per-profile VRAM fields at this pin. Recommended
model IDs may be a CPU fallback, so the Advisor uses the pinned dedicated
VRAM thresholds and excludes incompatible live catalog entries. Estimates
for complete missing files and remaining downloads are distinct. Full set
estimates include optional components, and omit additional staging overhead.
Do not infer cover, transcriber or training prerequisites from a full set.

Windows host fallback uses the OS memory API, logical CPU count, fixed
volume metadata and, when present in a standard installation path, one
bounded NVIDIA driver query. Linux reads local memory information and can
use the standard NVIDIA binary. Native RAM reports unused memory, which
may differ from the OS's available-memory estimate. NVIDIA GPU selection
uses non-conflicting exact UUID/index evidence; dedicated memory is neither
summed across GPUs nor inferred from shared VRAM. Native monitor free VRAM
is used only when a single matching name and size can be associated with
the device. Platform/device scenarios without adequate evidence remain
unknown or experimental.

| MCP observation | Pinned handler and use |
|---|---|
| `studio_status` | Composite activity read. Busy status uses the existing conservative activity policy. |
| `studio_system`, `system_gpus` | `GET /v1/system/resources`, `GET /v1/system/gpus`. The latter is NVIDIA-only and reports configured and running GPU selectors. |
| `models_status`, `models_catalog`, `models_own_list` | `GET /setup/status`, `GET /setup/catalog`, `GET /setup/own-model`. Separate selected/installed assets, candidate estimates and own-backbone licensing evidence. |
| `engine_options_get`, `music_pair_status` | `GET /engine/options`, `GET /v1/music/pair`. Effective options may be absent. The effective backend is unknown unless Studio explicitly reports CPU fallback. |
| `lora_list`, `karaoke_settings_get`, `training_status` | Concise reads with allowlisted arguments. Output is reduced to relevant state without names, dataset content or remote provider settings. |

The [MCP tool definitions](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/mcp.rs)
and [route handlers](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/lib.rs)
were checked for the exact argument and response shapes. The Advisor
shares the audited [Studio capability inventory](knowledge/STUDIO_CAPABILITIES.md)
allowlist and adds the catalog read. It never invokes tools outside the
selected goal's explicit list. Missing tools, incompatible advertised
schemas and failed or truncated replies are recorded. MCP replies keep
the client's size limit and short per-request timeout. No arbitrary tool
calls, redirects or retries of failed observations.

`storage_get` walks managed download folder trees, so the Advisor uses
bounded volume checks on the reported model root and explicit directories.
`native_music_runtime_status` requires a specific ACE-Step or MiniMax
engine and does not describe the default YuE2 engine. Defer those engines
to a separate supported-profile audit. See [local configuration](LOCAL_STUDIO_CONFIGURATION.md),
[the native control contract](knowledge/NATIVE_CONTROL_CONTRACT.md), and
[the architecture](MUSIC_DIRECTOR_ARCHITECTURE.md) for the execution gates.

## Remaining validation

1. **Read-only Windows acceptance.** Run `music.cmd --advisor --json` on the
   original Studio host and, when available, a genuinely fresh low-VRAM
   Windows machine. Compare the shareable summary with Studio's resource
   monitor and Local engine screen. Private reports, paths, logs, songs
   and credentials stay local. Preserve the prior exporter and synthesis
   evidence.
2. **Versioned alternate production policy.** Retain
   `stock-balanced-cuda-q8-v1` and the existing default. Verify exact
   model/decoder/runtime/adapter identities, execution request fields and
   rights. Freeze the opt-in profile per job and recheck it before native
   planning and synthesis. Audit continuation, retained sources, timeout
   and OOM recovery, and release consumers. Test old journals, drift,
   crashes and one-submission recovery before allowing the new profile.
3. **Target-host execution.** A separately authorized bounded plan and
   synthesis validation must establish actual fit on the chosen hardware
   and configuration. Record completion, peak memory and stop conditions.
   The read-only Advisor and fixture tests establish neither live fit nor
   artistic acceptance.
