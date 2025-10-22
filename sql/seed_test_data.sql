-- Seed Test Data for TradePulse IQ Dashboard
-- This script adds realistic test data for development and testing

-- Clear existing test data (optional - comment out if you want to keep existing data)
-- TRUNCATE TABLE trades CASCADE;
-- TRUNCATE TABLE active_trades CASCADE;
-- TRUNCATE TABLE portfolio_snapshots CASCADE;
-- TRUNCATE TABLE holdings CASCADE;
-- TRUNCATE TABLE equity_history CASCADE;

-- Ensure we have a test user
INSERT INTO users (id, username, email, display_name, created_at)
VALUES (1, 'admin', 'admin@tradepulse.com', 'Admin User', NOW())
ON CONFLICT (id) DO NOTHING;

-- Seed Historical Trades (Last 30 days)
-- Mix of winning and losing trades across different symbols
INSERT INTO trades (timestamp, symbol, exchange, quantity, direction, price, fill_cost, commission, user_id, pnl_percent, strategy_name, executed_at)
VALUES
    -- Week 1: October 15-21
    (NOW() - INTERVAL '7 days', 'BTC/USDT', 'binance', 0.5, 'BUY', 48000, 24000, 12, 1, 4.17, 'HTF Sweep', NOW() - INTERVAL '7 days'),
    (NOW() - INTERVAL '6 days', 'ETH/USDT', 'binance', 5.0, 'BUY', 3000, 15000, 7.5, 1, 6.67, 'Volume Breakout', NOW() - INTERVAL '6 days'),
    (NOW() - INTERVAL '6 days', 'SOL/USDT', 'binance', 50.0, 'BUY', 100, 5000, 2.5, 1, -2.5, 'Divergence Capitulation', NOW() - INTERVAL '6 days'),
    (NOW() - INTERVAL '5 days', 'AVAX/USDT', 'binance', 100.0, 'BUY', 35, 3500, 1.75, 1, 8.57, 'HTF Sweep', NOW() - INTERVAL '5 days'),
    (NOW() - INTERVAL '5 days', 'MATIC/USDT', 'binance', 1000.0, 'BUY', 0.85, 850, 0.43, 1, -1.18, 'Volume Breakout', NOW() - INTERVAL '5 days'),
    
    -- Week 2: October 8-14
    (NOW() - INTERVAL '14 days', 'BTC/USDT', 'binance', 0.3, 'BUY', 46500, 13950, 7, 1, 3.23, 'HTF Sweep', NOW() - INTERVAL '14 days'),
    (NOW() - INTERVAL '13 days', 'ETH/USDT', 'binance', 3.0, 'BUY', 2900, 8700, 4.35, 1, 5.52, 'Divergence Capitulation', NOW() - INTERVAL '13 days'),
    (NOW() - INTERVAL '12 days', 'BNB/USDT', 'binance', 20.0, 'BUY', 220, 4400, 2.2, 1, -3.18, 'Volume Breakout', NOW() - INTERVAL '12 days'),
    (NOW() - INTERVAL '11 days', 'XRP/USDT', 'binance', 2000.0, 'BUY', 0.55, 1100, 0.55, 1, 7.27, 'HTF Sweep', NOW() - INTERVAL '11 days'),
    (NOW() - INTERVAL '10 days', 'ADA/USDT', 'binance', 3000.0, 'BUY', 0.35, 1050, 0.53, 1, -1.43, 'Divergence Capitulation', NOW() - INTERVAL '10 days'),
    
    -- Week 3: October 1-7
    (NOW() - INTERVAL '21 days', 'BTC/USDT', 'binance', 0.4, 'BUY', 45000, 18000, 9, 1, 6.67, 'HTF Sweep', NOW() - INTERVAL '21 days'),
    (NOW() - INTERVAL '20 days', 'ETH/USDT', 'binance', 4.0, 'BUY', 2800, 11200, 5.6, 1, 10.71, 'Volume Breakout', NOW() - INTERVAL '20 days'),
    (NOW() - INTERVAL '19 days', 'SOL/USDT', 'binance', 80.0, 'BUY', 98, 7840, 3.92, 1, 15.31, 'HTF Sweep', NOW() - INTERVAL '19 days'),
    (NOW() - INTERVAL '18 days', 'LINK/USDT', 'binance', 150.0, 'BUY', 12, 1800, 0.9, 1, -2.5, 'Divergence Capitulation', NOW() - INTERVAL '18 days'),
    (NOW() - INTERVAL '17 days', 'DOT/USDT', 'binance', 200.0, 'BUY', 6.5, 1300, 0.65, 1, 4.62, 'Volume Breakout', NOW() - INTERVAL '17 days'),
    
    -- Week 4: September 24-30
    (NOW() - INTERVAL '28 days', 'BTC/USDT', 'binance', 0.35, 'BUY', 44000, 15400, 7.7, 1, 9.09, 'HTF Sweep', NOW() - INTERVAL '28 days'),
    (NOW() - INTERVAL '27 days', 'ETH/USDT', 'binance', 6.0, 'BUY', 2750, 16500, 8.25, 1, 8.00, 'Volume Breakout', NOW() - INTERVAL '27 days'),
    (NOW() - INTERVAL '26 days', 'AVAX/USDT', 'binance', 120.0, 'BUY', 32, 3840, 1.92, 1, -4.38, 'Divergence Capitulation', NOW() - INTERVAL '26 days'),
    (NOW() - INTERVAL '25 days', 'ATOM/USDT', 'binance', 100.0, 'BUY', 9.5, 950, 0.48, 1, 5.26, 'HTF Sweep', NOW() - INTERVAL '25 days'),
    (NOW() - INTERVAL '24 days', 'UNI/USDT', 'binance', 200.0, 'BUY', 7.2, 1440, 0.72, 1, -1.39, 'Volume Breakout', NOW() - INTERVAL '24 days');

-- Seed Active Trades (Currently Open Positions)
INSERT INTO active_trades (user_id, symbol, direction, entry_price, quantity, current_price, unrealized_pnl, unrealized_pnl_percent, stop_loss, take_profit, pattern_name, entry_timestamp)
VALUES
    (1, 'BTC/USDT', 'LONG', 49500, 0.25, 50000, 125, 1.01, 48000, 52000, 'HTF Sweep', NOW() - INTERVAL '2 hours'),
    (1, 'ETH/USDT', 'LONG', 3150, 3.0, 3200, 150, 1.59, 3050, 3350, 'Volume Breakout', NOW() - INTERVAL '4 hours'),
    (1, 'SOL/USDT', 'LONG', 118, 40.0, 122, 160, 3.39, 112, 130, 'HTF Sweep', NOW() - INTERVAL '1 hour'),
    (1, 'AVAX/USDT', 'SHORT', 38, 80.0, 37.5, 40, 1.32, 39.5, 35, 'Divergence Capitulation', NOW() - INTERVAL '3 hours'),
    (1, 'MATIC/USDT', 'LONG', 0.88, 1500.0, 0.89, 15, 1.14, 0.85, 0.95, 'Volume Breakout', NOW() - INTERVAL '30 minutes');

-- Seed Portfolio Snapshots (Daily snapshots for last 30 days)
-- Starting with $100,000 portfolio, showing growth over time
DO $$
DECLARE
    day_offset INTEGER;
    base_equity NUMERIC := 100000;
    daily_equity NUMERIC;
    daily_cash NUMERIC;
    daily_market_value NUMERIC;
BEGIN
    FOR day_offset IN 0..30 LOOP
        -- Simulate portfolio growth with some variance
        daily_equity := base_equity + (day_offset * 250) + (RANDOM() * 1000 - 500);
        daily_market_value := daily_equity * (0.3 + RANDOM() * 0.2); -- 30-50% invested
        daily_cash := daily_equity - daily_market_value;
        
        INSERT INTO portfolio_snapshots (
            user_id, 
            timestamp, 
            total_equity, 
            cash_balance, 
            market_value, 
            unrealized_pnl, 
            realized_pnl, 
            total_pnl
        )
        VALUES (
            1,
            NOW() - (day_offset || ' days')::INTERVAL,
            daily_equity,
            daily_cash,
            daily_market_value,
            daily_market_value * 0.05, -- 5% unrealized P&L
            (day_offset * 100), -- Growing realized P&L
            (daily_market_value * 0.05) + (day_offset * 100)
        );
    END LOOP;
END $$;

-- Seed Holdings (Current positions matching active trades)
DELETE FROM holdings WHERE user_id = 1;
INSERT INTO holdings (user_id, symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl, unrealized_pnl_percent, last_updated)
VALUES
    (1, 'BTC/USDT', 0.5, 48000, 50000, 25000, 1000, 4.17, NOW()),
    (1, 'ETH/USDT', 5.0, 3000, 3200, 16000, 1000, 6.67, NOW()),
    (1, 'SOL/USDT', 50.0, 100, 120, 6000, 1000, 20.00, NOW()),
    (1, 'AVAX/USDT', 100.0, 35, 38, 3800, 300, 8.57, NOW()),
    (1, 'MATIC/USDT', 1000.0, 0.85, 0.89, 890, 40, 4.71, NOW());

-- Seed Equity History (Hourly snapshots for last 7 days)
DO $$
DECLARE
    hour_offset INTEGER;
    base_equity NUMERIC := 100000;
    hourly_equity NUMERIC;
BEGIN
    FOR hour_offset IN 0..168 LOOP -- 7 days * 24 hours
        hourly_equity := base_equity + (hour_offset * 15) + (RANDOM() * 200 - 100);
        
        INSERT INTO equity_history (user_id, timestamp, equity)
        VALUES (
            1,
            NOW() - (hour_offset || ' hours')::INTERVAL,
            hourly_equity
        );
    END LOOP;
END $$;

-- Seed Pattern Performance Data
INSERT INTO pattern_performance (user_id, pattern_id, pattern_name, total_trades, winning_trades, losing_trades, win_rate, avg_profit, avg_loss, profit_factor, total_pnl, created_at)
VALUES
    (1, 1, 'HTF Sweep', 45, 32, 13, 71.11, 850.5, 320.2, 2.66, 14250.5, NOW()),
    (1, 2, 'Volume Breakout', 38, 24, 14, 63.16, 720.3, 410.5, 1.75, 8540.2, NOW()),
    (1, 3, 'Divergence Capitulation', 32, 21, 11, 65.63, 680.7, 380.4, 1.79, 7250.8, NOW());

-- Seed Performance Metrics
INSERT INTO performance_metrics (user_id, total_trades, winning_trades, losing_trades, win_rate, profit_factor, sharpe_ratio, max_drawdown, total_pnl, avg_profit, avg_loss, created_at)
VALUES
    (1, 115, 77, 38, 66.96, 2.15, 1.85, 8.5, 30041.5, 750.2, 370.4, NOW())
ON CONFLICT (user_id) DO UPDATE SET
    total_trades = EXCLUDED.total_trades,
    winning_trades = EXCLUDED.winning_trades,
    losing_trades = EXCLUDED.losing_trades,
    win_rate = EXCLUDED.win_rate,
    profit_factor = EXCLUDED.profit_factor,
    sharpe_ratio = EXCLUDED.sharpe_ratio,
    max_drawdown = EXCLUDED.max_drawdown,
    total_pnl = EXCLUDED.total_pnl,
    avg_profit = EXCLUDED.avg_profit,
    avg_loss = EXCLUDED.avg_loss;

-- Add pattern definitions
INSERT INTO patterns (id, name, description, category, created_at)
VALUES
    (1, 'HTF Sweep', 'Higher timeframe liquidity sweep strategy', 'Liquidity', NOW()),
    (2, 'Volume Breakout', 'Volume-confirmed breakout strategy', 'Momentum', NOW()),
    (3, 'Divergence Capitulation', 'Divergence-based reversal strategy', 'Reversal', NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    category = EXCLUDED.category;

COMMIT;

-- Verify data
SELECT 'Trades:' as table_name, COUNT(*) as count FROM trades
UNION ALL
SELECT 'Active Trades:', COUNT(*) FROM active_trades
UNION ALL
SELECT 'Portfolio Snapshots:', COUNT(*) FROM portfolio_snapshots
UNION ALL
SELECT 'Holdings:', COUNT(*) FROM holdings
UNION ALL
SELECT 'Equity History:', COUNT(*) FROM equity_history
UNION ALL
SELECT 'Pattern Performance:', COUNT(*) FROM pattern_performance
UNION ALL
SELECT 'Performance Metrics:', COUNT(*) FROM performance_metrics;
