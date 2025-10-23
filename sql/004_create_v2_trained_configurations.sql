-- Migration: Create V2 trained_configurations table for training system
-- Description: Simplified schema for V2 training results
-- Date: 2025-10-23

BEGIN;

-- Drop old table if exists (backup first if needed)
DROP TABLE IF EXISTS trained_configurations CASCADE;

-- Create V2 trained_configurations table
CREATE TABLE trained_configurations (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Configuration identification
    config_id TEXT UNIQUE NOT NULL,
    
    -- Strategy context
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    
    -- Lifecycle management
    lifecycle_stage TEXT NOT NULL,  -- 'DISCOVERY', 'VALIDATION', 'MATURE', 'PAPER'
    confidence_score NUMERIC(5,4) NOT NULL,
    
    -- Parameters and metrics (JSONB for flexibility)
    parameters JSONB NOT NULL,
    metrics JSONB NOT NULL,
    config_json JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Key performance metrics (for quick querying)
    sharpe_ratio NUMERIC(8,4),
    net_profit_pct NUMERIC(8,4),
    total_trades INTEGER,
    gross_win_rate NUMERIC(5,4)
);

-- Create indexes for common queries
CREATE INDEX idx_trained_configs_strategy ON trained_configurations(strategy);
CREATE INDEX idx_trained_configs_symbol ON trained_configurations(symbol);
CREATE INDEX idx_trained_configs_stage ON trained_configurations(lifecycle_stage);
CREATE INDEX idx_trained_configs_sharpe ON trained_configurations(sharpe_ratio DESC);

COMMIT;
