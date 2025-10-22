-- Seed Trained Assets for Paper Trading
-- Creates realistic trained asset data for major crypto pairs with optimized parameters

-- Ensure strategies exist
INSERT INTO strategies (id, name, description, category, created_at)
VALUES
    (1, 'HTF Sweep', 'Higher timeframe liquidity sweep strategy', 'Liquidity', NOW()),
    (2, 'Volume Breakout', 'Volume-confirmed breakout strategy', 'Momentum', NOW()),
    (3, 'Divergence Capitulation', 'Divergence-based reversal strategy', 'Reversal', NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    category = EXCLUDED.category;

-- Seed Strategy Training Results (Multi-dimensional training outcomes)
-- These represent completed training sessions for each asset/strategy combination

-- BTC/USDT Training Results
INSERT INTO strategy_training_results (strategy_name, symbol, training_parameters, success_rate, sharpe_ratio, max_drawdown, total_trades, training_duration, created_at)
VALUES
    ('HTF Sweep', 'BTC/USDT', '{"timeframe": "15m", "regime": "bull", "exchange": "binance", "atr_period": 14, "volume_threshold": 1.8, "sweep_confirmation_bars": 3}', 0.72, 2.1, 6.5, 145, '48 hours', NOW() - INTERVAL '7 days'),
    ('HTF Sweep', 'BTC/USDT', '{"timeframe": "1h", "regime": "bear", "exchange": "binance", "atr_period": 21, "volume_threshold": 2.2, "sweep_confirmation_bars": 2}', 0.68, 1.9, 7.2, 98, '48 hours', NOW() - INTERVAL '6 days'),
    ('Volume Breakout', 'BTC/USDT', '{"timeframe": "5m", "regime": "bull", "exchange": "binance", "atr_multiplier": 1.5, "volume_spike": 2.0, "consolidation_bars": 20}', 0.65, 1.7, 8.1, 203, '48 hours', NOW() - INTERVAL '5 days'),
    ('Divergence Capitulation', 'BTC/USDT', '{"timeframe": "1h", "regime": "sideways", "exchange": "binance", "rsi_period": 14, "divergence_lookback": 10, "volume_threshold": 1.5}', 0.70, 2.0, 6.8, 112, '48 hours', NOW() - INTERVAL '4 days'),

-- ETH/USDT Training Results  
    ('HTF Sweep', 'ETH/USDT', '{"timeframe": "15m", "regime": "bull", "exchange": "binance", "atr_period": 14, "volume_threshold": 1.9, "sweep_confirmation_bars": 3}', 0.69, 1.95, 7.0, 132, '48 hours', NOW() - INTERVAL '7 days'),
    ('Volume Breakout', 'ETH/USDT', '{"timeframe": "5m", "regime": "bull", "exchange": "binance", "atr_multiplier": 1.6, "volume_spike": 2.1, "consolidation_bars": 18}', 0.67, 1.85, 7.5, 189, '48 hours', NOW() - INTERVAL '6 days'),
    ('Divergence Capitulation', 'ETH/USDT', '{"timeframe": "1h", "regime": "bear", "exchange": "binance", "rsi_period": 14, "divergence_lookback": 12, "volume_threshold": 1.6}', 0.71, 2.05, 6.5, 95, '48 hours', NOW() - INTERVAL '5 days'),

-- SOL/USDT Training Results
    ('HTF Sweep', 'SOL/USDT', '{"timeframe": "15m", "regime": "bull", "exchange": "binance", "atr_period": 14, "volume_threshold": 2.0, "sweep_confirmation_bars": 3}', 0.74, 2.2, 6.2, 156, '48 hours', NOW() - INTERVAL '7 days'),
    ('Volume Breakout', 'SOL/USDT', '{"timeframe": "5m", "regime": "bull", "exchange": "binance", "atr_multiplier": 1.7, "volume_spike": 2.2, "consolidation_bars": 15}', 0.68, 1.9, 7.8, 221, '48 hours', NOW() - INTERVAL '6 days'),

-- AVAX/USDT Training Results
    ('Volume Breakout', 'AVAX/USDT', '{"timeframe": "15m", "regime": "bull", "exchange": "binance", "atr_multiplier": 1.5, "volume_spike": 1.9, "consolidation_bars": 22}', 0.66, 1.75, 8.3, 143, '48 hours', NOW() - INTERVAL '5 days'),
    ('Divergence Capitulation', 'AVAX/USDT', '{"timeframe": "1h", "regime": "sideways", "exchange": "binance", "rsi_period": 14, "divergence_lookback": 11, "volume_threshold": 1.7}', 0.69, 1.88, 7.1, 87, '48 hours', NOW() - INTERVAL '4 days');

-- Seed Strategy Parameters (Optimized parameters for each pattern/asset combination)
-- These are used by the trading system to execute trades

-- HTF Sweep Parameters for BTC/USDT
INSERT INTO strategy_parameters (strategy_id, user_id, parameter_name, parameter_value, parameter_type, default_value, min_value, max_value, description)
VALUES
    (1, 1, 'primary_timeframe', '"15m"', 'string', '"15m"', NULL, NULL, 'Primary timeframe for HTF Sweep analysis'),
    (1, 1, 'macro_timeframe', '"1h"', 'string', '"1h"', NULL, NULL, 'Higher timeframe for liquidity sweep detection'),
    (1, 1, 'atr_period', '14', 'number', '14', 10, 30, 'ATR period for volatility measurement'),
    (1, 1, 'volume_threshold', '1.8', 'number', '1.5', 1.0, 3.0, 'Volume spike threshold multiplier'),
    (1, 1, 'sweep_confirmation_bars', '3', 'number', '3', 1, 5, 'Number of bars to confirm sweep failure'),
    (1, 1, 'risk_reward_ratio', '2.0', 'number', '2.0', 1.5, 4.0, 'Minimum risk/reward ratio for entries'),
    (1, 1, 'stop_loss_atr', '1.5', 'number', '1.5', 0.5, 3.0, 'Stop loss distance in ATR multiples'),

-- Volume Breakout Parameters for BTC/USDT
    (2, 1, 'primary_timeframe', '"5m"', 'string', '"5m"', NULL, NULL, 'Primary timeframe for breakout analysis'),
    (2, 1, 'atr_multiplier', '1.5', 'number', '1.5', 1.0, 2.5, 'ATR multiplier for consolidation detection'),
    (2, 1, 'volume_spike', '2.0', 'number', '2.0', 1.5, 3.0, 'Volume spike multiplier for confirmation'),
    (2, 1, 'consolidation_bars', '20', 'number', '20', 10, 40, 'Minimum bars in consolidation'),
    (2, 1, 'breakout_confirmation', '0.5', 'number', '0.5', 0.1, 1.0, 'Percentage move for breakout confirmation'),
    (2, 1, 'risk_reward_ratio', '1.8', 'number', '1.8', 1.5, 3.0, 'Minimum risk/reward ratio'),

-- Divergence Capitulation Parameters for BTC/USDT
    (3, 1, 'primary_timeframe', '"1h"', 'string', '"1h"', NULL, NULL, 'Primary timeframe for divergence analysis'),
    (3, 1, 'rsi_period', '14', 'number', '14', 10, 30, 'RSI period for divergence detection'),
    (3, 1, 'divergence_lookback', '10', 'number', '10', 5, 20, 'Bars to look back for divergence'),
    (3, 1, 'volume_threshold', '1.5', 'number', '1.5', 1.2, 2.5, 'Volume threshold for capitulation'),
    (3, 1, 'risk_reward_ratio', '2.5', 'number', '2.5', 1.5, 4.0, 'Minimum risk/reward ratio');

-- Seed Strategy Performance (Per-asset strategy performance)
INSERT INTO strategy_performance (
    strategy_id, user_id, symbol, timeframe, 
    total_trades, winning_trades, losing_trades, win_rate,
    avg_win, avg_loss, profit_factor, total_pnl,
    max_consecutive_wins, max_consecutive_losses,
    avg_trade_duration_minutes, max_drawdown, max_drawdown_percent,
    sharpe_ratio, sortino_ratio,
    first_trade_at, last_trade_at, status
)
VALUES
    -- BTC/USDT - HTF Sweep Performance
    (1, 1, 'BTC/USDT', '15m', 145, 104, 41, 0.7172, 850.50, 320.20, 2.66, 52450.30, 8, 3, 125, 3250.50, 6.5, 2.1, 2.8, NOW() - INTERVAL '30 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- BTC/USDT - Volume Breakout Performance
    (2, 1, 'BTC/USDT', '5m', 203, 132, 71, 0.6502, 420.30, 280.15, 1.50, 28650.20, 6, 4, 45, 2100.30, 7.5, 1.7, 2.1, NOW() - INTERVAL '30 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- BTC/USDT - Divergence Capitulation Performance  
    (3, 1, 'BTC/USDT', '1h', 112, 78, 34, 0.6964, 920.75, 385.40, 2.39, 39840.50, 7, 3, 180, 2850.20, 6.8, 2.0, 2.5, NOW() - INTERVAL '30 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- ETH/USDT - HTF Sweep Performance
    (1, 1, 'ETH/USDT', '15m', 132, 91, 41, 0.6894, 485.30, 245.80, 1.97, 28960.40, 7, 3, 130, 2150.60, 7.0, 1.95, 2.6, NOW() - INTERVAL '25 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- ETH/USDT - Volume Breakout Performance
    (2, 1, 'ETH/USDT', '5m', 189, 127, 62, 0.6720, 320.45, 210.30, 1.52, 21540.80, 6, 4, 50, 1850.40, 7.5, 1.85, 2.2, NOW() - INTERVAL '25 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- ETH/USDT - Divergence Capitulation Performance
    (3, 1, 'ETH/USDT', '1h', 95, 67, 28, 0.7053, 565.80, 280.50, 2.02, 24320.70, 8, 3, 175, 1920.30, 6.5, 2.05, 2.7, NOW() - INTERVAL '25 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- SOL/USDT - HTF Sweep Performance
    (1, 1, 'SOL/USDT', '15m', 156, 115, 41, 0.7372, 295.40, 145.60, 2.03, 23250.80, 9, 2, 120, 1650.40, 6.2, 2.2, 3.0, NOW() - INTERVAL '20 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- SOL/USDT - Volume Breakout Performance
    (2, 1, 'SOL/USDT', '5m', 221, 150, 71, 0.6787, 185.70, 125.40, 1.48, 15820.50, 7, 4, 42, 1280.30, 7.8, 1.9, 2.3, NOW() - INTERVAL '20 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- AVAX/USDT - Volume Breakout Performance
    (2, 1, 'AVAX/USDT', '15m', 143, 94, 49, 0.6573, 245.80, 165.30, 1.49, 12850.40, 6, 3, 135, 1450.60, 8.3, 1.75, 2.1, NOW() - INTERVAL '18 days', NOW() - INTERVAL '1 day', 'ACTIVE'),
    
    -- AVAX/USDT - Divergence Capitulation Performance
    (3, 1, 'AVAX/USDT', '1h', 87, 60, 27, 0.6897, 385.60, 215.40, 1.79, 14250.30, 7, 3, 165, 1320.50, 7.1, 1.88, 2.4, NOW() - INTERVAL '18 days', NOW() - INTERVAL '1 day', 'ACTIVE')
ON CONFLICT (strategy_id, user_id, symbol, timeframe) DO UPDATE SET
    total_trades = EXCLUDED.total_trades,
    winning_trades = EXCLUDED.winning_trades,
    losing_trades = EXCLUDED.losing_trades,
    win_rate = EXCLUDED.win_rate,
    avg_win = EXCLUDED.avg_win,
    avg_loss = EXCLUDED.avg_loss,
    profit_factor = EXCLUDED.profit_factor,
    total_pnl = EXCLUDED.total_pnl,
    last_trade_at = EXCLUDED.last_trade_at,
    status = EXCLUDED.status;

COMMIT;

-- Verify seeded data
SELECT 'Training Results:' as table_name, COUNT(*) as count FROM strategy_training_results
UNION ALL
SELECT 'Strategy Parameters:', COUNT(*) FROM strategy_parameters
UNION ALL  
SELECT 'Strategy Performance:', COUNT(*) FROM strategy_performance
UNION ALL
SELECT 'Active Strategies:', COUNT(*) FROM strategy_performance WHERE status = 'ACTIVE';

-- Show trained assets summary
SELECT 
    pp.symbol,
    p.name as strategy,
    pp.timeframe,
    pp.total_trades,
    ROUND(pp.win_rate::numeric * 100, 2) as win_rate_pct,
    ROUND(pp.profit_factor::numeric, 2) as profit_factor,
    ROUND(pp.total_pnl::numeric, 2) as total_pnl,
    pp.status
FROM strategy_performance pp
JOIN strategies p ON pp.strategy_id = p.id
WHERE pp.status = 'ACTIVE'
ORDER BY pp.symbol, p.name;
