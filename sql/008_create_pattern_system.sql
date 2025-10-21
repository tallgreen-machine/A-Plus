-- 008_create_pattern_system.sql
-- Pattern management, performance tracking, and parameter configuration

-- Patterns table for pattern definitions and metadata
CREATE TABLE IF NOT EXISTS patterns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100), -- e.g., 'Reversal', 'Breakout', 'Momentum'
    implementation_class VARCHAR(255), -- Python class name
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    -- Pattern metadata
    version VARCHAR(50) DEFAULT '1.0',
    min_confidence NUMERIC(4, 3) DEFAULT 0.5,
    max_risk_per_trade NUMERIC(4, 3) DEFAULT 0.02
);

-- Pattern parameters for configurable pattern settings
CREATE TABLE IF NOT EXISTS pattern_parameters (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES patterns(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, -- User-specific overrides
    parameter_name VARCHAR(255) NOT NULL,
    parameter_value JSONB NOT NULL,
    parameter_type VARCHAR(50) NOT NULL, -- 'int', 'float', 'string', 'boolean', 'array'
    default_value JSONB,
    min_value NUMERIC,
    max_value NUMERIC,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pattern_id, user_id, parameter_name)
);

-- Pattern performance tracking
CREATE TABLE IF NOT EXISTS pattern_performance (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES patterns(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(255),
    timeframe VARCHAR(10), -- '1m', '5m', '1h', '4h', '1d'
    -- Performance metrics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(6, 4),
    avg_win NUMERIC(18, 8),
    avg_loss NUMERIC(18, 8),
    profit_factor NUMERIC(8, 4),
    total_pnl NUMERIC(18, 8) DEFAULT 0,
    max_consecutive_wins INTEGER DEFAULT 0,
    max_consecutive_losses INTEGER DEFAULT 0,
    avg_trade_duration_minutes INTEGER,
    -- Risk metrics
    max_drawdown NUMERIC(18, 8),
    max_drawdown_percent NUMERIC(6, 4),
    sharpe_ratio NUMERIC(8, 4),
    sortino_ratio NUMERIC(8, 4),
    -- Timing data
    first_trade_at TIMESTAMP WITH TIME ZONE,
    last_trade_at TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Status
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'PAUSED', 'PAPER_TRADING', 'DISABLED')) DEFAULT 'ACTIVE',
    UNIQUE(pattern_id, user_id, symbol, timeframe)
);

-- Pattern training results for AI/ML optimization
CREATE TABLE IF NOT EXISTS pattern_training_results (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES patterns(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(255) NOT NULL,
    training_session_id UUID DEFAULT gen_random_uuid(),
    -- Training configuration
    parameters_used JSONB NOT NULL,
    training_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    training_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    validation_period_start TIMESTAMP WITH TIME ZONE,
    validation_period_end TIMESTAMP WITH TIME ZONE,
    -- Results
    training_score NUMERIC(8, 6),
    validation_score NUMERIC(8, 6),
    confidence_score NUMERIC(4, 3),
    win_rate NUMERIC(6, 4),
    profit_factor NUMERIC(8, 4),
    sharpe_ratio NUMERIC(8, 4),
    max_drawdown NUMERIC(6, 4),
    total_signals INTEGER,
    profitable_signals INTEGER,
    -- Metadata
    training_duration_seconds INTEGER,
    model_path TEXT,
    feature_importance JSONB,
    optimization_method VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Exchange-specific pattern performance
CREATE TABLE IF NOT EXISTS pattern_exchange_performance (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES patterns(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(255) NOT NULL,
    symbol VARCHAR(255),
    -- Performance metrics specific to exchange
    total_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(6, 4),
    avg_profit NUMERIC(18, 8),
    avg_loss NUMERIC(18, 8),
    total_pnl NUMERIC(18, 8) DEFAULT 0,
    -- Exchange-specific metrics
    avg_slippage NUMERIC(6, 4), -- as percentage
    avg_fees NUMERIC(6, 4), -- as percentage
    avg_latency_ms INTEGER,
    fill_rate NUMERIC(6, 4), -- percentage of orders filled
    -- Status and timing
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'PAUSED', 'PAPER_TRADING', 'DISABLED')) DEFAULT 'ACTIVE',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pattern_id, user_id, exchange, symbol)
);

-- Market regime performance tracking
CREATE TABLE IF NOT EXISTS pattern_regime_performance (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES patterns(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    regime VARCHAR(50) CHECK (regime IN ('BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOLATILITY', 'LOW_VOLATILITY')) NOT NULL,
    symbol VARCHAR(255),
    -- Performance in specific market regime
    total_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(6, 4),
    avg_profit NUMERIC(18, 8),
    avg_loss NUMERIC(18, 8),
    total_pnl NUMERIC(18, 8) DEFAULT 0,
    profit_factor NUMERIC(8, 4),
    max_drawdown NUMERIC(6, 4),
    -- Regime-specific insights
    regime_detection_accuracy NUMERIC(6, 4),
    false_signal_rate NUMERIC(6, 4),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pattern_id, user_id, regime, symbol)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_patterns_name ON patterns(name);
CREATE INDEX IF NOT EXISTS idx_patterns_active ON patterns(is_active);
CREATE INDEX IF NOT EXISTS idx_pattern_parameters_pattern_user ON pattern_parameters(pattern_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_performance_pattern_user ON pattern_performance(pattern_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_performance_symbol_timeframe ON pattern_performance(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_pattern_performance_status ON pattern_performance(status);
CREATE INDEX IF NOT EXISTS idx_pattern_training_results_pattern_user ON pattern_training_results(pattern_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_training_results_session ON pattern_training_results(training_session_id);
CREATE INDEX IF NOT EXISTS idx_pattern_exchange_performance_pattern_user ON pattern_exchange_performance(pattern_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_exchange_performance_exchange ON pattern_exchange_performance(exchange);
CREATE INDEX IF NOT EXISTS idx_pattern_regime_performance_pattern_user ON pattern_regime_performance(pattern_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_regime_performance_regime ON pattern_regime_performance(regime);

-- Grant permissions to traduser
GRANT ALL ON TABLE patterns TO traduser;
GRANT ALL ON TABLE pattern_parameters TO traduser;
GRANT ALL ON TABLE pattern_performance TO traduser;
GRANT ALL ON TABLE pattern_training_results TO traduser;
GRANT ALL ON TABLE pattern_exchange_performance TO traduser;
GRANT ALL ON TABLE pattern_regime_performance TO traduser;

GRANT USAGE, SELECT ON SEQUENCE patterns_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE pattern_parameters_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE pattern_performance_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE pattern_training_results_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE pattern_exchange_performance_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE pattern_regime_performance_id_seq TO traduser;

-- Insert some default patterns to match the frontend
INSERT INTO patterns (name, description, category, implementation_class) VALUES
    ('Liquidity Sweep', 'Detects liquidity sweep patterns with stop hunt reversals', 'Reversal', 'LiquiditySweepPattern'),
    ('Divergence Capitulation', 'RSI/Price divergence with capitulation signals', 'Reversal', 'DivergenceCapitulationPattern'),
    ('HTF Sweep', 'Higher timeframe sweep with lower timeframe entries', 'Breakout', 'HTFSweepPattern'),
    ('Volume Breakout', 'Volume-confirmed breakout patterns', 'Breakout', 'VolumeBreakoutPattern')
ON CONFLICT (name) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE patterns IS 'Pattern definitions and metadata';
COMMENT ON TABLE pattern_parameters IS 'Configurable parameters for each pattern by user';
COMMENT ON TABLE pattern_performance IS 'Performance tracking for patterns by symbol and timeframe';
COMMENT ON TABLE pattern_training_results IS 'AI/ML training results and optimization data';
COMMENT ON TABLE pattern_exchange_performance IS 'Exchange-specific pattern performance metrics';
COMMENT ON TABLE pattern_regime_performance IS 'Pattern performance across different market regimes';