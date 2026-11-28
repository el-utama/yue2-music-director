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
On Windows (or simulation), the Advisor also shows a separate native
Studio CPU candidate when an NVIDIA card is below the Light GPU tier, or
Studio reports a CPU host. The candidate is **Light Q5_K_M**, with the
processor explicitly selected, F16 KV cache, keep loaded off and a
one-track limit. The pinned total RAM estimate is about 8.94 GiB: the
2,622,936,832-byte backbone and 530,497,344-byte VAE, plus 4 GiB for the
system and 2 GiB for compute buffers. This is an estimate from
[upstream hardware selection](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/hardware.rs),
using weights from the [pinned model catalog](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/model_manager.rs).
The local catalog can exclude the candidate if Light is unsupported or
its backbone and VAE sizes differ. `advice.cpu_candidate` reports whether
the total RAM estimate is met, unavailable, or above the observed capacity.

The pinned Windows engine selects an explicit backend directly. Auto can
still start CUDA on a 4 GiB NVIDIA GPU even when the model catalog
recommends Light as an in-memory fallback. The pinned launcher disables
Q8 KV cache for the processor and maps keep-loaded `no` to eviction.
These settings describe a candidate for a controlled native Studio test.
The estimate covers neither full disk assets, runtime performance, nor
synthesis peaks. The native Light set may still require its companion
file to be present even when the request disables companion use. See the
[pinned launcher and option handlers](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/lib.rs).
Vulkan needs separate validation.

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
reservation nor proof of fit. A free VRAM warning uses the stock tier the
Advisor recommends keeping or inspecting. The JSON RAM and disk comparisons
are `null` when a required input is unavailable. The live catalog provides a
per-host RAM estimate only when its hardware summary matches the selected
NVIDIA card.
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

## Live Windows Advisor check

On 2026-11-28 the operator ran `music.cmd --advisor --json` on the existing
Windows Studio host after updating to the Advisor release. The shareable
report confirmed the launcher, loopback connection, all ten production
reads, host resources, idle Studio and the selected stock Balanced Q6_K
model matching the engine. It reported CUDA configured, Q8 cache configured
and effective, flash attention on, and an unknown effective backend.
Dedicated VRAM was about 7.96 GiB total and 6.30 GiB free. The Advisor
recommended keeping Balanced with no missing set files. This completed
the targeted read-only check on the existing host. Provider, managed MOSS,
actual model loading and synthesis fit have separate evidence requirements.

## VAE decode runs out of GPU memory

On the existing 8 GB Windows host, a stock Balanced Q6_K replay finished
the acoustic (NAR) stage and loaded the F32 VAE weights. The decoder then
reduced its tile from 512 to the minimum 64 frames and stopped with about
0.31 GiB free. The operator reported that the replay succeeded with
**Keep models loaded between songs** set to **No**.

For this failure signature, check **Settings → Local engine → Engine log**
and the effective **Now** line under the keep-loaded setting. When the
engine keeps models loaded, wait until Studio is idle, choose **No** and
use **Save and restart engine**. Verify that the engine reports **loaded
for each song**. This allows the acoustic model to give up GPU memory
before the VAE decodes. If this policy is already effective when decoding
fails, inspect dedicated GPU memory use by process before another attempt.

The [pinned decoder](https://github.com/timoncool/yue2.cpp/blob/892b9b0311512a1c45e42d6403881d17a991b87c/src/vae.h#L443-L485)
reserves 768 MiB of GPU headroom when checking a tile. A graph smaller than
the displayed free memory can therefore still be rejected. The successful
replay is evidence for this host and configuration. Its final duration and
musical ending require separate verification.

## Alternate production contract audit

The Director reference uses Balanced Q6_K, VAE F32 and no selected
own-model override. The strict preflight checks configured CUDA/Q8,
effective Q8 and flash attention, matching engine context fields,
no custom binary or flags, and one track with adapters and companion use
disabled. These constraints are also part of the controlled A/B baseline.

| Existing boundary | Requirements for a separate opt-in profile |
|---|---|
| [Autonomous job identity](../src/yue2_music_director/autonomous.py) | Freeze the explicit profile before creating native work. Keep creative policy IDs separate. Legacy jobs keep their precise existing identity. |
| [Planner preflight and journal](../src/yue2_music_director/artist_run.py) | Validate the exact stock assets, runtime and effective settings before the first plan submission. Retain the legacy reference configuration and request/receipt identity for existing jobs. |
| [Synthesis preflight and journal](../src/yue2_music_director/native_draft.py) | Recheck the frozen effective configuration before the first song submission. Recover a submitted job only by its existing receipt or ID. An unavailable effective backend, timeout or ambiguous submission must never trigger fallback or another POST. |
| [Continuation and retained outputs](../src/yue2_music_director/retained_source.py) | Verify stored plan, request, score and audio identities without inspecting today's settings for an already completed take. Preserve independent review and exact audio identity before export. |
| [A/B experiments](../src/yue2_music_director/experiments.py) | Keep the stock reference gate and existing evidence. The first alternate profile must have its own compatibility and execution evidence. |

The first candidate to evaluate on an actual low-VRAM host is the native
CPU Light profile described above. Confirm the bundled build and its
effective backend from a reliable running-engine indicator, resolve the
stock asset versions and licenses, and record fresh idle/space readings
before scheduling a separately authorized bounded test. Native status
can describe a ready pair whose weights load on the first song. Keep
the existing Director gate until both load and synthesis are verified.

## Remaining validation

1. **Fresh low-VRAM Windows host.** When available, run
   `music.cmd --advisor --json` once on a genuinely fresh low-VRAM PC.
   Compare the shareable summary with Studio's resource monitor and Local
   engine screen. Preserve the prior exporter and synthesis evidence.
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
