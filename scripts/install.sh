#!/usr/bin/env bash
set -euo pipefail

MACHINE_ID_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/machine-id"

require_vps01() {
  if [[ ! -f "$MACHINE_ID_FILE" ]]; then
    echo "✗ Missing machine-id"
    exit 1
  fi

  if [[ "$(<"$MACHINE_ID_FILE")" != "vps01" ]]; then
    echo "✗ Not vps01"
    exit 1
  fi

  echo "✓ vps01 confirmed"
}

install_wireguard() {
  sudo apt-get update
  sudo apt-get install -y wireguard wireguard-tools qrencode
}

install_wg_config() {
  if [[ ! -f secrets/wg0.conf ]]; then
    echo "✗ missing secrets/wg0.conf"
    exit 1
  fi

  sudo install -d -m 700 /etc/wireguard
  sudo install -m 600 secrets/wg0.conf /etc/wireguard/wg0.conf

  sudo systemctl enable --now wg-quick@wg0
}

install_forwarding_service() {
  echo "🔁 Installing WireGuard forwarding service..."

  sudo install -m 644 systemd/wormlogic-wireguard-forwarding.service \
    /etc/systemd/system/wormlogic-wireguard-forwarding.service

  sudo systemctl daemon-reload
  sudo systemctl enable --now wormlogic-wireguard-forwarding.service
}

install_caddy_stack() {
  docker compose up -d
}

main() {
  require_vps01
  install_wireguard
  install_wg_config
  install_forwarding_service
  install_caddy_stack

  echo "✓ install complete"
}

main "$@"
