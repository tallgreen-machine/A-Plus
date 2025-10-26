-- Migration: Add candle-level progress tracking to training_jobs
-- Date: 2025-10-26
-- Purpose: Track fine-grained progress within iterations (updated every 50 candles)

-- Add candle tracking columns
ALTER TABLE training_jobs 
ADD COLUMN IF NOT EXISTS current_candle INTEGER,
ADD COLUMN IF NOT EXISTS total_candles INTEGER;

-- Add comments
COMMENT ON COLUMN training_jobs.current_candle IS 
    'Current candle being processed in backtest (updated every 50 candles)';

COMMENT ON COLUMN training_jobs.total_candles IS 
    'Total number of candles in training dataset';

-- Note: These columns provide fine-grained progress visibility
-- within each iteration, updating every 50 candles (~1-2 seconds)
-- This prevents "frozen" appearance during long iterations with large datasets
