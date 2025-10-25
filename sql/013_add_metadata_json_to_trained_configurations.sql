-- Add metadata_json column to trained_configurations table
-- This will store training metadata like optimizer, n_iterations, etc.

ALTER TABLE trained_configurations 
ADD COLUMN IF NOT EXISTS metadata_json JSONB;

-- Add index for JSON queries
CREATE INDEX IF NOT EXISTS idx_trained_configs_metadata ON trained_configurations USING GIN (metadata_json);
