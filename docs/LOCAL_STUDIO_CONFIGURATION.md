# Local Studio configuration and compatibility

## Policy

Use YuE2 Studio's native local YuE2 engine as the primary integration target. Original YuE2-3B weights are a reference baseline, not a mandatory installation. A supported community fine-tune may remain active; determine compatibility from the actual engine, checkpoint, decoder, companion, adapter slots and effective settings. Never switch model, quantization, cache type, decoder, companion, provider or adapter silently. The same seed does not guarantee the same audio when these change. For controlled comparisons freeze all non-treatment settings and retain the exact request and model identity. Base-model tests are optional, justified experiments; do not repeat previous generations for setup.

## One-time local inventory (Windows PowerShell)

1. Keep existing Studio settings unchanged. Start YuE2 Studio normally, and verify that its Agent (MCP) setting displays a local MCP URL. Do not enable remote access.
2. Open PowerShell in your existing Music Director checkout. Ensure the worktree is clean with `git status --short`; preserve local changes instead of resetting them. Once this feature is merged, update your main checkout with `git pull --ff-only` and `py -3 -m pip install -e .`. Do not replace old experiment directories.
3. Copy the exact URL from Studio (do not guess the port). Run:

```powershell
$url = Read-Host "Paste Studio MCP URL"
$profile = "results/studio-profile-$(Get-Date -Format yyyyMMdd-HHmmss).json"
py -3 -m yue2_music_director.cli studio-profile --url "$url" --out "$profile"
```

A fresh report is required. The results directory is Git-ignored. The command does not send generation, recognition, training, installation, library or settings operations. It captures the advertised tool input schemas and 13 audited read requests, including active engine status, native capabilities, generation defaults, model status, current music source, engine options, own/community models, system/GPU, LoRA, recognition, separator and training status. The complete report is private and may contain paths, IDs, dataset names or other metadata; never commit or post it publicly. Console output contains only inventory completeness, tool names/schema fingerprint and zero-operation counters. The output is not an anonymization tool for the full report. No need to transmit it to a remote service.

`reads_complete_unverified` means all requested reads returned structurally usable objects, not that the model, adapter, feature or hardware is compatible. `partial_inventory` means one or more calls were absent or failed; consult the local report and leave affected capabilities unknown. Initial status failure or an invalid endpoint aborts. No inference is authorized by this report. The snapshot is non-atomic and does not guarantee the engine remains idle or unchanged.

## Compatibility contract for future agent operations

| Field | Rule |
|---|---|
| Studio build, MCP schema and provider | Check live tool presence and input schema, not an assumed count or upstream version. |
| Active music engine and model | Distinguish requested, installed and effective/running configuration; never infer active model from downloads. |
| Checkpoint, quantization, VAE and companion | Retain exact resolved identity and settings in operation evidence; unknown identity blocks a controlled comparison. Do not double-load baked-in adapters. |
| LoRA | Discover installed ID, slot keys, trigger, strength, provenance, base compatibility and license; no automatic selection by display name. A listed adapter is not proof of compatibility. |
| Sampling, seeds, solver, effective cache | Freeze for comparisons except the deliberately tested variable. |
| Recognition and separation | Check selected provider, model and readiness. No cloud fallback, downloads or repeated ASR/split without permission. |
| Resources and jobs | Check active work and current hardware before expensive operations; a prior snapshot is not a lock. |
| Training and evaluation | Separate from ordinary generation; confirm resources, model/dataset rights, evaluation artifacts and explicit budget. |

Future orchestration must recheck relevant values immediately before submission and stop on unsupported or ambiguous differences; currently the inventory command only records evidence, and is not wired as a mandatory preflight for every existing CLI command. Existing operation-specific guards remain in force. For any Studio/model/LoRA/driver/configuration change, refresh the profile before a new experiment. No user should be required to reproduce another user's particular model choice.

## Evidence status

The read-only handler contracts were checked in pinned Studio source ca37d2d. The profile has mocked regression tests; current installed Studio runtime and actual response completeness have not yet been verified. No new inference, downloads or settings changes are needed to perform inventory.

### Observed local inventory and LoRA response limits

First real run: 339 advertised tools; 12 of 13 reads succeeded; detailed `lora_list` failed result validation. The pinned Studio MCP source caps serialized replies at 60,000 bytes and omits structuredContent when truncating; a large multilingual detailed catalog is a plausible cause, not confirmed from the discarded raw reply. Use `response_format: concise` (installed/catalog, slots, trigger, scales, download status) for inventory. Validate both installed and catalog arrays; never interpret a cut response as an empty adapter list. If concise also fails, leave LoRA availability unknown. No new inference or settings changes in the observed run.

## Community adapter compatibility

The real concise LoRA inventory succeeded after the detailed response failure. Preserve private inventory locally. The RS-FW/TW author explicitly warns against assuming stock-trained LoRA transfer; see [public LoRA research](knowledge/LORA_RESEARCH.md). Do not switch the active model automatically. A separate stock reference may be used only if installed and approved. Training and listening packs reported installed are readiness observations, not proof that a specific model, trainer base or alignment output is suitable. The pre-operation compatibility gate remains to be implemented.
