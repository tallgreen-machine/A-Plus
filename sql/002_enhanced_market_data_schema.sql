-- Enhanced Database Schema for Multi-Timeframe Trading Data
-- Supports OHLCV, trades, order book, and ticker data for ML training

-- =====================================================
-- MULTI-TIMEFRAME OHLCV DATA
-- =====================================================

-- Enhanced market_data table with timeframe support
CREATE TABLE IF NOT EXISTS market_data_enhanced (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,  -- 1m, 5m, 15m, 1h, 4h, 1d
    timestamp BIGINT NOT NULL,       -- Unix timestamp in milliseconds
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    quote_volume DECIMAL(20,8) DEFAULT NULL,  -- Volume in quote currency (USDT)
    trade_count INTEGER DEFAULT NULL,         -- Number of trades in this candle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure no duplicate candles
    UNIQUE(exchange, symbol, timeframe, timestamp)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_market_data_enhanced_lookup 
    ON market_data_enhanced(exchange, symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_enhanced_symbol_time 
    ON market_data_enhanced(symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_enhanced_timeframe 
    ON market_data_enhanced(timeframe, timestamp DESC);

-- =====================================================
-- INDIVIDUAL TRADES DATA
-- =====================================================

CREATE TABLE IF NOT EXISTS trade_data (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    trade_id VARCHAR(100),           -- Exchange-specific trade ID
    timestamp BIGINT NOT NULL,       -- Unix timestamp in milliseconds
    price DECIMAL(20,8) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,   -- Base currency amount
    cost DECIMAL(20,8) NOT NULL,     -- Quote currency cost (price * amount)
    side VARCHAR(10),                -- 'buy' or 'sell' 
    taker_or_maker VARCHAR(10),      -- 'taker' or 'maker'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure no duplicate trades
    UNIQUE(exchange, symbol, trade_id)
);

-- Indexes for trade analysis
CREATE INDEX IF NOT EXISTS idx_trade_data_lookup 
    ON trade_data(exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trade_data_symbol_time 
    ON trade_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trade_data_side_time 
    ON trade_data(side, timestamp DESC);

-- =====================================================
-- ORDER BOOK SNAPSHOTS
-- =====================================================

CREATE TABLE IF NOT EXISTS order_book_snapshots (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    
    -- Top 10 bids and asks as JSON arrays
    bids JSONB NOT NULL,             -- [[price, amount], [price, amount], ...]
    asks JSONB NOT NULL,             -- [[price, amount], [price, amount], ...]
    
    -- Calculated metrics
    best_bid DECIMAL(20,8),
    best_ask DECIMAL(20,8),
    spread DECIMAL(20,8),            -- best_ask - best_bid
    spread_pct DECIMAL(10,6),        -- spread / mid_price * 100
    mid_price DECIMAL(20,8),         -- (best_bid + best_ask) / 2
    bid_depth DECIMAL(20,8),         -- Total volume in top 10 bids
    ask_depth DECIMAL(20,8),         -- Total volume in top 10 asks
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for order book analysis
CREATE INDEX IF NOT EXISTS idx_order_book_lookup 
    ON order_book_snapshots(exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_order_book_spread 
    ON order_book_snapshots(symbol, spread_pct, timestamp DESC);

-- =====================================================
-- 24H TICKER DATA
-- =====================================================

CREATE TABLE IF NOT EXISTS ticker_data (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    
    -- 24h statistics
    last_price DECIMAL(20,8) NOT NULL,
    bid DECIMAL(20,8),
    ask DECIMAL(20,8),
    high_24h DECIMAL(20,8),
    low_24h DECIMAL(20,8),
    volume_24h DECIMAL(20,8),        -- Base volume
    quote_volume_24h DECIMAL(20,8),  -- Quote volume (USDT)
    change_24h DECIMAL(20,8),        -- Price change
    change_pct_24h DECIMAL(10,6),    -- Percentage change
    vwap_24h DECIMAL(20,8),          -- Volume weighted average price
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One ticker snapshot per symbol per exchange per hour
    UNIQUE(exchange, symbol, timestamp)
);

-- Indexes for ticker analysis
CREATE INDEX IF NOT EXISTS idx_ticker_data_lookup 
    ON ticker_data(exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ticker_data_volume 
    ON ticker_data(symbol, volume_24h DESC, timestamp DESC);

-- =====================================================
-- DATA COLLECTION METADATA
-- =====================================================

CREATE TABLE IF NOT EXISTS collection_runs (
    id BIGSERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,   -- 'ohlcv', 'trades', 'orderbook', 'ticker'
    exchange VARCHAR(50) NOT NULL,
    symbols TEXT[] NOT NULL,         -- Array of symbols collected
    timeframes TEXT[],               -- Array of timeframes (for OHLCV)
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'running', -- 'running', 'completed', 'failed'
    records_collected INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- USEFUL VIEWS FOR ANALYSIS
-- =====================================================

-- Latest prices across all exchanges
CREATE OR REPLACE VIEW latest_prices AS
SELECT 
    symbol,
    exchange,
    timeframe,
    close as price,
    volume,
    timestamp,
    to_timestamp(timestamp/1000) as price_time
FROM market_data_enhanced m1
WHERE timestamp = (
    SELECT MAX(timestamp) 
    FROM market_data_enhanced m2 
    WHERE m2.exchange = m1.exchange 
    AND m2.symbol = m1.symbol 
    AND m2.timeframe = '1h'
)
ORDER BY symbol, exchange;

-- Price spreads across exchanges
CREATE OR REPLACE VIEW exchange_spreads AS
SELECT 
    symbol,
    timeframe,
    timestamp,
    MAX(close) - MIN(close) as price_spread,
    (MAX(close) - MIN(close)) / AVG(close) * 100 as spread_pct,
    COUNT(*) as exchange_count
FROM market_data_enhanced
WHERE timeframe = '1h'
GROUP BY symbol, timeframe, timestamp
HAVING COUNT(*) > 1
ORDER BY timestamp DESC, spread_pct DESC;

-- Volume analysis by timeframe
CREATE OR REPLACE VIEW volume_by_timeframe AS
SELECT 
    symbol,
    timeframe,
    exchange,
    AVG(volume) as avg_volume,
    SUM(volume) as total_volume,
    COUNT(*) as candle_count,
    MIN(to_timestamp(timestamp/1000)) as start_date,
    MAX(to_timestamp(timestamp/1000)) as end_date
FROM market_data_enhanced
GROUP BY symbol, timeframe, exchange
ORDER BY symbol, timeframe, total_volume DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO traduser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO traduser;

-- Performance settings for large datasets
ALTER TABLE market_data_enhanced SET (fillfactor = 90);
ALTER TABLE trade_data SET (fillfactor = 90);

COMMENT ON TABLE market_data_enhanced IS 'Multi-timeframe OHLCV data for ML training';
COMMENT ON TABLE trade_data IS 'Individual trade data for tick-level analysis';
COMMENT ON TABLE order_book_snapshots IS 'Order book depth snapshots for liquidity analysis';
COMMENT ON TABLE ticker_data IS '24h ticker statistics for market overview';
COMMENT ON TABLE collection_runs IS 'Metadata tracking for data collection runs';