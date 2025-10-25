-- Add training_logs table for persistent training log storage
-- Stores log entries from training jobs to survive browser refreshes

CREATE TABLE IF NOT EXISTS training_logs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES training_jobs(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message TEXT NOT NULL,
    progress NUMERIC(5,2) DEFAULT 0.0,  -- 0.00 to 100.00
    log_level VARCHAR(20) DEFAULT 'info' CHECK (log_level IN ('info', 'success', 'error', 'warning', 'progress')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient log retrieval by job_id
CREATE INDEX IF NOT EXISTS idx_training_logs_job_id ON training_logs(job_id);

-- Index for time-based queries and cleanup
CREATE INDEX IF NOT EXISTS idx_training_logs_timestamp ON training_logs(timestamp DESC);

-- Composite index for fetching job logs sorted by time
CREATE INDEX IF NOT EXISTS idx_training_logs_job_time ON training_logs(job_id, timestamp DESC);

-- Add comment for documentation
COMMENT ON TABLE training_logs IS 'Persistent storage for training job logs - keeps last 7 days or 100 most recent jobs';
COMMENT ON COLUMN training_logs.job_id IS 'Foreign key to training_jobs table';
COMMENT ON COLUMN training_logs.timestamp IS 'When this log entry was created during training';
COMMENT ON COLUMN training_logs.message IS 'The log message content (can be multi-line for progress bars)';
COMMENT ON COLUMN training_logs.progress IS 'Training progress percentage at time of log (0-100)';
COMMENT ON COLUMN training_logs.log_level IS 'Log severity: info, success, error, warning, progress';
