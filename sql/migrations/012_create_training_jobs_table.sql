-- Migration: Create training_jobs table for persistent job queue
-- Date: 2025-10-24
-- Reason: Enable persistent training queue that survives app refresh, supports cancellation, and tracks job lifecycle

BEGIN;

-- Create training_jobs table
CREATE TABLE IF NOT EXISTS training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES training_configurations(id) ON DELETE CASCADE,
    rq_job_id VARCHAR(255) UNIQUE,  -- RQ job ID for status tracking
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress NUMERIC(5,2) DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 100),  -- 0.00 to 100.00
    
    -- Metadata for queue display
    strategy_name VARCHAR(100) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    pair VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    regime VARCHAR(20) NOT NULL,
    
    -- Progress details (for animated display)
    current_episode INTEGER,
    total_episodes INTEGER,
    current_reward NUMERIC(10,4),
    current_loss NUMERIC(10,4),
    current_stage VARCHAR(50),  -- 'loading', 'training', 'evaluating', 'saving'
    
    -- Timestamps
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error tracking
    error_message TEXT,
    
    -- Indexes for efficient querying
    CONSTRAINT valid_timestamps CHECK (
        (started_at IS NULL OR started_at >= submitted_at) AND
        (completed_at IS NULL OR completed_at >= COALESCE(started_at, submitted_at))
    )
);

-- Indexes for efficient queue queries
CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(status);
CREATE INDEX IF NOT EXISTS idx_training_jobs_submitted_at ON training_jobs(submitted_at);
CREATE INDEX IF NOT EXISTS idx_training_jobs_rq_job_id ON training_jobs(rq_job_id);

-- Track migration
INSERT INTO schema_migrations (version, description) 
VALUES ('1.1.0', 'Create training_jobs table for persistent job queue')
ON CONFLICT (version) DO NOTHING;

COMMIT;
