-- Migration: Create trained_configurations table
-- Description: Stores optimized strategy configurations with performance metrics
-- Date: 2025-10-22
-- Author: TradePulse IQ System

BEGIN;

-- Create trained_configurations table
CREATE TABLE IF NOT EXISTS trained_configurations (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Configuration context
    strategy_name VARCHAR(100) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    pair VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    regime VARCHAR(20) NOT NULL,  -- 'bull', 'bear', 'sideways', 'volatile'
    
    -- Lifecycle management
    status VARCHAR(20) NOT NULL DEFAULT 'DISCOVERY',  -- 'DISCOVERY', 'VALIDATION', 'MATURE', 'DECAY', 'PAPER'
    is_active BOOLEAN DEFAULT false,
    
    -- Strategy parameters (JSONB for flexibility)
    parameters_json JSONB NOT NULL,
    
    -- Performance metrics
    gross_win_rate DECIMAL(5,4),  -- 0.0000 to 1.0000 (65.5% = 0.6550)
    avg_win DECIMAL(15,2),
    avg_loss DECIMAL(15,2),
    net_profit DECIMAL(15,2),
    sample_size INTEGER,
    
    -- Fee and slippage tracking
    exchange_fees DECIMAL(15,2),
    est_slippage DECIMAL(15,2),
    actual_slippage DECIMAL(15,2),
    
    -- Statistical validation
    sharpe_ratio DECIMAL(8,4),
    calmar_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    p_value DECIMAL(8,6),
    z_score DECIMAL(8,4),
    monte_carlo_var DECIMAL(15,2),
    stability_score DECIMAL(5,4),
    drawdown_duration INTEGER,  -- in days
    trade_clustering DECIMAL(5,4),
    rolling_30d_sharpe DECIMAL(8,4),
    lifetime_sharpe_ratio DECIMAL(8,4),
    
    -- Execution metrics
    fill_rate DECIMAL(5,4),
    partial_fill_rate DECIMAL(5,4),
    time_to_fill_ms INTEGER,
    slippage_vs_mid_bps DECIMAL(8,2),
    adverse_selection_score DECIMAL(5,4),
    post_trade_drift_1m DECIMAL(8,2),
    post_trade_drift_5m DECIMAL(8,2),
    rejection_rate DECIMAL(5,4),
    
    -- Regime classification (JSONB for ensemble model data)
    regime_classification JSONB,
    
    -- Alternative data signals (JSONB for extensibility)
    alternative_data_signals JSONB,
    
    -- Adversarial analysis
    adversarial_score DECIMAL(5,4),
    trap_probability DECIMAL(5,4),
    smart_money_alignment DECIMAL(5,4),
    
    -- Risk allocation
    kelly_fraction DECIMAL(5,4),
    correlation_adjusted_weight DECIMAL(5,4),
    regime_adjusted_size DECIMAL(5,4),
    max_position_size DECIMAL(15,2),
    current_allocation DECIMAL(15,2),
    var_95 DECIMAL(15,2),
    cvar_95 DECIMAL(15,2),
    
    -- Market microstructure
    avg_spread_bps DECIMAL(8,2),
    book_depth_ratio DECIMAL(8,4),
    book_imbalance DECIMAL(5,4),
    tick_size_impact DECIMAL(8,4),
    maker_rebate DECIMAL(8,4),
    taker_fee DECIMAL(8,4),
    level2_depth_score DECIMAL(5,4),
    microstructure_noise DECIMAL(8,4),
    
    -- Pattern health tracking
    months_since_discovery INTEGER,
    performance_degradation DECIMAL(8,4),
    degradation_velocity DECIMAL(8,4),
    death_signals JSONB,  -- Stores flags like {volume_profile_changed: true, ...}
    death_signal_count INTEGER DEFAULT 0,
    resurrection_score DECIMAL(5,4),
    
    -- Metadata
    model_version VARCHAR(20),
    discovery_date TIMESTAMP WITH TIME ZONE,
    engine_hash VARCHAR(64),
    runtime_env VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activated_at TIMESTAMP WITH TIME ZONE,
    last_deactivated_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('DISCOVERY', 'VALIDATION', 'MATURE', 'DECAY', 'PAPER')),
    CONSTRAINT valid_regime CHECK (regime IN ('bull', 'bear', 'sideways', 'volatile')),
    CONSTRAINT valid_timeframe CHECK (timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d')),
    CONSTRAINT unique_configuration UNIQUE (strategy_name, exchange, pair, timeframe, regime)
);

-- Create indexes for common query patterns
CREATE INDEX idx_trained_configs_strategy ON trained_configurations(strategy_name);
CREATE INDEX idx_trained_configs_exchange ON trained_configurations(exchange);
CREATE INDEX idx_trained_configs_pair ON trained_configurations(pair);
CREATE INDEX idx_trained_configs_status ON trained_configurations(status);
CREATE INDEX idx_trained_configs_active ON trained_configurations(is_active) WHERE is_active = true;
CREATE INDEX idx_trained_configs_context ON trained_configurations(exchange, pair, timeframe);
CREATE INDEX idx_trained_configs_performance ON trained_configurations(net_profit DESC, sharpe_ratio DESC);
CREATE INDEX idx_trained_configs_lifecycle ON trained_configurations(status, months_since_discovery);

-- JSONB indexes for filtering
CREATE INDEX idx_trained_configs_parameters ON trained_configurations USING GIN (parameters_json);
CREATE INDEX idx_trained_configs_death_signals ON trained_configurations USING GIN (death_signals);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_trained_configurations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_trained_configurations_updated_at
    BEFORE UPDATE ON trained_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_trained_configurations_updated_at();

-- Add comment to table
COMMENT ON TABLE trained_configurations IS 'Stores optimized strategy configurations with comprehensive performance and risk metrics';

COMMIT;
