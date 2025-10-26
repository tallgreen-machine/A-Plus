-- Migration: Add lookback_candles column to training_jobs
-- Date: 2025-10-26
-- Purpose: Switch from time-based (days) to candle-based lookback for consistency across timeframes

-- Add the new column
ALTER TABLE training_jobs 
ADD COLUMN IF NOT EXISTS lookback_candles INTEGER;

-- Migrate existing data: Convert lookback_days to estimated candles
-- Formula: candles ≈ days × (minutes_per_day / timeframe_minutes)
-- For 5m: days × 288, for 1h: days × 24, for 1d: days × 1
-- We'll use a conservative estimate based on 5m (most common)
UPDATE training_jobs
SET lookback_candles = lookback_days * 288
WHERE lookback_candles IS NULL AND lookback_days IS NOT NULL;

-- Add comment
COMMENT ON COLUMN training_jobs.lookback_candles IS 
    'Number of candles for training data (replaces lookback_days for consistency across timeframes)';

-- Note: lookback_days column is kept for backward compatibility during transition
-- After all systems are updated, we can deprecate lookback_days in a future migration
