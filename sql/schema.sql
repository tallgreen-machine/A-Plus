-- =============================================================================
-- TradePulse IQ - Complete Database Schema
-- =============================================================================
-- This is the MASTER schema file that represents the complete database structure.
-- When making schema changes:
--   1. Update this file first
--   2. Create a migration script in sql/migrations/
--   3. Run sync_schema.sh to apply changes to production
-- =============================================================================

-- =============================================================================
-- CORE SYSTEM TABLES
-- =============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- =============================================================================
-- PORTFOLIO & HOLDINGS
-- =============================================================================

-- Portfolio snapshots
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_equity NUMERIC(18, 8) NOT NULL,
    cash_balance NUMERIC(18, 8) NOT NULL,
    positions_value NUMERIC(18, 8) NOT NULL,
    unrealized_pnl NUMERIC(18, 8) DEFAULT 0,
    realized_pnl NUMERIC(18, 8) DEFAULT 0,
    daily_pnl NUMERIC(18, 8) DEFAULT 0,
    daily_pnl_percent NUMERIC(6, 4) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_time 
    ON portfolio_snapshots(user_id, timestamp DESC);

-- Holdings (current positions)
CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL,
    average_price NUMERIC(18, 8) NOT NULL,
    current_price NUMERIC(18, 8),
    market_value NUMERIC(18, 8),
    unrealized_pnl NUMERIC(18, 8),
    unrealized_pnl_percent NUMERIC(6, 4),
    cost_basis NUMERIC(18, 8),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, symbol, exchange)
);

-- Equity history for charts
CREATE TABLE IF NOT EXISTS equity_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    equity NUMERIC(18, 8) NOT NULL,
    cash NUMERIC(18, 8),
    positions_value NUMERIC(18, 8)
);

CREATE INDEX IF NOT EXISTS idx_equity_history_user_time 
    ON equity_history(user_id, timestamp DESC);

-- =============================================================================
-- TRADING EXECUTION
-- =============================================================================

-- Completed trades
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    direction VARCHAR(10) NOT NULL, -- 'LONG' or 'SHORT'
    entry_price NUMERIC(18, 8) NOT NULL,
    exit_price NUMERIC(18, 8),
    quantity NUMERIC(18, 8) NOT NULL,
    pnl NUMERIC(18, 8),
    pnl_percent NUMERIC(6, 4),
    commission NUMERIC(18, 8) DEFAULT 0,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE,
    strategy_id INTEGER,
    strategy_name VARCHAR(255),
    timeframe VARCHAR(10),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_user_time 
    ON trades(user_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol 
    ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_strategy 
    ON trades(strategy_id);

-- Active trades (open positions)
CREATE TABLE IF NOT EXISTS active_trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(50) DEFAULT 'binance',
    direction VARCHAR(10) NOT NULL,
    entry_price NUMERIC(18, 8) NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL,
    current_price NUMERIC(18, 8),
    unrealized_pnl NUMERIC(18, 8),
    unrealized_pnl_percent NUMERIC(6, 4),
    stop_loss NUMERIC(18, 8),
    take_profit NUMERIC(18, 8),
    strategy_name VARCHAR(255),
    entry_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(user_id, symbol, exchange)
);

-- =============================================================================
-- STRATEGY SYSTEM (formerly "patterns")
-- =============================================================================

-- Strategy definitions
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100), -- e.g., 'Reversal', 'Breakout', 'Momentum'
    implementation_class VARCHAR(255), -- Python class name
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    version VARCHAR(50) DEFAULT '1.0',
    min_confidence NUMERIC(4, 3) DEFAULT 0.5,
    max_risk_per_trade NUMERIC(4, 3) DEFAULT 0.02
);

-- Strategy parameters (configurable per user/strategy)
CREATE TABLE IF NOT EXISTS strategy_parameters (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    parameter_name VARCHAR(255) NOT NULL,
    parameter_value JSONB NOT NULL,
    parameter_type VARCHAR(50) NOT NULL, -- 'int', 'float', 'string', 'boolean', 'array'
    default_value JSONB,
    min_value NUMERIC,
    max_value NUMERIC,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id, user_id, parameter_name)
);

CREATE INDEX IF NOT EXISTS idx_strategy_parameters_strategy_user 
    ON strategy_parameters(strategy_id, user_id);

-- Strategy performance tracking
CREATE TABLE IF NOT EXISTS strategy_performance (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
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
    UNIQUE(strategy_id, user_id, symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_strategy_user 
    ON strategy_performance(strategy_id, user_id);

-- Strategy training results (ML optimization outcomes)
CREATE TABLE IF NOT EXISTS strategy_training_results (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(255) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    training_parameters JSONB,
    success_rate DOUBLE PRECISION,
    sharpe_ratio DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,
    total_trades INTEGER,
    training_duration INTERVAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_strategy_training_results_strategy_symbol 
    ON strategy_training_results(strategy_name, symbol);

-- Trained configurations (optimized strategy instances)
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
    gross_win_rate NUMERIC(5,4),  -- 0.0000 to 1.0000 (65.5% = 0.6550)
    avg_win NUMERIC(15,2),
    avg_loss NUMERIC(15,2),
    net_profit NUMERIC(15,2),
    sample_size INTEGER,
    
    -- Fee and slippage tracking
    exchange_fees NUMERIC(15,2),
    est_slippage NUMERIC(15,2),
    actual_slippage NUMERIC(15,2),
    
    -- Statistical validation
    sharpe_ratio NUMERIC(8,4),
    calmar_ratio NUMERIC(8,4),
    sortino_ratio NUMERIC(8,4),
    p_value NUMERIC(8,6),
    z_score NUMERIC(8,4),
    monte_carlo_var NUMERIC(15,2),
    stability_score NUMERIC(5,4),
    drawdown_duration INTEGER,  -- in days
    trade_clustering NUMERIC(5,4),
    rolling_30d_sharpe NUMERIC(8,4),
    lifetime_sharpe_ratio NUMERIC(8,4),
    
    -- Execution metrics
    fill_rate NUMERIC(5,4),
    partial_fill_rate NUMERIC(5,4),
    time_to_fill_ms INTEGER,
    slippage_vs_mid_bps NUMERIC(8,2),
    adverse_selection_score NUMERIC(5,4),
    post_trade_drift_1m NUMERIC(8,2),
    post_trade_drift_5m NUMERIC(8,2),
    rejection_rate NUMERIC(5,4),
    
    -- Regime classification (JSONB for ensemble model data)
    regime_classification JSONB,
    
    -- Alternative data signals (JSONB for extensibility)
    alternative_data_signals JSONB,
    
    -- Adversarial analysis
    adversarial_score NUMERIC(5,4),
    trap_probability NUMERIC(5,4),
    smart_money_alignment NUMERIC(5,4),
    
    -- Risk allocation
    kelly_fraction NUMERIC(5,4),
    correlation_adjusted_weight NUMERIC(5,4),
    regime_adjusted_size NUMERIC(5,4),
    max_position_size NUMERIC(15,2),
    current_allocation NUMERIC(15,2),
    var_95 NUMERIC(15,2),
    cvar_95 NUMERIC(15,2),
    
    -- Market microstructure
    avg_spread_bps NUMERIC(8,2),
    book_depth_ratio NUMERIC(8,4),
    book_imbalance NUMERIC(5,4),
    tick_size_impact NUMERIC(8,4),
    maker_rebate NUMERIC(8,4),
    taker_fee NUMERIC(8,4),
    level2_depth_score NUMERIC(5,4),
    microstructure_noise NUMERIC(8,4),
    
    -- Pattern health tracking
    months_since_discovery INTEGER,
    performance_degradation NUMERIC(8,4),
    degradation_velocity NUMERIC(8,4),
    death_signals JSONB,  -- Stores flags like {volume_profile_changed: true, ...}
    death_signal_count INTEGER DEFAULT 0,
    resurrection_score NUMERIC(5,4),
    
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
    CONSTRAINT valid_timeframe CHECK (timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d'))
    -- Note: Removed unique_configuration constraint to allow multiple training runs
    -- Each configuration gets a unique UUID (id) as the primary key
);

CREATE INDEX IF NOT EXISTS idx_trained_configs_strategy ON trained_configurations(strategy_name);
CREATE INDEX IF NOT EXISTS idx_trained_configs_exchange ON trained_configurations(exchange);
CREATE INDEX IF NOT EXISTS idx_trained_configs_pair ON trained_configurations(pair);
CREATE INDEX IF NOT EXISTS idx_trained_configs_status ON trained_configurations(status);
CREATE INDEX IF NOT EXISTS idx_trained_configs_active ON trained_configurations(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_trained_configs_context ON trained_configurations(exchange, pair, timeframe);
CREATE INDEX IF NOT EXISTS idx_trained_configs_performance ON trained_configurations(net_profit DESC, sharpe_ratio DESC);
CREATE INDEX IF NOT EXISTS idx_trained_configs_lifecycle ON trained_configurations(status, months_since_discovery);
CREATE INDEX IF NOT EXISTS idx_trained_configs_parameters ON trained_configurations USING GIN (parameters_json);
CREATE INDEX IF NOT EXISTS idx_trained_configs_death_signals ON trained_configurations USING GIN (death_signals);

-- Strategy exchange performance (per exchange metrics)
CREATE TABLE IF NOT EXISTS strategy_exchange_performance (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(100) NOT NULL,
    symbol VARCHAR(255),
    total_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(6, 4),
    profit_factor NUMERIC(8, 4),
    total_pnl NUMERIC(18, 8) DEFAULT 0,
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'PAUSED', 'DISABLED')) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id, user_id, exchange, symbol)
);

-- Strategy regime performance (bull/bear/sideways metrics)
CREATE TABLE IF NOT EXISTS strategy_regime_performance (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    regime VARCHAR(50) NOT NULL, -- 'BULL', 'BEAR', 'SIDEWAYS'
    symbol VARCHAR(255),
    total_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(6, 4),
    profit_factor NUMERIC(8, 4),
    total_pnl NUMERIC(18, 8) DEFAULT 0,
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'PAUSED', 'DISABLED')) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id, user_id, regime, symbol)
);

-- =============================================================================
-- MARKET DATA
-- =============================================================================

-- Market data cache
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open NUMERIC(18, 8) NOT NULL,
    high NUMERIC(18, 8) NOT NULL,
    low NUMERIC(18, 8) NOT NULL,
    close NUMERIC(18, 8) NOT NULL,
    volume NUMERIC(18, 8) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange, timeframe, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time 
    ON market_data(symbol, exchange, timeframe, timestamp DESC);

-- Symbol status tracking
CREATE TABLE IF NOT EXISTS symbol_status (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(32) NOT NULL, -- 'available', 'unavailable', 'unknown'
    reason TEXT,
    last_checked TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- EXCHANGE CONNECTIONS
-- =============================================================================

-- Exchange API credentials
CREATE TABLE IF NOT EXISTS exchange_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_testnet BOOLEAN DEFAULT false,
    last_connection_test TIMESTAMP WITH TIME ZONE,
    connection_status VARCHAR(50), -- 'connected', 'disconnected', 'error'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, exchange)
);

-- =============================================================================
-- AI/ML TRAINING SYSTEM
-- =============================================================================

-- Training jobs tracking
CREATE TABLE IF NOT EXISTS training_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbols TEXT[], -- Array of symbols being trained
    strategies TEXT[], -- Array of strategy names
    status VARCHAR(50) NOT NULL, -- 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'
    progress INTEGER DEFAULT 0, -- 0-100
    current_phase VARCHAR(100),
    phase_description TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_training_jobs_user_status 
    ON training_jobs(user_id, status);

-- =============================================================================
-- BACKTESTING
-- =============================================================================

-- Backtest results
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    -- Results
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate NUMERIC(6, 4),
    total_pnl NUMERIC(18, 8),
    max_drawdown NUMERIC(6, 4),
    sharpe_ratio NUMERIC(8, 4),
    profit_factor NUMERIC(8, 4),
    -- Configuration
    parameters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- SYSTEM CONFIGURATION
-- =============================================================================

-- System settings
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User settings
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Additional composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_trades_user_symbol_time 
    ON trades(user_id, symbol, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_user_symbol 
    ON strategy_performance(user_id, symbol);

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Active strategies summary view
CREATE OR REPLACE VIEW active_strategies_summary AS
SELECT 
    s.id,
    s.name,
    s.category,
    COUNT(DISTINCT sp.symbol) as active_symbols,
    SUM(sp.total_trades) as total_trades,
    AVG(sp.win_rate) as avg_win_rate,
    SUM(sp.total_pnl) as total_pnl
FROM strategies s
LEFT JOIN strategy_performance sp ON s.id = sp.strategy_id AND sp.status = 'ACTIVE'
WHERE s.is_active = true
GROUP BY s.id, s.name, s.category;

-- User portfolio summary view
CREATE OR REPLACE VIEW user_portfolio_summary AS
SELECT 
    u.id as user_id,
    u.username,
    ps.total_equity,
    ps.unrealized_pnl,
    ps.realized_pnl,
    COUNT(h.id) as active_positions,
    COUNT(t.id) as total_trades
FROM users u
LEFT JOIN LATERAL (
    SELECT * FROM portfolio_snapshots 
    WHERE user_id = u.id 
    ORDER BY timestamp DESC LIMIT 1
) ps ON true
LEFT JOIN holdings h ON u.id = h.user_id
LEFT JOIN trades t ON u.id = t.user_id
GROUP BY u.id, u.username, ps.total_equity, ps.unrealized_pnl, ps.realized_pnl;

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp for trained_configurations
CREATE OR REPLACE FUNCTION update_trained_configurations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for trained_configurations updated_at
CREATE TRIGGER IF NOT EXISTS trigger_trained_configurations_updated_at
    BEFORE UPDATE ON trained_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_trained_configurations_updated_at();

-- =============================================================================
-- SCHEMA VERSION TRACKING
-- =============================================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Record current schema version
INSERT INTO schema_migrations (version, description) 
VALUES ('1.1.0', 'Added trained_configurations table for V2 dashboard')
ON CONFLICT (version) DO NOTHING;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
