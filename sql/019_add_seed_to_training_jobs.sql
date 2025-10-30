-- Migration 019: Add seed column to training_jobs table
-- Purpose: Enable reproducible parameter optimization
-- Date: October 30, 2025

-- Add seed column with default value of 42
ALTER TABLE training_jobs 
ADD COLUMN IF NOT EXISTS seed INTEGER DEFAULT 42;

-- Add comment explaining the purpose
COMMENT ON COLUMN training_jobs.seed IS 
'Seed for reproducible parameter optimization. Same seed produces same parameter exploration path, enabling reproducibility, debugging, and ensemble validation.';

-- Create index for potential seed-based queries
CREATE INDEX IF NOT EXISTS idx_training_jobs_seed ON training_jobs(seed);

-- Verify the column was added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'training_jobs' 
        AND column_name = 'seed'
    ) THEN
        RAISE NOTICE 'SUCCESS: seed column added to training_jobs table';
    ELSE
        RAISE EXCEPTION 'FAILED: seed column was not added';
    END IF;
END $$;
