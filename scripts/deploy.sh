#!/usr/bin/env bash
set -euo pipefail

sudo install -m 600 secrets/wg0.conf /etc/wireguard/wg0.conf
sudo systemctl restart wg-quick@wg0

docker compose up -d

echo "✓ deployed"
