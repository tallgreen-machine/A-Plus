-- 002_create_strategy_training_results.sql
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
