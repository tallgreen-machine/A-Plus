#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   SERVER=1.2.3.4 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh
# Requires: ssh, rsync, sudo on remote (or SSH_USER=root)

SERVER="${SERVER:-}"
SSH_USER="${SSH_USER:-root}"
DEST="${DEST:-/srv/trad}"

if [[ -z "$SERVER" ]]; then
  echo "SERVER env var is required (IP or hostname)" >&2
  exit 1
fi

echo "[deploy] syncing repository to ${SSH_USER}@${SERVER}:${DEST}"
ssh -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER}" "mkdir -p '${DEST}'"
rsync -az --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  ./ "${SSH_USER}@${SERVER}:${DEST}/"

echo "[deploy] installing environment config"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"
sudo mkdir -p /etc/trad
sudo cp "${DEST}/config/trad.env" /etc/trad/trad.env
EOF

echo "[deploy] installing systemd units and timers"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"
sudo mkdir -p /etc/trad
sudo touch /var/log/trad-encoder.log /var/log/trad-meta.log /var/log/trad-backfill.log /var/log/trad-train.log || true
sudo cp "${DEST}/ops/systemd/"*.service /etc/systemd/system/
sudo cp "${DEST}/ops/systemd/"*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trad-encoder.timer trad-meta.timer trad-backfill.timer trad-train.timer
EOF

echo "[deploy] installing logrotate config"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"
sudo cp "${DEST}/ops/logrotate/trad" /etc/logrotate.d/trad
EOF

echo "[deploy] ensuring minimal Python runtime deps (idempotent)"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
export PIP_DISABLE_PIP_VERSION_CHECK=1
if command -v pip3 >/dev/null 2>&1; then :; else sudo apt-get update && sudo apt-get install -y python3-pip python3-dotenv; fi
pip3 install --break-system-packages --root-user-action=ignore --no-cache-dir \
  torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu || true
pip3 install --break-system-packages --root-user-action=ignore --no-cache-dir \
  gymnasium==0.29.1 stable-baselines3>=2.5 psycopg2-binary cloudpickle farama-notifications || true
EOF

echo "[deploy] running health check"
ssh "${SSH_USER}@${SERVER}" "bash '${DEST}/ops/scripts/health_check.sh'" || true

echo "[deploy] done"
