CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(255) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    entry_price NUMERIC NOT NULL,
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_price NUMERIC,
    pnl_percentage NUMERIC,
    trade_type VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
