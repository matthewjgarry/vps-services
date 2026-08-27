#!/usr/bin/env python3
"""Create a SQLite-consistent local export of a running Beszel Hub.

The Hub database is backed up with SQLite's online backup API, not a live
filesystem copy. The Hub identity key is copied from the running container so
its root-only host permissions need not be relaxed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_sqlite(source: Path, destination: Path) -> dict[str, int | str]:
    source_uri = f"file:{source.resolve()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source_db:
        with sqlite3.connect(destination) as destination_db:
            source_db.backup(destination_db)
        integrity = sqlite3.connect(destination).execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {source.name}: {integrity}")
        metadata: dict[str, int | str] = {"integrity_check": integrity}
        if source.name == "data.db":
            for table in ("systems", "users", "alerts"):
                metadata[f"{table}_count"] = source_db.execute(
                    f"SELECT count(*) FROM {table}"
                ).fetchone()[0]
        return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Beszel /beszel_data bind-mount")
    parser.add_argument("--destination", type=Path, required=True, help="Ignored local backup root")
    parser.add_argument("--container", default="beszel", help="Running Hub container name")
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit(f"source directory does not exist: {source}")
    for filename in ("data.db", "auxiliary.db"):
        if not (source / filename).is_file():
            raise SystemExit(f"required Beszel database is absent: {source / filename}")

    os.umask(0o077)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_root = args.destination.resolve()
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(backup_root, 0o700)
    output = backup_root / timestamp
    output.mkdir(mode=0o700)

    try:
        details = {
            "created_at": datetime.now(UTC).isoformat(),
            "method": "sqlite-online-backup-api",
            "source": str(source),
            "container": args.container,
            "databases": {},
        }
        for filename in ("data.db", "auxiliary.db"):
            destination = output / filename
            details["databases"][filename] = backup_sqlite(source / filename, destination)
            os.chmod(destination, 0o600)

        key_destination = output / "id_ed25519"
        subprocess.run(
            ["docker", "cp", f"{args.container}:/beszel_data/id_ed25519", str(key_destination)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        if not key_destination.is_file() or key_destination.stat().st_size == 0:
            raise RuntimeError("Hub identity key was not copied")
        os.chmod(key_destination, 0o600)

        files = {}
        for path in (output / "data.db", output / "auxiliary.db", key_destination):
            files[path.name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        details["files"] = files
        manifest = output / "manifest.json"
        manifest.write_text(json.dumps(details, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(manifest, 0o600)
        print(output)
        return 0
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, sqlite3.Error, subprocess.CalledProcessError) as error:
        print(f"beszel backup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
