# SQL Directory Structure

## Files

### Master Schema
- **`schema.sql`** - Complete database schema (source of truth)
  - Use this file for reference and schema sync operations
  - Edit this when making structural changes
  - Keep it up to date with production

### Seed Data
- **`seed_test_data.sql`** - Test data for development/testing
  - 21 trades, 5 active positions, portfolio history
  - User: ID 1, portfolio snapshots, equity history
  
- **`seed_trained_assets.sql`** - Trained strategy data
  - 10 active strategies across BTC/ETH/SOL/AVAX
  - Training results, optimized parameters, performance metrics
  - Used for paper trading and ML system

### Dashboard Setup
- **`dashboard_init.sql`** - Dashboard-specific initialization
  - Basic tables for dashboard operation
  - Symbol status tracking
  - Run by deployment script automatically

### Migrations
All numbered migration scripts are in `migrations/` directory:

```
migrations/
├── 001_create_backtest_results.sql
├── 002_create_strategy_training_results.sql
├── 003_rename_patterns_to_strategies.sql  ← Latest major refactor
├── 007_create_portfolio_system.sql
├── 008_create_strategy_system.sql
└── ...
```

**Important Migrations:**
- `003_rename_patterns_to_strategies.sql` - Renamed all "pattern" terminology to "strategy" (Oct 22, 2025)
- `007_create_portfolio_system.sql` - Portfolio tracking tables
- `008_create_strategy_system.sql` - Strategy performance system

## Usage

### Check Current Schema
```bash
# View local master schema
cat sql/schema.sql

# Extract production schema for comparison
./ops/scripts/extract_schema.sh
less sql/schema_production_dump.sql
```

### Apply Schema Changes
```bash
# Dry run to see what would change
./ops/scripts/sync_schema.sh --dry-run

# Apply local schema to production
./ops/scripts/sync_schema.sh
```

### Seed Test Data
```bash
# Upload and run seed scripts
scp sql/seed_test_data.sql root@138.68.245.159:/tmp/
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /tmp/seed_test_data.sql"

scp sql/seed_trained_assets.sql root@138.68.245.159:/tmp/
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /tmp/seed_trained_assets.sql"
```

### Create New Migration
```bash
# Create new migration file
vim sql/migrations/004_add_new_feature.sql

# Template:
cat > sql/migrations/004_add_new_feature.sql << 'EOF'
-- Migration: Brief description
-- Date: $(date +%Y-%m-%d)
-- Reason: Why this change is needed

BEGIN;

-- Your changes here
ALTER TABLE ...
CREATE INDEX ...

-- Track migration
INSERT INTO schema_migrations (version, description) 
VALUES ('1.X.X', 'Description of change')
ON CONFLICT (version) DO NOTHING;

COMMIT;
EOF

# Apply to production
scp sql/migrations/004_add_new_feature.sql root@138.68.245.159:/tmp/
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /tmp/004_add_new_feature.sql"

# Update master schema
vim sql/schema.sql
```

## Schema Management Workflow

1. **Make changes locally** in `sql/schema.sql`
2. **Create migration script** in `sql/migrations/`
3. **Test migration** (if possible)
4. **Apply to production** using migration script
5. **Verify** with `sync_schema.sh --dry-run`
6. **Commit** both schema.sql and migration to git

See [SCHEMA_MANAGEMENT.md](../docs/SCHEMA_MANAGEMENT.md) for detailed guide.

## Current Schema Version

**Version:** 1.0.0 (after pattern→strategy refactor)

**Tables:**
- Core: users, system_settings, user_settings
- Portfolio: portfolio_snapshots, holdings, equity_history
- Trading: trades, active_trades
- Strategies: strategies, strategy_parameters, strategy_performance, strategy_training_results, strategy_exchange_performance, strategy_regime_performance
- Market Data: market_data, symbol_status
- Exchange: exchange_connections
- Training: training_jobs
- Backtesting: backtest_results

**Total:** 20+ tables, 30+ indexes, 2 views

## Important Notes

⚠️ **Never edit production database directly** - Always use migrations or schema sync

⚠️ **Always backup before migrations** - `sync_schema.sh` does this automatically

⚠️ **Test migrations locally first** - If you have a local database

✅ **Keep schema.sql updated** - It's the source of truth

✅ **Document migrations** - Include comments explaining WHY
