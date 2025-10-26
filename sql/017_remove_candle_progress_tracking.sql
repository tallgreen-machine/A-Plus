-- Migration: Remove candle-level progress tracking from training_jobs
-- Date: 2025-10-26
-- Purpose: Remove candle tracking columns (not useful - only visible 0.3% of time)
--
-- Context: Candle progress was only visible during backtest phase (~0.5s per iteration)
-- but signal generation takes 2-3 minutes per iteration. The candle display
-- provided no value since it was barely visible. Signal generation progress
-- is now tracked directly instead.

-- Remove candle tracking columns
ALTER TABLE training_jobs 
DROP COLUMN IF EXISTS current_candle,
DROP COLUMN IF EXISTS total_candles;

-- Note: Progress tracking now focuses on signal generation phase which
-- represents 95%+ of iteration time, providing continuous visibility
-- throughout the actual bottleneck.
