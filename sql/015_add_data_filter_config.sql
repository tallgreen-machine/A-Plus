-- Add data_filter_config column to training_jobs and trained_configurations tables
-- This stores the data quality filtering settings used during training

-- 1. Add to training_jobs table (stores settings for jobs in queue/running)
ALTER TABLE training_jobs 
ADD COLUMN IF NOT EXISTS data_filter_config JSONB DEFAULT jsonb_build_object(
    'enable_filtering', true,
    'min_volume_threshold', 0.1,
    'min_price_movement_pct', 0.01,
    'filter_flat_candles', true,
    'preserve_high_volume_single_price', true
);

COMMENT ON COLUMN training_jobs.data_filter_config IS 'Data quality filtering configuration: enable_filtering, min_volume_threshold, min_price_movement_pct, filter_flat_candles, preserve_high_volume_single_price';

-- 2. Add to trained_configurations table (stores settings used in trained configs)
ALTER TABLE trained_configurations 
ADD COLUMN IF NOT EXISTS data_filter_config JSONB;

COMMENT ON COLUMN trained_configurations.data_filter_config IS 'Data quality filtering settings used during training (for reproducibility and transparency)';

-- 3. Create index for querying by filter settings (useful for comparing results)
CREATE INDEX IF NOT EXISTS idx_training_jobs_filter_enabled 
ON training_jobs ((data_filter_config->>'enable_filtering'));

CREATE INDEX IF NOT EXISTS idx_trained_configs_filter_enabled 
ON trained_configurations ((data_filter_config->>'enable_filtering'));

-- 4. Example queries to use the new column:

-- Find all training jobs with filtering enabled
-- SELECT * FROM training_jobs WHERE data_filter_config->>'enable_filtering' = 'true';

-- Find trained configs that used strict volume filtering (> 0.5)
-- SELECT * FROM trained_configurations 
-- WHERE (data_filter_config->>'min_volume_threshold')::float > 0.5;

-- Compare win rates with/without filtering
-- SELECT 
--     data_filter_config->>'enable_filtering' as filtering_enabled,
--     AVG(gross_win_rate) as avg_win_rate,
--     COUNT(*) as count
-- FROM trained_configurations
-- WHERE gross_win_rate IS NOT NULL
-- GROUP BY filtering_enabled;
