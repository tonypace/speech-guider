# Workspace cleanup — 2026-11-06

Legacy research and generated build artifacts were moved into the ignored local
staging directory `archive/2026-11-06/`. Nothing was deleted or transferred off-device. Backup payload totals **33.127 GiB**
across **87,778 files**, independently verified against SHA-256 checksums.
Another approximately **1.5 GiB** of regenerable artifacts is staged separately.

The archive's `README.md` explains backup priorities and restoration. `MOVES.json`
records original paths, and `SHA256.jsonl` plus `verify.py` support verification
after transfer to a backup device.

| Archive area | Contents | Long-term backup |
| --- | --- | --- |
| `backup/AAI/` | Legacy research, checkpoints, original corpus downloads, prepared datasets | Preserve until independently backed up |
| `backup/external/` | Previous portable MLP and Haskins BiGRU releases | Useful model history |
| `backup/models/` | Retired DistilHuBERT checkpoint | Useful model history |
| `backup/resources/`, `backup/Plans/`, root summaries/helper | Development references and historical documentation | Small; worth preserving |
| `regenerable/` | Tauri builds, Python caches, test/coverage reports | Optional; reproducible |

Current R4 assets remain at `external/R4 26-11-06/`. TTS models/build, Python/Node
environments, source/tests, ongoing specs, and agent configuration remain active.
Historical model-dependent tests skip while their checkpoints are archived.
Restore assets to the original paths in `MOVES.json` to rerun those checks.

This archive is excluded from Git, Ruff, mypy, and ESLint scans. Its contents
must be backed up separately; a Git commit cannot preserve the ignored payload.
Staging on the same device does not reclaim disk space. Verify the off-device
copy before removing local archived material.
