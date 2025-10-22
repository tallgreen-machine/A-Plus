# Database Schema Management Guide

## Overview

TradePulse IQ uses a **schema-first** approach to database management, similar to infrastructure-as-code. All database structure changes are tracked in version-controlled files and systematically applied to production.

## Files and Structure

```
sql/
├── schema.sql                    # MASTER schema file (source of truth)
├── schema_production_dump.sql    # Reference dump from production (read-only)
├── migrations/                   # Individual migration scripts
│   ├── 001_initial_setup.sql
│   ├── 002_create_strategy_training_results.sql
│   ├── 003_rename_patterns_to_strategies.sql
│   └── ...
├── seed_test_data.sql           # Test data for development
├── seed_trained_assets.sql      # Trained strategy data
└── dashboard_init.sql           # Dashboard-specific tables

ops/scripts/
├── sync_schema.sh               # Apply schema.sql to production
├── extract_schema.sh            # Extract production schema to local file
└── deploy_to_server.sh          # Full application deployment
```

## Workflow: Making Schema Changes

### Method 1: Schema-First (Recommended for Development)

**When to use**: Adding new tables, columns, or making structural changes during development

1. **Edit the master schema**:
   ```bash
   # Edit sql/schema.sql directly
   vim sql/schema.sql
   ```

2. **Sync to production**:
   ```bash
   # Dry run first to see what would change
   ./ops/scripts/sync_schema.sh --dry-run
   
   # Apply changes
   ./ops/scripts/sync_schema.sh
   ```

3. **Create a migration for the change**:
   ```bash
   # Document the change as a migration for future deployments
   vim sql/migrations/004_add_new_table.sql
   ```

### Method 2: Migration-First (Recommended for Production)

**When to use**: Production changes, complex migrations, data transformations

1. **Create a migration script**:
   ```bash
   vim sql/migrations/004_add_paper_trading_flag.sql
   ```

   ```sql
   -- 004_add_paper_trading_flag.sql
   BEGIN;
   
   ALTER TABLE trades 
   ADD COLUMN is_paper_trade BOOLEAN DEFAULT false;
   
   CREATE INDEX idx_trades_paper ON trades(is_paper_trade);
   
   COMMIT;
   ```

2. **Test locally** (if you have local DB):
   ```bash
   psql -d trad -f sql/migrations/004_add_paper_trading_flag.sql
   ```

3. **Apply to production**:
   ```bash
   scp sql/migrations/004_add_paper_trading_flag.sql root@138.68.245.159:/tmp/
   ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /tmp/004_add_paper_trading_flag.sql"
   ```

4. **Update master schema**:
   ```bash
   # Add the new column to sql/schema.sql
   vim sql/schema.sql
   ```

## Common Operations

### View Current Production Schema

```bash
# Extract current production schema
./ops/scripts/extract_schema.sh

# View the extracted schema
less sql/schema_production_dump.sql

# Compare with master schema
diff sql/schema.sql sql/schema_production_dump.sql
```

### Verify Schema Consistency

```bash
# Compare local and remote
./ops/scripts/sync_schema.sh --dry-run

# Check table counts
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -c '\dt'" | wc -l
grep "^CREATE TABLE" sql/schema.sql | wc -l
```

### Check Production Database Structure

```bash
# List all tables
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -c '\dt'"

# Describe specific table
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -c '\d strategy_performance'"

# Show all indexes
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -c '\di'"

# Show all views
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -c '\dv'"
```

### Create Database Backup

```bash
# Manual backup
ssh root@138.68.245.159 "sudo -u postgres pg_dump trad > /tmp/trad_backup_$(date +%Y%m%d).sql"

# Download backup
scp root@138.68.245.159:/tmp/trad_backup_*.sql ./backups/

# Automatic backup (done by sync_schema.sh)
./ops/scripts/sync_schema.sh  # Creates backup before applying
```

### Restore from Backup

```bash
# Upload backup
scp backups/trad_backup_20251022.sql root@138.68.245.159:/tmp/

# Restore database
ssh root@138.68.245.159 "sudo -u postgres psql -d trad < /tmp/trad_backup_20251022.sql"
```

## Best Practices

### 1. Always Use Transactions

```sql
BEGIN;

-- Your changes here
ALTER TABLE ...
CREATE INDEX ...

-- If anything fails, everything rolls back
COMMIT;
```

### 2. Make Migrations Idempotent

```sql
-- Good: Can be run multiple times safely
CREATE TABLE IF NOT EXISTS new_table (...);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS new_column VARCHAR(50);

-- Bad: Will fail on second run
CREATE TABLE new_table (...);
ALTER TABLE trades ADD COLUMN new_column VARCHAR(50);
```

### 3. Test Before Production

```bash
# Always dry-run first
./ops/scripts/sync_schema.sh --dry-run

# Review the changes
cat sql/migrations/004_new_migration.sql

# Apply to test environment first (if available)
```

### 4. Document Schema Changes

```sql
-- Always include comments explaining WHY
-- Migration: Add paper trading support
-- Date: 2025-10-22
-- Reason: Enable paper trading mode for strategy testing

ALTER TABLE trades 
ADD COLUMN is_paper_trade BOOLEAN DEFAULT false;
```

### 5. Keep Schema Version History

```sql
-- Record migrations in schema_migrations table
INSERT INTO schema_migrations (version, description) 
VALUES ('1.1.0', 'Added paper trading support');
```

### 6. Use Descriptive Column Names

```sql
-- Good
strategy_id, strategy_name, executed_at, unrealized_pnl

-- Bad
sid, sname, time, pnl
```

## Migration Patterns

### Adding a Column

```sql
BEGIN;

ALTER TABLE trades 
ADD COLUMN risk_reward_ratio NUMERIC(6, 4);

-- Add index if needed
CREATE INDEX idx_trades_risk_reward ON trades(risk_reward_ratio);

-- Update schema_migrations
INSERT INTO schema_migrations (version, description) 
VALUES ('1.1.1', 'Added risk_reward_ratio to trades');

COMMIT;
```

### Renaming a Column

```sql
BEGIN;

ALTER TABLE strategy_performance 
RENAME COLUMN old_column_name TO new_column_name;

-- Update any dependent indexes
DROP INDEX IF EXISTS idx_old_name;
CREATE INDEX idx_new_name ON strategy_performance(new_column_name);

INSERT INTO schema_migrations (version, description) 
VALUES ('1.1.2', 'Renamed old_column_name to new_column_name');

COMMIT;
```

### Adding a Table with Foreign Keys

```sql
BEGIN;

CREATE TABLE paper_trading_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    initial_balance NUMERIC(18, 8) NOT NULL,
    final_balance NUMERIC(18, 8),
    total_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(6, 4)
);

CREATE INDEX idx_paper_trading_sessions_user 
    ON paper_trading_sessions(user_id);

INSERT INTO schema_migrations (version, description) 
VALUES ('1.2.0', 'Added paper_trading_sessions table');

COMMIT;
```

### Data Migration

```sql
BEGIN;

-- Add new column
ALTER TABLE trades ADD COLUMN timeframe VARCHAR(10);

-- Migrate existing data
UPDATE trades 
SET timeframe = '1h' 
WHERE timeframe IS NULL AND executed_at < '2025-01-01';

UPDATE trades 
SET timeframe = '5m' 
WHERE timeframe IS NULL;

-- Make it NOT NULL after data is populated
ALTER TABLE trades ALTER COLUMN timeframe SET NOT NULL;

INSERT INTO schema_migrations (version, description) 
VALUES ('1.2.1', 'Added timeframe column to trades with data migration');

COMMIT;
```

## Troubleshooting

### Schema Drift Detected

If local and remote schemas don't match:

```bash
# Extract production schema
./ops/scripts/extract_schema.sh

# Compare
diff sql/schema.sql sql/schema_production_dump.sql > schema_diff.txt

# Review differences
less schema_diff.txt

# Option 1: Update local to match production
cp sql/schema_production_dump.sql sql/schema.sql

# Option 2: Apply local to production
./ops/scripts/sync_schema.sh
```

### Migration Failed

```bash
# Check error logs
ssh root@138.68.245.159 "sudo -u postgres psql -d trad" << 'EOF'
SELECT * FROM pg_stat_activity WHERE datname = 'trad';
EOF

# Restore from backup
ssh root@138.68.245.159 "sudo -u postgres psql -d trad < /tmp/trad_backups/trad_backup_TIMESTAMP.sql"
```

### Foreign Key Violations

```sql
-- Check for orphaned records before adding FK
SELECT t.id 
FROM trades t 
LEFT JOIN strategies s ON t.strategy_id = s.id 
WHERE t.strategy_id IS NOT NULL AND s.id IS NULL;

-- Clean up orphaned records
DELETE FROM trades 
WHERE strategy_id NOT IN (SELECT id FROM strategies);

-- Now add the foreign key
ALTER TABLE trades 
ADD CONSTRAINT fk_trades_strategy 
FOREIGN KEY (strategy_id) REFERENCES strategies(id);
```

## Integration with Deployment

The deployment script (`deploy_to_server.sh`) automatically:
1. Creates database backups
2. Runs `sql/dashboard_init.sql` for basic table setup
3. Preserves existing data

For schema changes, you should:
1. Update `sql/schema.sql`
2. Run `sync_schema.sh` separately
3. Then run normal deployment

## Schema Version Control

Current schema version: **1.0.0** (after pattern→strategy refactor)

Version history is tracked in:
- `schema_migrations` table in database
- Git commits of `sql/schema.sql`
- Individual migration files in `sql/migrations/`

## Examples

### Full Workflow Example: Adding Paper Trading Support

```bash
# 1. Create migration
vim sql/migrations/005_add_paper_trading.sql
```

```sql
-- 005_add_paper_trading.sql
BEGIN;

-- Add paper trading flag to trades
ALTER TABLE trades 
ADD COLUMN IF NOT EXISTS is_paper_trade BOOLEAN DEFAULT false;

-- Add paper trading sessions table
CREATE TABLE IF NOT EXISTS paper_trading_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    initial_balance NUMERIC(18, 8) NOT NULL DEFAULT 100000,
    final_balance NUMERIC(18, 8),
    status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE INDEX idx_paper_sessions_user ON paper_trading_sessions(user_id);

-- Track version
INSERT INTO schema_migrations (version, description) 
VALUES ('1.1.0', 'Added paper trading support')
ON CONFLICT (version) DO NOTHING;

COMMIT;
```

```bash
# 2. Apply migration to production
scp sql/migrations/005_add_paper_trading.sql root@138.68.245.159:/tmp/
ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /tmp/005_add_paper_trading.sql"

# 3. Update master schema
vim sql/schema.sql  # Add the new table and column

# 4. Verify sync
./ops/scripts/sync_schema.sh --dry-run

# 5. Commit to git
git add sql/schema.sql sql/migrations/005_add_paper_trading.sql
git commit -m "feat: Add paper trading support"
```

## Summary

✅ **DO:**
- Edit `sql/schema.sql` as the source of truth
- Create migration scripts for all changes
- Use transactions for all migrations
- Test with `--dry-run` first
- Keep backups
- Document why changes were made

❌ **DON'T:**
- Make manual changes directly on production DB
- Skip creating migrations
- Forget to update `sql/schema.sql`
- Apply untested migrations to production
- Ignore schema drift warnings
