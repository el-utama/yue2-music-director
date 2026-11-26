# Retained audio critic calibration

First local, audio-aware critic experiment. Not a full autonomous director, not a MIRA reproduction, not a new song-generation test.

## Evaluator selection

MIRA uses Music Flamingo with per-requirement yes/no token scores. NVIDIA's [Music Flamingo checkpoint](https://huggingface.co/nvidia/music-flamingo-2601-hf) is approximately 16.5 GB and restricted to noncommercial research. [Music Flamingo DLT](https://huggingface.co/DeimantasLT/music-flamingo-dlt-gguf) documents an 8 GB Windows laptop deployment, but retains academic-only model restrictions and uses a separate patched decoder runtime. Do not use it for ordinary commercial song production.

Instead evaluate [MOSS-Music-8B-Instruct](https://huggingface.co/OpenMOSS-Team/MOSS-Music-8B-Instruct), whose model card declares Apache-2.0. It specializes in music captioning, musical QA, lyrics and structural analysis. Authors report 80.38 vs Music Flamingo's 73.87 average accuracy on eight music QA benchmarks; these are their upstream results, not our quantized CPU validation. A native music captioner already exists in [HOT-Step-CPP](https://github.com/scragnog/HOT-Step-CPP/tree/v1.5.2), including custom prompts, explicit model path and CPU backend selection. The [F16 audio tower](https://huggingface.co/scragnog/MOSS-Music-8B-Instruct-GGUF) and [Q4_K_M language weights](https://huggingface.co/nerualdreming/MOSS-Music-8B-Instruct-GGUF) are separate GGUFs. Q4_K_M quality relative to Q8 is not established. Do not load only the text decoder in a generic LLM loader. Model license is more suitable for a production candidate, but no claim about all dependency/data rights.

The pinned CPU-only Windows v1.5.2 release archive, two model revisions, byte sizes and SHA-256 identities are in `audio_critic.py`. Only captioner and sibling DLLs are extracted to the ignored local runtime; no app installation, server, admin privileges, Python dependencies or Studio configuration changes. Independent CPU execution avoids GPU contention; CPU speed, peak RAM and accuracy on this machine are unknown. Use separate processes per arm to release resources. The existing AudioBox estimator remains descriptive supplementary evidence and is not substituted for requirement-based assessment.

## Operator workflow

From the current repository, after pulling the merged change:

```powershell
.\critic.cmd
```

This validates the retained P5 comparison, including exact brief, requests, reference configuration, report and audio hashes, and freezes an identical rubric for the two existing originals. No Studio calls, model downloads or inference. It creates `results/critic-calibration/contract.json` and `prompt.txt`.

Only after reviewing the download scope (about 7.1 GB transfer, plus extraction and space overhead):

```powershell
.\critic.cmd --setup
```

Downloads the pinned CPU release and weights via Windows curl, checks exact size/hash, and extracts only the captioner/DLLs. Valid cached downloads are reused; incomplete downloads may resume if the server supports range requests. Invalid files/staging directories stop for inspection. No code execution/inference during setup; no downloads during evaluation.

```powershell
.\critic.cmd --confirm-evaluation
```

Run the one bounded CPU calibration, at most one full-song captioner response per arm. FFmpeg required on PATH. Original FLACs are not modified. A 215-second input cap covers both known originals; 1024 output tokens, temperature 0, fixed seed, one-hour process timeout per arm. Source SHA verified before and after evaluation. Logs and exact responses remain local. An unresolved prior attempt blocks automatic rerun; completed verified responses are reused. Output: `results/critic-output.txt`, `results/critic-calibration/report.json` and per-arm raw answer/log/receipt. The runtime must be checked on the actual Windows machine; CI only tests offline contracts.

## Calibration logic

Seven song-specific requirements derived from the existing brief (slow blues-soul, lead vocal, instrumental responses, drums, contrast, pauses, ending), plus two deliberately contradictory controls (instrumental/no singing, fast aggressive electronic dance). The model receives identical question text for both tracks, not their route or listener verdict. No exact lyric or stereo claims from the mono captioner. Strict structured responses retain supported/contradicted/uncertain and evidence; malformed responses are all unknown and raw text is retained. No forced JSON repair, invented confidence or numeric overall winner. One bundled prompt is a resource-conscious choice, not the MIRA token-probability algorithm.

Review factual errors, contradictions, agreement with known listener observation and specificity of cues. The same-score pair and two negative controls are a sanity test, not a general benchmark; the user already knows the tracks. If useful, extend to existing preferred/unpreferred songs with their own predeclared rubrics and controlled listening. If model fails or is too slow, stop and investigate without new generation. Do not trigger song revision automatically. A later style intervention requires an actionable supported issue, preservation constraints, bounded budget and separate approval.

No AI-detection optimization, uploading private audio, destructive processing or training.
