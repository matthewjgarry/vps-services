#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MACHINE_ID="${MACHINE_ID:-vps01}"

SECRETS_DIR="${REPO_ROOT}/secrets/${MACHINE_ID}"
RUNTIME_DIR="${REPO_ROOT}/runtime/${MACHINE_ID}/secrets"

required_secrets=(
  "postgres.env"
  "n8n.env"
  "caddy.env"
)

mkdir -p "${RUNTIME_DIR}"
chmod 700 "${RUNTIME_DIR}"

for secret in "${required_secrets[@]}"; do
  encrypted_file="${SECRETS_DIR}/${secret}.enc"
  runtime_file="${RUNTIME_DIR}/${secret}"

  if [[ ! -f "${encrypted_file}" ]]; then
    printf 'Missing encrypted secret: %s\n' "${encrypted_file}" >&2
    exit 1
  fi

  sops --decrypt \
    --input-type dotenv \
    --output-type dotenv \
    --output "${runtime_file}" \
    "${encrypted_file}"

  chmod 600 "${runtime_file}"
done

printf 'Decrypted secrets to %s\n' "${RUNTIME_DIR}"
