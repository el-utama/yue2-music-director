# YuE2 Music Director

Local-first Python toolkit for **YuE2-Studio timoncool v5.0.0**, focused on safe ABC score edits, lyric-section diagnostics, MIDI compatibility checks and controlled audio A/B experiments. **Development build: experimental alpha; package version 0.7.0a8.post3. Identify unreleased builds by Git commit, not the unchanged package version.**

> The repository is public. Never commit private audio, unpublished lyrics, local job journals, model weights or credentials.

## Native-first development policy

Music Director is an evidence-driven decision and orchestration layer for YuE2 Studio, not a replacement generator, trainer, DAW or Studio UI. The current development audit supersedes earlier alignment-first planning.

- [Studio capability knowledge](docs/knowledge/STUDIO_CAPABILITIES.md): native workflows, requirements, side effects, limits and reuse decisions.
- [MCP tool index](docs/knowledge/MCP_TOOL_INDEX.md): 339 static definitions at the audited upstream revision; not live availability.
- [Community and official evaluation research](docs/knowledge/COMMUNITY_AND_EVALUATION.md): existing agent skill, model/LoRA prior art, evaluator protocols and license gates.
- [Development audit and revised roadmap](docs/knowledge/DEVELOPMENT_AUDIT.md): overlap analysis, priorities and evidence gates.

Do not add a feature until native and reusable alternatives have been checked. Do not install or train models simply to test a capability. Existing research modules remain available but do not imply production-ready autonomous correction.

## Ringkasan bahasa Indonesia

YuE2 Music Director adalah agent pendamping YuE2 Studio yang bertugas memahami tujuan musik, memilih fitur native yang sesuai, mengelola eksperimen secara aman, menilai hasil berdasarkan bukti, dan menentukan apakah kandidat perlu dipertahankan atau ditolak. Agent ini bukan pengganti generator, trainer LoRA, DAW, maupun antarmuka Studio.

**Status:** masih dalam tahap riset alpha. Evaluasi AudioBox, review gabungan dan inspeksi timing native telah berhasil pada satu perbandingan audio nyata. Kualitas musikal, koreksi fonetik otomatis, dan orkestrasi produksi lagu baru belum tervalidasi. Dokumentasi teknis berbahasa Inggris merupakan sumber utama.

**Kebijakan:** utamakan fitur bawaan YuE2, skill resmi, model dan adapter komunitas yang kompatibel serta berlisensi sesuai penggunaan. Gunakan eksperimen yang sudah ada sebelum meminta pengguna menjalankan inferensi lagi. Jangan mengunduh model, melatih LoRA, mengubah pengaturan, atau menghapus hasil tanpa izin.

**Penggunaan dasar:** Python 3.10+ dan Git diperlukan. Untuk instalasi editable dan tes offline, ikuti bagian Setup. Jalankan `py -3 -m yue2_music_director.cli --help` untuk melihat perintah aktual. FFmpeg dan Studio lokal diperlukan hanya untuk operasi terkait. Jangan mengulang eksperimen yang sudah selesai; periksa laporan dan jurnal lokal terlebih dahulu. Jangan unggah audio, lirik, dataset atau konfigurasi pribadi ke repository publik.

**Rencana terkini:** baca [audit pengembangan](docs/knowledge/DEVELOPMENT_AUDIT.md). Inventaris kemampuan Studio yang benar-benar terpasang, validasi laporan eksperimen lama, audit evaluator resmi dan kompatibilitas adapter, baru tentukan kebutuhan implementasi baru.

## Setup

Requires Python 3.10+; no mandatory third-party Python runtime dependencies. Audio commands require installed FFmpeg/ffprobe, Studio commands require local Studio, and optional MIDI render QA requires FluidSynth and a SoundFont. Optional alignment discovery does not install a backend.

```powershell
git clone https://github.com/el-utama/yue2-music-director.git
cd yue2-music-director
py -3 -m pip install -e .
py -3 -m unittest discover -s tests -v
```

## Documentation map

- [Research handbook](docs/RESEARCH_HANDBOOK.md): goals, architecture, evidence, operating rules and roadmap.
- [Changelog and research milestones](CHANGELOG.md): retrospective history from the early prototypes.
- [Development](DEVELOPMENT.md): architecture and validation gates.
- [Finish existing song](docs/FINISH_EXISTING.md): integrated audio processing and ASR screening.
- [Instrument dynamics](docs/INSTRUMENT_DYNAMICS.md) and [MIDI render QA](docs/INSTRUMENT_RENDER_QA.md): separate audio and MIDI workflows.
- [Offline finishing selection](docs/FINISHING_SELECTION.md): compare completed evidence without new processing.
- [Native Process Audio integration contract](docs/NATIVE_PROCESS_AUDIO.md): source audit, transaction design and outstanding blockers.
- [Historical v0.6.1 acceptance protocol](docs/MUSICAL_ACCEPTANCE_V061.md): frozen score and original research design; superseded for routine human listening by the ASR-primary policy.

## Generation control study (experimental)

See [Generation Control Study](docs/GENERATION_CONTROL_STUDY.md). Compare default native score planning against section-aware planning with the existing private brief. The Windows launcher `generation-control.cmd` plans without inference; `generation-control.cmd --confirm-plans` permits two native planning jobs, no full-song renders. Review results before selecting any generation policy.

## Director-authored first-song study (experimental)

Run `draft.cmd --director-demo` to inspect the bundled original research composition offline, or `draft.cmd --director-demo --confirm-run` to authorize one new song and one local lyric recognition. Uses an explicit pre-reviewed score, native MIDI preflight and retained score verification; no repair or edits to the private brief. See [Study 2](docs/GENERATION_CONTROL_STUDY.md#study-2--new-song-director-authored-composition).

## Native song draft (experimental)

See [Native Song Draft](docs/NATIVE_DRAFT.md). A private six-field brief and one explicit authorization drive one native stock reference generation and one local recognition, with a resumable journal, technical QA and automatic TXT handoff. No optional evaluator is required. Combined live validation is pending.

## Finish a generated song (alpha 8)

Requires FFmpeg/ffprobe, existing stems from the exact source mix, reference lyrics, baseline native ASR JSON and a ready local Studio. No new song generation or stem separation. One possible additional recognition call, explicitly authorized.

```powershell
py -3 -m yue2_music_director.cli finish-existing --mix local/mix.flac --instrumental local/ins.wav --vocals local/vocals.wav --lyrics local/lyrics.txt --baseline-asr local/recognition.json --language en --out results/finish-001 --confirm-recognition
```

Set the loopback MCP endpoint first. A non-regression candidate is provisional; no claim of improved naturalness. See the finishing guide for statuses and recovery. The command has completed on one real YuE2 song. Native Naturalize preview capture, headroom continuation and recognition with a matching pending preview have also completed on one real song. Direct-pass ASR, other native effects, and general compatibility remain unverified.

## Diagnose completed finishing experiments without new inference

```powershell
py -3 -m yue2_music_director.cli director-diagnose --source local/mix.flac --lyrics local/lyrics.txt --baseline-asr local/recognition.json --language en --custom results/finish-001 --native results/native-001 --out results/diagnosis-001
```

Provide at least one completed experiment directory, and optionally a matching `--abc`. Native selection currently supports the headroom-continuation record shape. This reports provisional selection and diagnostic cues, not a correction loop. The integrated real-song diagnosis has passed on Windows with cached AudioBox evidence; native timing inspection also passed. No extra audio or ASR.

## One-command score preparation workflow

Put your own score, lyrics and style text in a **local ignored folder** and run:

```powershell
yue2-director run local/song.abc --lyrics local/lyrics.txt --style local/style.txt --out results/run-001 --seed 42
```

This single command validates ABC, checks lyric-section order, reports approximate phrase density, generates a **separate** pitch candidate and prepares an A/B manifest. **Zero Studio calls and zero audio jobs** by default. Set `YUE2_MCP_URL` or pass `--url` and add `--midi` to also verify both scores through `score_to_midi` (still zero audio jobs). The output directory must be new and empty; existing results are never overwritten. No safe candidate means the run refuses to prepare A/B instead of inventing random edits.

To create audio later, review the manifest and use the separately confirmed `ab-submit` commands below, pointing `--out` to `results/run-001/ab`.

## Working with ABC, offline

```powershell
yue2-director audit path/to/song.abc --lyrics path/to/lyrics.txt
yue2-director humanize path/to/song.abc --lyrics path/to/lyrics.txt --out results/variant.abc --seed 42
```

The humanizer makes **conservative chord-aware pitch edits**, grouped by approximate lyric-line phrases. In **v0.6.1**, the default `--profile conservative` re-screens the same seed-based proposals as v0.6. It defers edits that shift pitch more than three semitones, or increase a neighboring melodic leap beyond five semitones; it does **not** replace deferred edits just to fill `--max-edits`. A `deferred_changes` array in the JSON report lists each rejected proposal and the reason. You may specify `--profile legacy` to reproduce the former v0.6 candidate for a controlled comparison. The number of accepted edits is score-dependent; **eight is a hypothesis for the earlier 114-bar score, not a hardcoded quota**. It protects chorus, intro, interlude, outro, and all instrumental notes, and checks meter/ties/events. The original ABC is never overwritten. It **does not** promise natural singing, syllable alignment, microtiming, vibrato, velocity or audible improvement.

### Conservative vs. legacy candidate (offline)

```powershell
# Profile changes must use NEW output paths; existing experiments are never overwritten.
yue2-director humanize local/song.abc --lyrics local/lyrics.txt --out results/v061.abc --seed 42 --profile conservative
yue2-director humanize local/song.abc --lyrics local/lyrics.txt --out results/v060_replay.abc --seed 42 --profile legacy
```

The report records `proposed_change_count`, `change_count`, and `deferred_changes`. A conservative filter is only a contour heuristic; musical quality and lyric stress are not established by contour screening; routine lyric comparison uses ASR, with optional human musical judgment. The change does not modify velocity, timing or audio-generation behavior.

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
- GitHub Actions run offline tests and actual FFmpeg synthetic-audio tests on Linux; they do **not** contact your local Studio, run inference, or prove audible improvement.
- The repository has no access to your machine's loopback MCP address from GitHub Actions or this chat.

See [DEVELOPMENT.md](DEVELOPMENT.md) for quality gates and architecture.

See [offline director diagnosis](docs/DIRECTOR_DIAGNOSIS.md) for the combined evidence-selection and diagnosis workflow.

See [temporal evidence](docs/TEMPORAL_EVIDENCE.md) for read-only inspection of existing karaoke anchors and alignment limitations.

See [optional singing alignment backend research](docs/ALIGNMENT_BACKEND.md) for the discovery-only command and model validation gates.

The optional `alignment-benchmark` command evaluates existing HTK phoneme labels against independent reference annotations without inference; see [alignment research and benchmark](docs/ALIGNMENT_BACKEND.md).

Use `alignment-reference` to prepare a short excerpt from independently annotated PCM WAV for the offline benchmark. See [reference data and limits](docs/ALIGNMENT_BACKEND.md); no dataset or model is downloaded automatically.

See [native LoRA training and MMS alignment audit](docs/NATIVE_LORA_TRAINING.md) for the separate training research track and revised native-first alignment priority. No training job is implemented or authorized by this documentation.

See [local Studio configuration and compatibility](docs/LOCAL_STUDIO_CONFIGURATION.md) for the read-only `studio-profile` command. Original YuE2 weights are not mandatory; keep a compatible existing fine-tune and record effective settings.

**Panduan konfigurasi lokal:** jangan mengganti model, VAE, LoRA atau pengaturan engine hanya untuk menyesuaikan agent. Gunakan inventaris read-only `studio-profile` sesuai [panduan konfigurasi](docs/LOCAL_STUDIO_CONFIGURATION.md), simpan hasil secara lokal, dan jangan unggah laporan mentah ke repository publik. Inventaris belum merupakan sertifikasi kompatibilitas.

See [public LoRA research](docs/knowledge/LORA_RESEARCH.md) and the [39-entry native catalog index](docs/knowledge/LORA_CATALOG_INDEX.md). Stock YuE2-trained LoRA is not automatically compatible with RS-TW/FW; retain the selected model and require verified adapter provenance before activation.

**Kompatibilitas LoRA:** model Ruach TW/FW bukan bobot YuE2 original. Jangan langsung menumpuk LoRA yang dilatih pada model original; periksa model dasar, decoder, companion, dan lisensi. Lihat riset di atas sebelum mengunduh atau melatih adapter baru.

For the 8 GB CUDA tier, the recommended development reference is stock YuE2 Balanced Q6_K with stock VAE, no optional LoRA, and explicit companion off. See [configuration guide](docs/LOCAL_STUDIO_CONFIGURATION.md). This is a controlled reference, not a quality ranking. Native training's documented minimum is 11 GB VRAM.

**Baseline pengembangan 8 GB:** YuE2 original Balanced Q6_K, VAE original, LoRA tambahan nonaktif dan companion off. Fine-tune dan LoRA hanyalah pilihan untuk kebutuhan spesifik, bukan kewajiban. Jangan menghapus file model atau menjalankan training untuk menyiapkan baseline.

Optional independent audio evaluation: see [Quality Evaluation](docs/QUALITY_EVALUATION.md) for the official AudioBox model integration, local checkpoint requirement and research-only alternatives. No required new dependencies or automatic model downloads.
