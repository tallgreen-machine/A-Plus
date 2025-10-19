#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   SERVER=1.2.3.4 SSH_USER=root DEST=/srv/aplus ./ops/scripts/deploy_to_server.sh
# Requires: ssh, rsync, sudo on remote (or SSH_USER=root)

SERVER="${SERVER:-}"
SSH_USER="${SSH_USER:-root}"
DEST="${DEST:-/srv/aplus}"

if [[ -z "$SERVER" ]]; then
  echo "SERVER env var is required (IP or hostname)" >&2
  exit 1
fi

echo "[deploy] syncing repository to ${SSH_USER}@${SERVER}:${DEST}"
ssh -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER}" "mkdir -p '${DEST}'"
rsync -az --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  ./ "${SSH_USER}@${SERVER}:${DEST}/"

echo "[deploy] installing environment config"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"
sudo mkdir -p /etc/aplus
sudo cp "${DEST}/config/aplus.env" /etc/aplus/aplus.env
EOF

echo "[deploy] installing systemd units and timers"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"
sudo mkdir -p /etc/aplus
sudo touch /var/log/aplus-encoder.log /var/log/aplus-meta.log /var/log/aplus-backfill.log /var/log/aplus-train.log || true
sudo cp "${DEST}/ops/systemd/"*.service /etc/systemd/system/
sudo cp "${DEST}/ops/systemd/"*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aplus-encoder.timer aplus-meta.timer aplus-backfill.timer aplus-train.timer
EOF

echo "[deploy] installing logrotate config"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"
sudo cp "${DEST}/ops/logrotate/aplus" /etc/logrotate.d/aplus
EOF

echo "[deploy] setting up python virtual environment"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"
export PIP_DISABLE_PIP_VERSION_CHECK=1
sudo apt-get update
sudo apt-get install -y python3-venv

# Create venv
python3 -m venv "${DEST}/.venv"

# Install dependencies
"${DEST}/.venv/bin/pip" install --extra-index-url https://download.pytorch.org/whl/cpu -r "${DEST}/encoder/requirements.txt"
"${DEST}/.venv/bin/pip" install -r "${DEST}/meta_controller/requirements.txt"
"${DEST}/.venv/bin/pip" install --extra-index-url https://download.pytorch.org/whl/cpu -r "${DEST}/policy/requirements.txt"
EOF

echo "[deploy] running health check"
ssh "${SSH_USER}@${SERVER}" "bash '${DEST}/ops/scripts/health_check.sh'" || true

echo "[deploy] done"
