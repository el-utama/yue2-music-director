# Development and roadmap

This project is being migrated from tested local prototypes into one canonical repository.

## Verified in the user's local Studio

- MCP connection and score-to-MIDI conversion work on YuE2-Studio timoncool v5.0.0.
- Original and modified ABC can be converted to four-track MIDI.
- A/B FLACs have been rendered; this does **not** establish musical improvement.
- The observed song_create response uses a structured job object's id. The job_receipt module parses this safely.

## What's in this bootstrap

- A read-only restricted ABC score guard: not a full YuE2 notation parser.
- A defensive MCP receipt parser.
- Python tests and CI.

## Next migration steps

1. Port the previously tested full v0.1 ABC analyzer, variation engine and regression tests.
2. Port MIDI probe, event audit, chorus alignment and v0.5.2 A/B runner in separate reviewed changes.
3. Build phrase-aware humanization with lyric alignment and bridge prosody checks.
4. Add safe, opt-in generation and resource-aware queueing; never duplicate pending jobs.

## Privacy and safety

- No fixed MCP endpoint; use configuration or CLI.
- Do not check in private lyrics, audio renders, local reports, or model weights.
- Never automatically re-submit a generation on a transport timeout.
