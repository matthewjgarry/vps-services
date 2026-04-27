#!/usr/bin/env bash
set -euo pipefail

fail=0

check() {
  if "$@" >/dev/null 2>&1; then
    echo "✓ $1"
  else
    echo "✗ $1"
    fail=1
  fi
}

check "wg" ip link show wg0
check "wg service" systemctl is-active --quiet wg-quick@wg0
check "caddy" docker inspect -f '{{.State.Running}}' wormlogic-caddy
check "whoami" curl -fsS http://127.0.0.1:8080

exit $fail
