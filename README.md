# YuE2 Music Director

Local-first Python toolkit for **YuE2-Studio timoncool v5.0.0**, focused on safe ABC score edits, lyric-section diagnostics, MIDI compatibility checks and controlled audio A/B experiments. **Current version 0.6.0 (beta)**.

> The repository is public. Never commit private audio, unpublished lyrics, local job journals, model weights or credentials.

## Setup

Requires Python 3.10+; no third-party runtime dependencies.

```powershell
git clone https://github.com/el-utama/yue2-music-director.git
cd yue2-music-director
py -3 -m pip install -e .
py -3 -m unittest discover -s tests -v
```

## Working with ABC, offline

```powershell
yue2-director audit path/to/song.abc --lyrics path/to/lyrics.txt
yue2-director humanize path/to/song.abc --lyrics path/to/lyrics.txt --out results/variant.abc --seed 42
```

The humanizer makes **conservative chord-aware pitch edits**, grouped by approximate lyric-line phrases. It protects chorus, intro, interlude, outro, and all instrumental notes, and checks meter/ties/events. The original ABC is never overwritten. It **does not** promise natural singing, syllable alignment, microtiming, vibrato, velocity or audible improvement.

## MCP: only explicit local Studio endpoint

Find the MCP URL in YuE2-Studio Settings, and set it once in each PowerShell session:

```powershell
$env:YUE2_MCP_URL = Read-Host "Enter the Studio MCP URL"
yue2-director studio-check
yue2-director midi-probe path/to/song.abc results/variant.abc --out results/midi
```

Only `localhost`, `127.0.0.1` and `[::1]` endpoints are accepted, with a configurable port/path. No audio job is started by `studio-check` or `midi-probe`.

## Offline MIDI event audit

After converting two ABC versions with `midi-probe`, compare their symbolic note events without any new Studio calls:

```powershell
yue2-director midi-audit --original results/midi/01_original.mid --candidate results/midi/02_variant.mid --out results/midi_audit.json --allowed-pitch-track 1 --enforce-pitch-only
```

The audit compares note counts, pitch, start/duration, velocity, tracks, tempo and meter. Pass `--allowed-pitch-track` as many times as needed for explicit vocal tracks; remove `--enforce-pitch-only` if intentionally auditing a rhythm variant. The tool rejects malformed MIDI, does **not** prove audio quality, and does not call YuE2.

## A/B audio experiment

This operation **is not a dry run after you call `ab-submit`**. Each submit can launch a GPU-intensive Studio job. Make sure the Studio is idle and no active job needs to be preserved before confirming.

```powershell
yue2-director ab-prepare --original results/original.abc --candidate results/variant.abc --style local/style.txt --lyrics local/lyrics.txt --out results/ab-001 --seed 42
yue2-director ab-submit --arm A --out results/ab-001 --confirm-idle
yue2-director ab-status --arm A --out results/ab-001
# Only after A is completed and confirmed in Studio:
yue2-director ab-recover --arm A --out results/ab-001 --confirm-complete
yue2-director ab-submit --arm B --out results/ab-001 --confirm-idle --confirm-a-complete
yue2-director ab-status --arm B --out results/ab-001
```

The output directory must be new and empty. Both arms have identical requests except ABC; source hashes are checked on submit. A journal is created **before** each submit attempt, preventing duplicates on timeout/reconnect. If submit reports unknown status, inspect Studio and use `ab-recover` only when you personally verified completion. Never delete journals or blindly repeat a song submission. A/B works for new experiments; existing v0.5.x journals are **not automatically migrated**.

## Safety and current limitations

- The ABC parser supports the tested YuE2 notation subset, not full ABC notation. Unsupported constructs are rejected.
- Section matching does not verify syllable placement. The Bridge reuse from the earlier demo was **not** prosody-verified.
- Identical seed does not guarantee identical audio realization, so A/B differences are not isolated solely to pitch edits.
- MIDI conversion verifies Studio compatibility, not musical quality.
- GitHub Actions run offline unit tests; they do **not** contact your local Studio, run inference, or prove audible improvement.
- The repository has no access to your machine's loopback MCP address from GitHub Actions or this chat.

See [DEVELOPMENT.md](DEVELOPMENT.md) for quality gates and architecture.
