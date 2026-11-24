# YuE2 Music Director

Local-first music composition humanization toolkit for **YuE2-Studio (timoncool) v5.0.0**.

This repository is under active development. The goal is to analyze and modify YuE2 ABC scores safely, validate the resulting MIDI, and evaluate audio A/B experiments without unnecessary GPU work.

## Status

Initial repository bootstrap. Tested Python prototypes will be introduced via pull requests before the stable branch is expanded.

## Safety

- MCP endpoint is configurable; no endpoint is hardcoded.
- No automatic audio generation without deliberate user action.
- Local audio, model files, runtime journals and generated reports must stay out of version control.
- Never resubmit a song job blindly after a timeout.

See the development pull request for the initial codebase.