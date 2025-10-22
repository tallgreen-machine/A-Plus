-- 003_rename_patterns_to_strategies.sql
-- Comprehensive migration: Rename all "pattern" terminology to "strategy"
-- This aligns our database schema with the A+ Strategy architecture described in README

BEGIN;

-- Step 1: Rename main tables
ALTER TABLE IF EXISTS patterns RENAME TO strategies;
ALTER TABLE IF EXISTS pattern_parameters RENAME TO strategy_parameters;
ALTER TABLE IF EXISTS pattern_performance RENAME TO strategy_performance;
ALTER TABLE IF EXISTS pattern_training_results RENAME TO strategy_training_results;
ALTER TABLE IF EXISTS pattern_exchange_performance RENAME TO strategy_exchange_performance;
ALTER TABLE IF EXISTS pattern_regime_performance RENAME TO strategy_regime_performance;

-- Step 2: Rename columns - pattern_parameters has pattern_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'strategy_parameters' AND column_name = 'pattern_id'
    ) THEN
        ALTER TABLE strategy_parameters RENAME COLUMN pattern_id TO strategy_id;
    END IF;
END $$;

-- Step 3: Rename columns - pattern_performance has pattern_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'strategy_performance' AND column_name = 'pattern_id'
    ) THEN
        ALTER TABLE strategy_performance RENAME COLUMN pattern_id TO strategy_id;
    END IF;
END $$;

-- Step 4: Rename columns - pattern_training_results has pattern_name (not pattern_id!)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'strategy_training_results' AND column_name = 'pattern_name'
    ) THEN
        ALTER TABLE strategy_training_results RENAME COLUMN pattern_name TO strategy_name;
    END IF;
END $$;

-- Step 5: Rename columns in strategy_exchange_performance (if exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'strategy_exchange_performance' AND column_name = 'pattern_id'
    ) THEN
        ALTER TABLE strategy_exchange_performance RENAME COLUMN pattern_id TO strategy_id;
    END IF;
END $$;

-- Step 6: Rename columns in strategy_regime_performance (if exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'strategy_regime_performance' AND column_name = 'pattern_id'
    ) THEN
        ALTER TABLE strategy_regime_performance RENAME COLUMN pattern_id TO strategy_id;
    END IF;
END $$;

-- Step 7: Rename columns in trades table (if pattern_id exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trades' AND column_name = 'pattern_id'
    ) THEN
        ALTER TABLE trades RENAME COLUMN pattern_id TO strategy_id;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trades' AND column_name = 'pattern_name'
    ) THEN
        ALTER TABLE trades RENAME COLUMN pattern_name TO strategy_name;
    END IF;
END $$;

-- Step 8: Rename columns in active_trades table (if pattern_name exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'active_trades' AND column_name = 'pattern_name'
    ) THEN
        ALTER TABLE active_trades RENAME COLUMN pattern_name TO strategy_name;
    END IF;
END $$;

-- Step 9: Update foreign key constraints
-- Drop old foreign keys and recreate with new names
DO $$
DECLARE
    constraint_name text;
BEGIN
    -- strategy_parameters foreign keys
    FOR constraint_name IN 
        SELECT conname FROM pg_constraint 
        WHERE conrelid = 'strategy_parameters'::regclass 
        AND contype = 'f'
        AND conname LIKE '%pattern%'
    LOOP
        EXECUTE format('ALTER TABLE strategy_parameters DROP CONSTRAINT %I', constraint_name);
    END LOOP;
    
    -- Recreate foreign key constraints with correct references
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conrelid = 'strategy_parameters'::regclass 
        AND conname = 'strategy_parameters_strategy_id_fkey'
    ) THEN
        ALTER TABLE strategy_parameters 
        ADD CONSTRAINT strategy_parameters_strategy_id_fkey 
        FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE;
    END IF;
    
    -- strategy_performance foreign keys
    FOR constraint_name IN 
        SELECT conname FROM pg_constraint 
        WHERE conrelid = 'strategy_performance'::regclass 
        AND contype = 'f'
        AND conname LIKE '%pattern%'
    LOOP
        EXECUTE format('ALTER TABLE strategy_performance DROP CONSTRAINT %I', constraint_name);
    END LOOP;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conrelid = 'strategy_performance'::regclass 
        AND conname = 'strategy_performance_strategy_id_fkey'
    ) THEN
        ALTER TABLE strategy_performance 
        ADD CONSTRAINT strategy_performance_strategy_id_fkey 
        FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE;
    END IF;
    
    -- Note: strategy_training_results uses strategy_name (VARCHAR), not strategy_id (FK)
    -- No foreign key constraint needed for this table
END $$;

-- Step 10: Update indexes
-- Rename indexes to use strategy terminology
DO $$
DECLARE
    idx_name text;
BEGIN
    FOR idx_name IN 
        SELECT indexname FROM pg_indexes 
        WHERE tablename IN ('strategies', 'strategy_parameters', 'strategy_performance', 
                           'strategy_training_results', 'strategy_exchange_performance', 
                           'strategy_regime_performance')
        AND indexname LIKE '%pattern%'
    LOOP
        EXECUTE format('ALTER INDEX %I RENAME TO %I', 
                      idx_name, 
                      REPLACE(idx_name, 'pattern', 'strategy'));
    END LOOP;
END $$;

-- Step 11: Update unique constraints
DO $$
DECLARE
    constraint_name text;
    table_name text;
BEGIN
    FOR constraint_name, table_name IN 
        SELECT conname, conrelid::regclass::text
        FROM pg_constraint 
        WHERE conrelid IN ('strategy_parameters'::regclass, 'strategy_performance'::regclass)
        AND contype = 'u'
        AND conname LIKE '%pattern%'
    LOOP
        EXECUTE format('ALTER TABLE %I RENAME CONSTRAINT %I TO %I', 
                      table_name,
                      constraint_name, 
                      REPLACE(constraint_name, 'pattern', 'strategy'));
    END LOOP;
END $$;

-- Step 12: Create summary report
DO $$
BEGIN
    RAISE NOTICE '=== Pattern → Strategy Migration Complete ===';
    RAISE NOTICE 'Tables renamed:';
    RAISE NOTICE '  - patterns → strategies';
    RAISE NOTICE '  - pattern_parameters → strategy_parameters';
    RAISE NOTICE '  - pattern_performance → strategy_performance';
    RAISE NOTICE '  - pattern_training_results → strategy_training_results';
    RAISE NOTICE '  - pattern_exchange_performance → strategy_exchange_performance';
    RAISE NOTICE '  - pattern_regime_performance → strategy_regime_performance';
    RAISE NOTICE 'Columns renamed in all tables (pattern_id → strategy_id, pattern_name → strategy_name)';
    RAISE NOTICE 'Foreign keys, indexes, and constraints updated';
END $$;

COMMIT;

-- Verification queries
SELECT 'Strategies:' as table_name, COUNT(*) as count FROM strategies
UNION ALL
SELECT 'Strategy Parameters:', COUNT(*) FROM strategy_parameters
UNION ALL
SELECT 'Strategy Performance:', COUNT(*) FROM strategy_performance
UNION ALL
SELECT 'Strategy Training Results:', COUNT(*) FROM strategy_training_results;
