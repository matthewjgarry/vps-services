# Beszel recovery on Heighliner

## Scope and authority

The Beszel Hub is deployed by `vps-services` as the `beszel` Compose service. Its
application state is **not** reconstructed from Git alone. Recovery requires the
versioned Compose/Caddy configuration and a crash-consistent export of the mutable
Hub state.

This document deliberately does not configure an external heartbeat or a separate
monitoring plane. Total Heighliner loss remains a known monitoring-plane blind spot.

## State that must be preserved

A recoverable Hub needs all of the following from the same backup set:

- `data.db` — PocketBase/Beszel records: users, system registrations, alert policy,
  histories, and settings.
- `auxiliary.db` — companion PocketBase/Beszel state.
- `id_ed25519` — Hub identity/private key used by the locally monitored agent.
- the exact `vps-services` revision containing `compose.yaml` and the Caddy route.

The live `data.db-wal` and `data.db-shm` files must **not** be copied as an ad-hoc
filesystem snapshot while the Hub is live. `scripts/backup-beszel.py` uses SQLite's
online backup API to create standalone consistent database files, so the WAL is
intentionally absent from the resulting backup.

## Creating a local consistent export

Run from the checked-out `vps-services` root on Heighliner:

```sh
python3 scripts/backup-beszel.py \
  --source config/beszel/data \
  --destination runtime/vps01/backups/beszel
```

The command creates a timestamped, mode-0700 directory containing:

```text
manifest.json
data.db
auxiliary.db
id_ed25519
```

The script checks SQLite integrity and records non-secret checksums and row counts.
It copies the identity key through the running `beszel` container, so the host
operator does not need to weaken the key's root-only mode.

`runtime/` is ignored by Git. This is a **local consistent export**, not proof of
an off-host recovery point. Until an existing off-host backup authority is selected
and verifies this directory, Heighliner loss remains a documented recovery gap.

## Safe isolated restore validation

A non-destructive validation can use a temporary data directory and a disposable Hub
container pinned to the deployed Beszel version. It must not publish a Caddy route,
reuse the production container name, or modify production Hub state.

The verification gate is:

1. copied export databases pass `PRAGMA integrity_check`;
2. the restored temporary Hub returns `200` from `/api/health`;
3. the expected system-registration count is present in the restored `data.db`.

## Production restore procedure — requires root/operator approval

1. Record the intended `vps-services` source revision and deployed Beszel image.
2. Stop only the production `beszel` Compose service.
3. Preserve the failed live data directory intact for forensics.
4. Restore `data.db`, `auxiliary.db`, and `id_ed25519` from one verified export,
   preserving root ownership and restrictive key permissions.
5. Start the pinned `beszel` service from the recovered revision.
6. Verify `/api/health`, sign-in, system count, and one known agent reconnection.
7. Do not copy old `data.db-wal` or `data.db-shm` into the restored directory.

Do not use a restore test against the production data directory.
