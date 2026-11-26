# Retained audio critic calibration (Studio-native)

Initial audio-aware research calibration, not a full autonomous director or a MIRA reproduction. No new music generation.

## Why reuse Studio

[Studio v5.0.0 source](https://github.com/timoncool/YuE2-Studio/tree/bfd35a0e594cbd1268557833001d5675ebbdd2d3) contains MOSS-Music-8B-Instruct in `crates/music-server/src/listen.rs` and `training.rs`. Studio's own listening pack manages the F16 audio tower (1,724,480,640 bytes) and the Q4_K_M language model (5,188,223,648 bytes) on 8 GB systems. It deliberately selects CPU and 120 seconds for an 8 GB card; the source's measured Q4 peak at 60 seconds is 7.1 GiB before a 2 GiB desktop reserve. Do not override that policy by trying full-song GPU inference.

The official [MCP tools](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/mcp.rs) expose `library_song_describe_style` and `recording_describe_style` but no custom rubric prompt. Their implementation describes the track, optionally rewrites the description using the writing assistant, and may hear only the middle 120 seconds. The installed captioner itself supports custom prompts (Studio's [pinned HOT-Step fork](https://github.com/timoncool/HOT-Step-CPP/blob/479cbeb8f5e7de98f85f2ac8c3da305cb73839e8/engine/tools/ace-caption.cpp)). We use that executable locally instead of downloading the independent HOT-Step archive originally proposed in PR #72. No external model download command is shipped.

[MOSS-Music-8B-Instruct](https://huggingface.co/OpenMOSS-Team/MOSS-Music-8B-Instruct) declares Apache-2.0 model terms; suitability of model and dependencies for the actual intended use still requires review. MIRA's Music Flamingo alternative has noncommercial research restrictions. The new critic is independently implemented and uses no copied MIRA code.

## Operator workflow

After merge, pull and run:

```powershell
.\critic.cmd
```

The preflight validates the retained reviewed/direct comparison, source hashes, exact brief and reports. It infers Studio's data root from the shared managed media folder. It checks these exact v5.0 paths:
- `data/hotstep/hotstep-tools-479cbeb8-xcr0/ace-caption.exe` and sibling ggml DLLs;
- `data/training/models/moss/moss-aud-f16.gguf`;
- `data/training/models/moss/moss-lm-q4_k_m.gguf`.

The installation is not presumed ready. The inventory checks managed paths and expected file sizes; this is not independent authentication of Studio's installation. No arbitrary drive scan, no runtime fallback, no inference, network or Studio mutation. Inspect `results/critic-output.txt` and `results/critic-calibration/inventory.json`. If missing, use Studio's Auto-describe/listening pack installation, then repeat this check. That may require the native models if not already installed; no duplicates downloaded by the director.

Once installed and explicitly approved:

```powershell
.\critic.cmd --confirm-evaluation
```

Requires Windows and FFmpeg. Uses the same installed Studio files, not a new runtime. Each of the two original recordings is divided into two contiguous halves, all at most 105 seconds. Convert each to a temporary mono 16 kHz PCM WAV; no source changes. Run the custom rubric in a separate process per excerpt with CPU explicitly selected, fixed seed, greedy temperature, 1024 token output limit and one-hour timeout. Four bounded excerpt responses total. Pin the actual local runtime/model byte hashes for resumption, not an attestation of upstream authenticity. No GPU jobs, new song, new ASR or library changes. An unresolved attempt stops automatic reruns; completed verified receipts can resume. Raw outputs, logs and structured checks remain private in `results/critic-calibration`; transcript is `results/critic-output.txt`.

Seven song-specific audible checks and two sanity controls use the same rubric for both takes. Status supported/contradicted/uncertain is an unvalidated model claim, not a measured probability. Malformed structured output becomes unknown; raw response retained. Excerpt-local observation cannot establish global narrative arc or whole-song structure, and mono cannot assess stereo placement. No winner, automatic acceptance or prompt revision. Compare against known listener observations and test the critic's specific evidence before any new render. CPU latency, peak RAM and actual accuracy are not yet verified locally. Do not run concurrently with other resource-intensive tasks; no automatic Studio pause or model unloading.

This supersedes the original independent 7.1 GB setup proposal. CI tests only local contracts, not real MOSS inference. No external audio transfer, detector optimization, training or publication.
