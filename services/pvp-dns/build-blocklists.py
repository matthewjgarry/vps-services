#!/usr/bin/env python3

import ipaddress
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

DB_PATH = "/var/lib/unbound/pvp-dnsbl.sqlite"

# Midway policies, in Midway order.
POLICIES = {
    1: {
        "name": "Security",
        "sources": {
            "atf": "https://threatfox.abuse.ch/downloads/hostfile",
            "hgz011": "https://hagezi-mirror.dnsbunker.org/wildcard/tif.txt",
            "hgz009": "https://hagezi-mirror.dnsbunker.org/wildcard/fake.txt",
        },
        "allowlist": [],
    },
    2: {
        "name": "Adblocking",
        "sources": {
            "el": "https://v.firebog.net/hosts/Easylist.txt",
            "ep": "https://v.firebog.net/hosts/Easyprivacy.txt",
            "oisd0": "https://small.oisd.nl/domainswild",
        },
        "allowlist": [],
    },
    3: {
        "name": "DNS Enforcement",
        "sources": {
            "hgz014": "https://hagezi-mirror.dnsbunker.org/wildcard/doh-vpn-proxy-bypass.txt",
        },
        "allowlist": [
            "www.torproject.org",
            "dist.torproject.org",
            "aus1.torproject.org",
            "static.torproject.org",
        ],
    },
}

DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    re.I,
)


def normalize(raw):
    raw = raw.split("#", 1)[0].strip()
    if not raw:
        return None

    fields = raw.split()

    try:
        ipaddress.ip_address(fields[0])
        if len(fields) < 2:
            return None
        raw = fields[-1]
    except ValueError:
        raw = fields[-1]

    raw = raw.lower().rstrip(".")

    wildcard = 0
    if raw.startswith("*."):
        wildcard = 1
        raw = raw[2:]

    try:
        ipaddress.ip_address(raw)
        return None
    except ValueError:
        pass

    if not DOMAIN_RE.match(raw):
        return None

    return raw, wildcard


def fetch_lines(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "wormlogic-pvp-dns/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        for raw in response:
            yield raw.decode("utf-8", errors="replace")


def main():
    tmp = Path(DB_PATH + ".new")
    tmp.unlink(missing_ok=True)

    db = sqlite3.connect(tmp)

    db.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=FILE;

        CREATE TABLE domains (
            domain   TEXT NOT NULL,
            policy   INTEGER NOT NULL,
            wildcard INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (domain, policy)
        ) WITHOUT ROWID;

        CREATE TABLE allowlist (
            policy INTEGER NOT NULL,
            domain TEXT NOT NULL,
            PRIMARY KEY (policy, domain)
        ) WITHOUT ROWID;
        """
    )

    insert_domain = """
        INSERT INTO domains(domain, policy, wildcard)
        VALUES (?, ?, ?)
        ON CONFLICT(domain, policy)
        DO UPDATE SET wildcard = MAX(wildcard, excluded.wildcard)
    """

    for policy_id, policy in POLICIES.items():
        for domain in policy["allowlist"]:
            db.execute(
                "INSERT OR IGNORE INTO allowlist(policy, domain) VALUES (?, ?)",
                (policy_id, domain.lower()),
            )

        for shortcode, url in policy["sources"].items():
            count = 0
            wildcard_count = 0
            batch = []

            for line in fetch_lines(url):
                item = normalize(line)
                if not item:
                    continue

                domain, wildcard = item
                batch.append((domain, policy_id, wildcard))

                count += 1
                wildcard_count += wildcard

                if len(batch) >= 5000:
                    db.executemany(insert_domain, batch)
                    db.commit()
                    batch.clear()

            if batch:
                db.executemany(insert_domain, batch)
                db.commit()

            print(
                f"{policy['name']:16} {shortcode:8} "
                f"entries={count:8} wildcard={wildcard_count:8}",
                file=sys.stderr,
            )

    db.execute("ANALYZE")
    db.commit()

    total = db.execute("SELECT count(*) FROM domains").fetchone()[0]
    db.close()

    tmp.chmod(0o644)
    tmp.replace(DB_PATH)

    print(f"compiled {total:,} policy/domain rows", file=sys.stderr)


if __name__ == "__main__":
    main()
