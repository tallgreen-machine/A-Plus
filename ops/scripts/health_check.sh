#!/usr/bin/env bash
set -euo pipefail

# Load env if present
if [ -f /etc/aplus/aplus.env ]; then
  set -a; . /etc/aplus/aplus.env; set +a
fi

echo "[health] checking DB connectivity..."
psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-aplususer}" -d "${DB_NAME:-aplus}" -c "SELECT 1;" >/dev/null

echo "[health] checking for market data..."
psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-aplususer}" -d "${DB_NAME:-aplus}" -c "SELECT symbol, count(*) FROM market_data GROUP BY symbol;"

echo "[health] OK"
