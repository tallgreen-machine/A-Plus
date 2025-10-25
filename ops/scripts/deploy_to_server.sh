#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   SERVER=1.2.3.4 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh
# Requires: ssh, rsync, sudo on remote (or SSH_USER=root)
#
# Project Structure (automatically synced):
#   data/     - Data collection and exchange integration modules
#   ml/       - Machine learning and pattern recognition components  
#   tools/    - Utility scripts for maintenance and debugging
#   api/      - REST API endpoints
#   core/     - Core trading system components
#   policy/   - Trading policies and ML training
#   strategies/ - Trading strategy implementations

SERVER="${SERVER:-}"
SSH_USER="${SSH_USER:-root}"
DEST="${DEST:-/srv/trad}"

if [[ -z "$SERVER" ]]; then
  echo "SERVER env var is required (IP or hostname)" >&2
  exit 1
fi

echo "[deploy] syncing repository to ${SSH_USER}@${SERVER}:${DEST}"
ssh -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER}" "mkdir -p '${DEST}'"

# Clean up __pycache__ directories on server first
echo "[deploy] cleaning up __pycache__ directories on server"
ssh "${SSH_USER}@${SERVER}" "find '${DEST}' -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true"
ssh "${SSH_USER}@${SERVER}" "find '${DEST}' -type f -name '*.pyc' -delete 2>/dev/null || true"

rsync -az --delete --delete-excluded \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'node_modules/' \
  --exclude '.env.local' \
  --exclude 'tradepulse-v2/' \
  ./ "${SSH_USER}@${SERVER}:${DEST}/"

echo "[deploy] installing environment config"
ssh "${SSH_USER}@${SERVER}" "bash -s" <<EOF
set -euo pipefail
DEST="${DEST}"
sudo mkdir -p /etc/trad
if [ -f "\${DEST}/config/trad.env" ]; then
  sudo cp "\${DEST}/config/trad.env" /etc/trad/trad.env
else
  echo "No trad.env found, skipping"
fi
EOF

echo "[deploy] installing systemd units"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"

# Stop and disable services to ensure a clean start
sudo systemctl stop trad.service || true
sudo systemctl disable trad.service || true
sudo systemctl stop dashboard.service || true
sudo systemctl disable dashboard.service || true

# Main bot service
sudo mkdir -p /etc/trad
sudo touch /var/log/trad.log || true
sudo cp "${DEST}/ops/systemd/trad.service" /etc/systemd/system/

# TradePulse IQ Dashboard service (FastAPI backend)
sudo touch /var/log/trad-dashboard.log || true
sudo cp "${DEST}/ops/systemd/dashboard.service" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now trad.service
EOF

echo "[deploy] installing logrotate config"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"
sudo cp "${DEST}/ops/logrotate/trad" /etc/logrotate.d/trad
EOF

echo "[deploy] setting up python virtual environments"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export DEBIAN_FRONTEND=noninteractive
export TMPDIR=/var/tmp/pip

# Remove potentially broken Caddy repo to prevent apt-get update from failing
sudo rm -f /etc/apt/sources.list.d/caddy-stable.list

sudo apt-get update
sudo apt-get install -y python3-venv postgresql-client

# Create venv for main bot
python3 -m venv "${DEST}/.venv"
"${DEST}/.venv/bin/pip" install -r "${DEST}/requirements.txt"
EOF

echo "[deploy] installing Redis for RQ job queue"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"

# Check if Redis is already installed
if ! command -v redis-cli &> /dev/null; then
    echo "Redis not found, installing..."
    sudo "${DEST}/ops/scripts/install_redis.sh"
else
    echo "Redis already installed"
    redis-cli --version
fi

# Ensure Redis is running
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping || (echo "Redis not responding" && exit 1)
EOF

echo "[deploy] installing RQ training worker service"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"

# Stop existing worker if running
sudo systemctl stop trad-worker.service || true
sudo systemctl disable trad-worker.service || true

# Install worker service
sudo touch /var/log/trad-worker.log || true
sudo cp "${DEST}/ops/systemd/trad-worker.service" /etc/systemd/system/

# Reload systemd and enable worker (will be started in final restart section)
sudo systemctl daemon-reload
sudo systemctl enable trad-worker.service
EOF

echo "[deploy] checking postgres authentication config"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
echo "--- pg_hba.conf contents ---"
HBA_FILE=$(sudo -u postgres psql -t -P format=unaligned -c 'show hba_file')
sudo cat "$HBA_FILE"
echo "--- end of pg_hba.conf ---"
EOF

echo "[deploy] initializing database and starting TradePulse IQ dashboard"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail
DEST="${DEST:-/srv/trad}"

# Source the environment file to get DB credentials
if [ ! -f /etc/trad/trad.env ]; then
    echo "/etc/trad/trad.env not found. Exiting."
    exit 1
fi

# Isolate credential handling and database command in a subshell
(
    set -a
    source /etc/trad/trad.env
    set +a

    # Debugging output
    echo "DB_HOST: ${DB_HOST:-'not set'}"
    echo "DB_USER: ${DB_USER:-'not set'}"
    echo "DB_NAME: ${DB_NAME:-'not set'}"
    echo "DB_PASSWORD length: ${#DB_PASSWORD}"

    # Run the database initialization SQL with the password set directly
    echo "Attempting to connect to database..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -a -f "${DEST}/sql/dashboard_init.sql"
)

# Enable dashboard service (will be started in final restart section)
sudo systemctl enable dashboard.service
echo "Database initialized."
EOF

echo "[deploy] restarting all services"
ssh "${SSH_USER}@${SERVER}" bash -s <<'EOF'
set -euo pipefail

# Dynamically detect and restart all trad-related services
echo "Detecting trad services..."
SERVICES=$(systemctl list-units --type=service --all | grep -E '(trad|dashboard)' | awk '{print $1}' | grep -E '\.(service)$' || true)

if [ -z "$SERVICES" ]; then
    echo "No trad services found to restart"
    exit 0
fi

echo "Found services:"
echo "$SERVICES"
echo ""

# Stop all services first (clean shutdown)
echo "Stopping services..."
for service in $SERVICES; do
    echo "  Stopping $service..."
    sudo systemctl stop "$service" || true
done

# Clear Python bytecode cache to ensure fresh imports
echo "Clearing Python bytecode cache..."
find /srv/trad -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /srv/trad -type f -name '*.pyc' -delete 2>/dev/null || true

# Start all services (clean start)
echo "Starting services..."
for service in $SERVICES; do
    echo "  Starting $service..."
    sudo systemctl start "$service"
done

echo ""
echo "Service status:"
for service in $SERVICES; do
    echo "---"
    sudo systemctl status "$service" --no-pager --lines=5 || true
done

echo ""
echo "All services restarted successfully."
EOF

echo "[deploy] complete"
