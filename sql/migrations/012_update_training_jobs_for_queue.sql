-- Migration: Update training_jobs table for new queue system
-- Date: 2025-10-24
-- Reason: Add columns for persistent queue with SSE progress tracking

BEGIN;

-- Add new columns if they don't exist
DO $$ 
BEGIN
    -- Add config_id column (reference to trained_configurations)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='config_id') THEN
        ALTER TABLE training_jobs ADD COLUMN config_id UUID;
        ALTER TABLE training_jobs ADD CONSTRAINT fk_config_id 
            FOREIGN KEY (config_id) REFERENCES trained_configurations(id) ON DELETE CASCADE;
    END IF;

    -- Add rq_job_id column (for RQ job tracking)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='rq_job_id') THEN
        ALTER TABLE training_jobs ADD COLUMN rq_job_id VARCHAR(255) UNIQUE;
    END IF;

    -- Add progress column (0-100 with 0.1 precision)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='progress') THEN
        ALTER TABLE training_jobs ADD COLUMN progress NUMERIC(5,2) DEFAULT 0.0 
            CHECK (progress >= 0 AND progress <= 100);
    END IF;

    -- Add metadata columns for queue display
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='strategy_name') THEN
        ALTER TABLE training_jobs ADD COLUMN strategy_name VARCHAR(100);
        -- Populate from existing strategy column
        UPDATE training_jobs SET strategy_name = strategy WHERE strategy_name IS NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='pair') THEN
        ALTER TABLE training_jobs ADD COLUMN pair VARCHAR(20);
        -- Populate from existing symbol column
        UPDATE training_jobs SET pair = symbol WHERE pair IS NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='regime') THEN
        ALTER TABLE training_jobs ADD COLUMN regime VARCHAR(20) DEFAULT 'sideways';
    END IF;

    -- Add progress tracking columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='current_episode') THEN
        ALTER TABLE training_jobs ADD COLUMN current_episode INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='total_episodes') THEN
        ALTER TABLE training_jobs ADD COLUMN total_episodes INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='current_reward') THEN
        ALTER TABLE training_jobs ADD COLUMN current_reward NUMERIC(10,4);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='current_loss') THEN
        ALTER TABLE training_jobs ADD COLUMN current_loss NUMERIC(10,4);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='training_jobs' AND column_name='current_stage') THEN
        ALTER TABLE training_jobs ADD COLUMN current_stage VARCHAR(50);
    END IF;

    -- Rename created_at to submitted_at if needed
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='training_jobs' AND column_name='created_at') 
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='training_jobs' AND column_name='submitted_at') THEN
        ALTER TABLE training_jobs RENAME COLUMN created_at TO submitted_at;
    END IF;

    -- Update status constraint to match new values
    IF EXISTS (SELECT 1 FROM information_schema.constraint_column_usage 
               WHERE table_name='training_jobs' AND constraint_name='valid_status') THEN
        ALTER TABLE training_jobs DROP CONSTRAINT valid_status;
    END IF;
    
    ALTER TABLE training_jobs ADD CONSTRAINT valid_status 
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 
                          'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'));
END $$;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_training_jobs_submitted_at ON training_jobs(submitted_at);
CREATE INDEX IF NOT EXISTS idx_training_jobs_rq_job_id ON training_jobs(rq_job_id);
CREATE INDEX IF NOT EXISTS idx_training_jobs_config_id ON training_jobs(config_id);

-- Track migration (create table if it doesn't exist)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_migrations (version, description) 
VALUES ('1.1.0', 'Update training_jobs table for persistent queue system')
ON CONFLICT (version) DO NOTHING;

COMMIT;
