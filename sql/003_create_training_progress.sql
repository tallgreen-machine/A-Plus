-- Training Progress Tracking
-- Stores real-time progress updates for training jobs

CREATE TABLE IF NOT EXISTS training_progress (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL UNIQUE,  -- One progress record per job
    
    -- Overall progress
    percentage FLOAT NOT NULL DEFAULT 0.0,  -- 0.0 to 100.0
    current_step VARCHAR(100) NOT NULL,      -- e.g., "Data Collection", "Optimization", "Validation"
    step_number INTEGER NOT NULL DEFAULT 1,  -- Current step (1-4)
    total_steps INTEGER NOT NULL DEFAULT 4,  -- Total steps in workflow
    
    -- Step-specific progress
    step_percentage FLOAT NOT NULL DEFAULT 0.0,  -- Progress within current step
    step_details JSONB,                          -- Step-specific metadata
    
    -- Time tracking
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estimated_completion TIMESTAMPTZ,
    
    -- Optimizer-specific metrics (for real-time monitoring)
    current_iteration INTEGER,
    total_iterations INTEGER,
    best_score FLOAT,
    current_score FLOAT,
    best_params JSONB,
    
    -- Status
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    
    CONSTRAINT fk_training_job
        FOREIGN KEY (job_id)
        REFERENCES training_jobs(job_id)
        ON DELETE CASCADE
);

-- Index for fast job lookups
CREATE INDEX IF NOT EXISTS idx_training_progress_job_id 
    ON training_progress(job_id);

-- Index for fetching latest progress
CREATE INDEX IF NOT EXISTS idx_training_progress_job_updated 
    ON training_progress(job_id, updated_at DESC);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_training_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER training_progress_updated_at
    BEFORE UPDATE ON training_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_training_progress_timestamp();
