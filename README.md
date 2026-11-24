# YuE2 Music Director

A local-first toolbox for safer musical score variation and YuE2-Studio integration.

**Target:** timoncool YuE2-Studio v5.0.0 (MCP integration). **Stage:** repository bootstrap and migration from local prototypes, not production-ready.

## What's here

- Score guard: read-only validation for a restricted subset of YuE2 ABC (Vocal and Ins voices).
- Job receipt: safely parses the live song_create response, including top-level id, without confusing library song IDs with job IDs.
- Standard-library tests and GitHub Actions. Python >=3.10.

## Run tests

    python -m pip install -e .
    python -m unittest discover -s tests -v

Do not deploy this score guard as a replacement for the full prototype's parser. The full humanizer and other established local tools will be ported in follow-up commits. No generation commands are shipped in this initial bootstrap.

See DEVELOPMENT.md for verified local results, scope and migration steps.
