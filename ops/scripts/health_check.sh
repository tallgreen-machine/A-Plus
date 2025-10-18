#!/usr/bin/env bash
set -euo pipefail

# Load env if present
if [ -f /etc/trad/trad.env ]; then
  set -a; . /etc/trad/trad.env; set +a
fi

echo "[health] checking DB connectivity..."
psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-trad}" -d "${DB_NAME:-trad}" -c "SELECT 1;" >/dev/null

echo "[health] checking embeddings exist..."
psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-trad}" -d "${DB_NAME:-trad}" -c "SELECT symbol, count(*) FROM current_embeddings GROUP BY symbol;"

echo "[health] checking model file..."
if [ -f /srv/trad/policy/models/ppo_trader.zip ]; then
  echo "model OK: /srv/trad/policy/models/ppo_trader.zip"
else
  echo "model missing: /srv/trad/policy/models/ppo_trader.zip" >&2
  exit 1
fi

echo "[health] OK"
