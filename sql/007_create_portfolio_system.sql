-- 007_create_portfolio_system.sql
-- Portfolio tracking, performance metrics, and equity history

-- Portfolio snapshots for real-time portfolio state
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_equity NUMERIC(18, 8) NOT NULL DEFAULT 0,
    cash_balance NUMERIC(18, 8) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(18, 8) DEFAULT 0,
    realized_pnl NUMERIC(18, 8) DEFAULT 0,
    total_pnl NUMERIC(18, 8) DEFAULT 0,
    position_count INTEGER DEFAULT 0,
    market_value NUMERIC(18, 8) DEFAULT 0
);

-- Holdings for current positions
CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(255) NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL DEFAULT 0,
    avg_cost NUMERIC(18, 8) NOT NULL DEFAULT 0,
    current_price NUMERIC(18, 8),
    market_value NUMERIC(18, 8),
    unrealized_pnl NUMERIC(18, 8),
    unrealized_pnl_percent NUMERIC(8, 4),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, symbol)
);

-- Equity history for performance charts
CREATE TABLE IF NOT EXISTS equity_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    equity NUMERIC(18, 8) NOT NULL,
    cash NUMERIC(18, 8) NOT NULL DEFAULT 0,
    market_value NUMERIC(18, 8) NOT NULL DEFAULT 0,
    total_pnl NUMERIC(18, 8) DEFAULT 0,
    daily_return NUMERIC(8, 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, timestamp)
);

-- Performance metrics for comprehensive analytics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    total_return NUMERIC(18, 8),
    total_return_percent NUMERIC(8, 4),
    sharpe_ratio NUMERIC(8, 4),
    max_drawdown NUMERIC(8, 4),
    max_drawdown_percent NUMERIC(8, 4),
    win_rate NUMERIC(8, 4),
    profit_factor NUMERIC(8, 4),
    avg_win NUMERIC(18, 8),
    avg_loss NUMERIC(18, 8),
    largest_win NUMERIC(18, 8),
    largest_loss NUMERIC(18, 8),
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    avg_trade_duration_hours NUMERIC(8, 2),
    volatility NUMERIC(8, 4),
    alpha NUMERIC(8, 4),
    beta NUMERIC(8, 4),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enhance existing trades table (add columns if they don't exist)
DO $$ 
BEGIN
    -- Add user_id column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='user_id') THEN
        ALTER TABLE trades ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
        -- Set default user for existing trades
        UPDATE trades SET user_id = 1 WHERE user_id IS NULL;
    END IF;
    
    -- Add other columns if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='fees') THEN
        ALTER TABLE trades ADD COLUMN fees NUMERIC(18, 8) DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='exchange') THEN
        ALTER TABLE trades ADD COLUMN exchange VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='order_id') THEN
        ALTER TABLE trades ADD COLUMN order_id VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='executed_at') THEN
        ALTER TABLE trades ADD COLUMN executed_at TIMESTAMP WITH TIME ZONE;
        -- Copy created_at to executed_at for existing records
        UPDATE trades SET executed_at = created_at WHERE executed_at IS NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='pnl_percent') THEN
        ALTER TABLE trades ADD COLUMN pnl_percent NUMERIC(8, 4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='pattern_id') THEN
        ALTER TABLE trades ADD COLUMN pattern_id INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='strategy_name') THEN
        ALTER TABLE trades ADD COLUMN strategy_name VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='entry_signal') THEN
        ALTER TABLE trades ADD COLUMN entry_signal TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='exit_signal') THEN
        ALTER TABLE trades ADD COLUMN exit_signal TEXT;
    END IF;
END $$;

-- Active trades for position monitoring
CREATE TABLE IF NOT EXISTS active_trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(255) NOT NULL,
    direction VARCHAR(10) CHECK (direction IN ('BUY', 'SELL', 'LONG', 'SHORT')) NOT NULL,
    entry_price NUMERIC(18, 8) NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL,
    current_price NUMERIC(18, 8),
    unrealized_pnl NUMERIC(18, 8),
    unrealized_pnl_percent NUMERIC(8, 4),
    stop_loss NUMERIC(18, 8),
    take_profit NUMERIC(18, 8),
    pattern_name VARCHAR(255),
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_paper_trade BOOLEAN DEFAULT false
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_timestamp ON portfolio_snapshots(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol);
CREATE INDEX IF NOT EXISTS idx_equity_history_user_timestamp ON equity_history(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_user_period ON performance_metrics(user_id, period_start, period_end);
-- Create indexes after column additions
DO $$
BEGIN
    -- Create indexes only if they don't exist and columns exist
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='user_id') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='executed_at') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at DESC);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_active_trades_user_id ON active_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_active_trades_symbol ON active_trades(symbol);

-- Grant permissions to traduser
GRANT ALL ON TABLE portfolio_snapshots TO traduser;
GRANT ALL ON TABLE holdings TO traduser;
GRANT ALL ON TABLE equity_history TO traduser;
GRANT ALL ON TABLE performance_metrics TO traduser;
GRANT ALL ON TABLE trades TO traduser;
GRANT ALL ON TABLE active_trades TO traduser;

GRANT USAGE, SELECT ON SEQUENCE portfolio_snapshots_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE holdings_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE equity_history_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE performance_metrics_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE trades_id_seq TO traduser;
GRANT USAGE, SELECT ON SEQUENCE active_trades_id_seq TO traduser;

-- Comments for documentation
COMMENT ON TABLE portfolio_snapshots IS 'Point-in-time portfolio state snapshots';
COMMENT ON TABLE holdings IS 'Current positions and holdings by user';
COMMENT ON TABLE equity_history IS 'Historical equity values for performance charting';
COMMENT ON TABLE performance_metrics IS 'Calculated performance statistics by period';
COMMENT ON TABLE trades IS 'All executed trades with performance data';
COMMENT ON TABLE active_trades IS 'Currently open positions being monitored';