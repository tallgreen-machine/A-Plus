-- 005_create_market_data.sql

-- Drop the table if it exists to ensure a clean slate, especially during development.
DROP TABLE IF EXISTS market_data;

CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(255) NOT NULL,
    symbol VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol, timestamp)
);

COMMENT ON TABLE market_data IS 'Stores OHLCV market data from various exchanges.';
COMMENT ON COLUMN market_data.exchange IS 'The exchange from which the data was sourced (e.g., binanceus).';
COMMENT ON COLUMN market_data.symbol IS 'The trading symbol (e.g., BTC/USD).';
COMMENT ON COLUMN market_data.timestamp IS 'The UTC timestamp for the start of the candle (in milliseconds).';
