-- Training Jobs Table
-- Tracks asynchronous training job status and results

CREATE TABLE IF NOT EXISTS training_jobs (
    id SERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    
    -- Job configuration
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    optimizer TEXT NOT NULL,  -- 'grid', 'random', 'bayesian'
    
    -- Job parameters
    lookback_days INTEGER DEFAULT 90,
    n_iterations INTEGER,  -- For random/bayesian
    parameter_space JSONB,
    
    -- Job status
    status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    progress_pct NUMERIC DEFAULT 0,
    current_iteration INTEGER DEFAULT 0,
    total_iterations INTEGER,
    
    -- Timing
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Results
    best_config_id TEXT,  -- Reference to trained_configurations
    best_score NUMERIC,
    best_parameters JSONB,
    best_metrics JSONB,
    
    -- Errors
    error_message TEXT,
    error_trace TEXT,
    
    -- Metadata
    created_by TEXT,
    metadata JSONB,
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    CONSTRAINT valid_optimizer CHECK (optimizer IN ('grid', 'random', 'bayesian'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_training_jobs_job_id ON training_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(status);
CREATE INDEX IF NOT EXISTS idx_training_jobs_created_at ON training_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_jobs_strategy ON training_jobs(strategy);
CREATE INDEX IF NOT EXISTS idx_training_jobs_symbol_exchange ON training_jobs(symbol, exchange);

-- Index for querying active jobs
CREATE INDEX IF NOT EXISTS idx_training_jobs_active ON training_jobs(status, created_at DESC) 
    WHERE status IN ('PENDING', 'RUNNING');

COMMENT ON TABLE training_jobs IS 'Tracks training job execution status and results';
COMMENT ON COLUMN training_jobs.job_id IS 'Unique job identifier (UUID)';
COMMENT ON COLUMN training_jobs.status IS 'Job status: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED';
COMMENT ON COLUMN training_jobs.optimizer IS 'Optimization algorithm: grid, random, bayesian';
COMMENT ON COLUMN training_jobs.best_config_id IS 'Foreign key to trained_configurations.config_id';
COMMENT ON COLUMN training_jobs.progress_pct IS 'Job completion percentage (0-100)';
