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

echo "[deploy] installing systemd units"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"

# Stop and disable services to ensure a clean start
sudo systemctl stop aplus.service || true
sudo systemctl disable aplus.service || true
sudo systemctl stop dashboard.service || true
sudo systemctl disable dashboard.service || true

# Main bot service
sudo mkdir -p /etc/aplus
sudo touch /var/log/aplus.log || true
sudo cp "${DEST}/ops/systemd/aplus.service" /etc/systemd/system/

# Dashboard service
sudo touch /var/log/aplus-dashboard.log || true
sudo cp "${DEST}/ops/systemd/dashboard.service" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now aplus.service
# The dashboard service will be started after its venv is set up.
EOF

echo "[deploy] installing logrotate config"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"
sudo cp "${DEST}/ops/logrotate/aplus" /etc/logrotate.d/aplus
EOF

echo "[deploy] setting up python virtual environments"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export DEBIAN_FRONTEND=noninteractive

# Remove potentially broken Caddy repo to prevent apt-get update from failing
sudo rm -f /etc/apt/sources.list.d/caddy-stable.list

sudo apt-get update
sudo apt-get install -y python3-venv postgresql-client

# Create venv for main bot
python3 -m venv "${DEST}/.venv"
"${DEST}/.venv/bin/pip" install -r "${DEST}/requirements.txt"

# Create venv for dashboard
python3 -m venv "${DEST}/dashboard/.venv"
"${DEST}/dashboard/.venv/bin/pip" install -r "${DEST}/dashboard/requirements.txt"
EOF

echo "[deploy] initializing database and starting dashboard"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"

# Source the environment file to get DB credentials
if [ -f /etc/aplus/aplus.env ]; then
    set -a
    . /etc/aplus/aplus.env
    set +a
fi

# Run the SQL script to create tables if they don't exist
psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -f "${DEST}/sql/dashboard_init.sql"

# Start the dashboard service
sudo systemctl enable --now dashboard.service
EOF

echo "[deploy] configuring caddy reverse proxy"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/aplus}"

# Source the environment file to get dashboard credentials
if [ -f /etc/aplus/aplus.env ]; then
    set -a
    . /etc/aplus/aplus.env
    set +a
fi

# The DASHBOARD_PASSWORD_HASH is already hashed and in the env file.
# It must be passed directly to the ssh command.
envsubst '' < "${DEST}/ops/caddy/Caddyfile" | sudo tee /etc/caddy/Caddyfile > /dev/null

# Reload Caddy to apply the new config
sudo systemctl reload caddy
EOF

echo "[deploy] running health check"
ssh "${SSH_USER}@${SERVER}" "bash '${DEST}/ops/scripts/health_check.sh'" || true

echo "[deploy] done"
