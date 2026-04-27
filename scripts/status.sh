#!/usr/bin/env bash
set -euo pipefail

echo "=== WireGuard ==="
sudo wg show || true

echo
echo "=== Docker ==="
docker ps
