-- Migration 011: Remove unique_configuration constraint
-- 
-- Problem: The unique constraint on (strategy_name, exchange, pair, timeframe, regime)
-- prevents multiple training runs of the same configuration from being saved.
-- Each training should create a new row with a unique UUID.
--
-- Solution: Drop the unique constraint to allow multiple configurations
-- with the same strategy/exchange/pair/timeframe/regime combination.

BEGIN;

-- Drop the unique constraint
ALTER TABLE trained_configurations 
DROP CONSTRAINT IF EXISTS unique_configuration;

-- Verify the constraint is removed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'unique_configuration'
    ) THEN
        RAISE EXCEPTION 'Failed to drop unique_configuration constraint';
    END IF;
END $$;

COMMIT;

-- Migration complete
-- Each training run will now create a new row with a unique UUID (id column)
-- Users can train the same strategy/symbol/timeframe multiple times
