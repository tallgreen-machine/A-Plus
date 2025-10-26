-- Migration: Add job_id to trained_configurations
-- Date: 2025-10-26
-- Purpose: Track which training job created each configuration

-- Add job_id column to store the training job ID
ALTER TABLE trained_configurations
ADD COLUMN IF NOT EXISTS job_id INTEGER;

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_trained_configurations_job_id ON trained_configurations(job_id);

-- Add comment
COMMENT ON COLUMN trained_configurations.job_id IS 'Training job ID that created this configuration (for tracking and display)';

-- Note: This is NOT a foreign key because training_jobs may be cleaned up
-- but we want to keep the job_id for historical reference
