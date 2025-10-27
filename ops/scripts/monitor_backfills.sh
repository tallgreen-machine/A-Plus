#!/bin/bash
# Monitor all running backfill jobs
# Usage: bash ops/scripts/monitor_backfills.sh

SERVER="138.68.245.159"
SSH_USER="root"

echo "========================================================================"
echo "📊 BACKFILL MONITORING DASHBOARD"
echo "========================================================================"
echo "Time: $(date)"
echo ""

# Check screen sessions
echo "=== Active Backfill Sessions ==="
ssh -A ${SSH_USER}@${SERVER} "screen -ls | grep backfill || echo 'No active backfills'"
echo ""

# Check database record counts by exchange and symbol
echo "=== Current Record Counts by Exchange/Symbol ==="
ssh -A ${SSH_USER}@${SERVER} "source /etc/trad/trad.env && PGPASSWORD=\"\$DB_PASSWORD\" psql -h localhost -U \$DB_USER -d \$DB_NAME -c \"
SELECT 
    exchange,
    symbol,
    COUNT(*) as total_records,
    COUNT(DISTINCT timeframe) as timeframes,
    MIN(timestamp) as earliest_data,
    MAX(timestamp) as latest_data
FROM market_data 
WHERE symbol IN ('BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'MATIC/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'BNB/USDT')
GROUP BY exchange, symbol
ORDER BY exchange, symbol;
\""
echo ""

# Total records across all exchanges
echo "=== Total Records Summary ==="
ssh -A ${SSH_USER}@${SERVER} "source /etc/trad/trad.env && PGPASSWORD=\"\$DB_PASSWORD\" psql -h localhost -U \$DB_USER -d \$DB_NAME -c \"
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT exchange) as exchanges,
    COUNT(DISTINCT symbol) as symbols,
    COUNT(DISTINCT timeframe) as timeframes
FROM market_data;
\""
echo ""

# Recent log tail for active backfills
echo "=== Recent Log Activity ==="
ssh -A ${SSH_USER}@${SERVER} "
for log in /srv/trad/logs/*_backfill.log; do
    if [ -f \"\$log\" ]; then
        echo \"--- \$(basename \$log) (last 2 lines) ---\"
        tail -2 \"\$log\" 2>/dev/null
    fi
done
"

echo ""
echo "========================================================================"
