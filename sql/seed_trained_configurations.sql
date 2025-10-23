-- =============================================================================
-- Seed Data for trained_configurations table
-- =============================================================================
-- Purpose: Populate database with test configurations for V2 dashboard testing
-- Note: This data is intentionally different from mockApi to distinguish
--       between UI mock data and actual database data
-- =============================================================================

BEGIN;

-- Clean existing data (for fresh seeding)
-- TRUNCATE trained_configurations CASCADE;

-- =============================================================================
-- LIQUIDITY SWEEP V3 Configurations
-- =============================================================================

INSERT INTO trained_configurations (
    strategy_name, exchange, pair, timeframe, regime, status, is_active,
    parameters_json,
    gross_win_rate, avg_win, avg_loss, net_profit, sample_size,
    exchange_fees, est_slippage, actual_slippage,
    sharpe_ratio, calmar_ratio, sortino_ratio, p_value, z_score,
    stability_score, fill_rate, adverse_selection_score,
    max_position_size, var_95,
    months_since_discovery, performance_degradation, death_signal_count,
    model_version, discovery_date, runtime_env
) VALUES
-- BTC/USDT Binance Bull Market (MATURE - Best performer)
('LIQUIDITY_SWEEP_V3', 'binance', 'BTC/USDT', '1h', 'bull', 'MATURE', true,
 '{"pierce_depth": 0.18, "rejection_candles": 3, "volume_spike_threshold": 2.8, "reversal_candle_size": 1.3, "key_level_lookback": 120, "stop_distance": 0.9, "target_multiple": 3.2, "min_stop_density_score": 0.75, "max_spread_tolerance": 4}'::jsonb,
 0.6850, 1250.00, -420.00, 45600.00, 156,
 125.50, 85.20, 92.30,
 2.15, 1.85, 2.40, 0.012, 3.2,
 0.87, 0.94, 0.21,
 5000.00, -2100.00,
 8, -0.05, 0,
 'v3.2.1', '2024-03-15 10:30:00+00', 'production'),

-- BTC/USDT Binance Bear Market (VALIDATION)
('LIQUIDITY_SWEEP_V3', 'binance', 'BTC/USDT', '1h', 'bear', 'VALIDATION', false,
 '{"pierce_depth": 0.22, "rejection_candles": 4, "volume_spike_threshold": 3.2, "reversal_candle_size": 1.5, "key_level_lookback": 150, "stop_distance": 1.1, "target_multiple": 2.8, "min_stop_density_score": 0.80, "max_spread_tolerance": 6}'::jsonb,
 0.5920, 980.00, -510.00, 12400.00, 85,
 88.20, 72.40, 78.60,
 1.35, 1.10, 1.50, 0.045, 1.8,
 0.72, 0.88, 0.32,
 5000.00, -3200.00,
 4, 0.08, 1,
 'v3.2.1', '2024-07-20 14:15:00+00', 'production'),

-- ETH/USDT Coinbase Bull Market (MATURE)
('LIQUIDITY_SWEEP_V3', 'coinbase', 'ETH/USDT', '4h', 'bull', 'MATURE', true,
 '{"pierce_depth": 0.15, "rejection_candles": 2, "volume_spike_threshold": 2.5, "reversal_candle_size": 1.2, "key_level_lookback": 100, "stop_distance": 0.85, "target_multiple": 3.5, "min_stop_density_score": 0.72, "max_spread_tolerance": 5}'::jsonb,
 0.7120, 890.00, -310.00, 38200.00, 142,
 102.30, 68.50, 71.20,
 2.45, 2.10, 2.65, 0.008, 3.8,
 0.91, 0.96, 0.18,
 4000.00, -1800.00,
 6, -0.02, 0,
 'v3.2.1', '2024-04-10 09:00:00+00', 'production'),

-- =============================================================================
-- HTF SWEEP Configurations
-- =============================================================================

-- BTC/USDT Bybit Sideways (DISCOVERY)
('HTF_SWEEP', 'bybit', 'BTC/USDT', '15m', 'sideways', 'DISCOVERY', false,
 '{"htf_timeframe": "4h", "ltf_timeframe": "15m", "liquidity_threshold": 1.8, "sweep_confirmation": 2, "structure_shift_required": true}'::jsonb,
 0.5450, 520.00, -380.00, 3200.00, 28,
 42.10, 35.20, 38.50,
 0.85, 0.65, 0.95, 0.182, 0.9,
 0.58, 0.82, 0.45,
 3000.00, -4500.00,
 1, 0.00, 0,
 'v2.1.0', '2024-10-05 16:45:00+00', 'production'),

-- ETH/USDT Binance Bull Market (MATURE)
('HTF_SWEEP', 'binance', 'ETH/USDT', '1h', 'bull', 'MATURE', true,
 '{"htf_timeframe": "1d", "ltf_timeframe": "1h", "liquidity_threshold": 2.2, "sweep_confirmation": 3, "structure_shift_required": true}'::jsonb,
 0.6980, 720.00, -290.00, 32800.00, 118,
 92.40, 61.30, 65.80,
 2.12, 1.92, 2.28, 0.015, 3.1,
 0.85, 0.93, 0.24,
 3500.00, -1950.00,
 7, -0.08, 0,
 'v2.1.0', '2024-03-28 11:20:00+00', 'production'),

-- =============================================================================
-- VOLUME BREAKOUT Configurations
-- =============================================================================

-- SOL/USDT Binance Bull Market (VALIDATION)
('VOLUME_BREAKOUT', 'binance', 'SOL/USDT', '1h', 'bull', 'VALIDATION', true,
 '{"consolidation_period": 20, "volume_multiplier": 2.5, "atr_threshold": 1.8, "breakout_strength": 0.7}'::jsonb,
 0.6320, 450.00, -280.00, 18500.00, 92,
 68.20, 48.30, 52.10,
 1.68, 1.45, 1.82, 0.032, 2.4,
 0.78, 0.89, 0.28,
 2500.00, -2800.00,
 3, 0.05, 0,
 'v1.5.2', '2024-08-12 13:30:00+00', 'production'),

-- MATIC/USDT Coinbase Sideways (DECAY - Declining performance)
('VOLUME_BREAKOUT', 'coinbase', 'MATIC/USDT', '4h', 'sideways', 'DECAY', false,
 '{"consolidation_period": 24, "volume_multiplier": 3.0, "atr_threshold": 2.0, "breakout_strength": 0.8}'::jsonb,
 0.4820, 180.00, -220.00, -4200.00, 65,
 52.30, 41.20, 45.60,
 0.42, 0.28, 0.55, 0.285, -0.5,
 0.45, 0.78, 0.58,
 1500.00, -5200.00,
 12, -0.35, 3,
 'v1.5.2', '2023-10-18 08:15:00+00', 'production'),

-- =============================================================================
-- DIVERGENCE CAPITULATION Configurations
-- =============================================================================

-- BTC/USDT Binance Bear Market (PAPER - Failed configuration)
('DIVERGENCE_CAPITULATION', 'binance', 'BTC/USDT', '1h', 'bear', 'PAPER', false,
 '{"rsi_period": 14, "rsi_oversold": 30, "divergence_lookback": 50, "volume_confirmation": 1.5, "trend_filter": "ema_200"}'::jsonb,
 0.3950, 380.00, -490.00, -8900.00, 48,
 62.10, 52.80, 58.20,
 -0.25, -0.18, -0.12, 0.452, -1.2,
 0.38, 0.72, 0.68,
 2000.00, -6800.00,
 15, -0.58, 5,
 'v1.8.0', '2023-06-22 10:45:00+00', 'production'),

-- ETH/USDT Bybit Volatile Market (DISCOVERY - New configuration)
('DIVERGENCE_CAPITULATION', 'bybit', 'ETH/USDT', '15m', 'volatile', 'DISCOVERY', false,
 '{"rsi_period": 12, "rsi_oversold": 25, "divergence_lookback": 40, "volume_confirmation": 2.0, "trend_filter": "macd"}'::jsonb,
 0.5580, 290.00, -240.00, 2100.00, 22,
 28.40, 22.10, 24.80,
 0.92, 0.78, 1.05, 0.165, 1.1,
 0.62, 0.84, 0.42,
 1800.00, -3900.00,
 1, 0.00, 0,
 'v1.8.0', '2024-10-18 15:00:00+00', 'production');

-- =============================================================================
-- Additional configurations for variety
-- =============================================================================

INSERT INTO trained_configurations (
    strategy_name, exchange, pair, timeframe, regime, status, is_active,
    parameters_json,
    gross_win_rate, avg_win, avg_loss, net_profit, sample_size,
    sharpe_ratio, fill_rate,
    max_position_size,
    months_since_discovery,
    model_version, discovery_date, runtime_env
) VALUES
-- More BTC configurations across different regimes
('LIQUIDITY_SWEEP_V3', 'binance', 'BTC/USDT', '4h', 'bull', 'MATURE', true,
 '{"pierce_depth": 0.20, "rejection_candles": 3, "volume_spike_threshold": 2.6}'::jsonb,
 0.7020, 1850.00, -620.00, 52300.00, 178,
 2.38, 0.95, 6000.00, 9,
 'v3.2.1', '2024-02-14 12:00:00+00', 'production'),

('HTF_SWEEP', 'coinbase', 'BTC/USDT', '1h', 'sideways', 'VALIDATION', false,
 '{"htf_timeframe": "4h", "ltf_timeframe": "1h", "liquidity_threshold": 2.0}'::jsonb,
 0.6150, 680.00, -320.00, 15800.00, 76,
 1.52, 0.91, 4500.00, 5,
 'v2.1.0', '2024-06-01 14:30:00+00', 'production'),

-- Altcoin configurations
('VOLUME_BREAKOUT', 'bybit', 'AVAX/USDT', '1h', 'bull', 'VALIDATION', true,
 '{"consolidation_period": 18, "volume_multiplier": 2.8, "atr_threshold": 1.9}'::jsonb,
 0.6580, 380.00, -210.00, 14200.00, 68,
 1.78, 0.90, 2200.00, 4,
 'v1.5.2', '2024-07-08 09:45:00+00', 'production'),

('LIQUIDITY_SWEEP_V3', 'coinbase', 'SOL/USDT', '1h', 'bull', 'MATURE', true,
 '{"pierce_depth": 0.16, "rejection_candles": 2, "volume_spike_threshold": 2.7}'::jsonb,
 0.6920, 520.00, -240.00, 28600.00, 132,
 2.02, 0.94, 3000.00, 6,
 'v3.2.1', '2024-05-20 11:15:00+00', 'production');

COMMIT;

-- =============================================================================
-- Verification Queries
-- =============================================================================

-- Count by status
SELECT status, COUNT(*) as count
FROM trained_configurations
GROUP BY status
ORDER BY status;

-- Count by strategy
SELECT strategy_name, COUNT(*) as count
FROM trained_configurations
GROUP BY strategy_name
ORDER BY count DESC;

-- Active configurations
SELECT strategy_name, exchange, pair, timeframe, regime, net_profit, sharpe_ratio
FROM trained_configurations
WHERE is_active = true
ORDER BY net_profit DESC;

-- Total configurations
SELECT COUNT(*) as total_configurations FROM trained_configurations;
