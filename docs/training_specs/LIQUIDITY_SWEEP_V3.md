# LIQUIDITY SWEEP V3 - Training Specification

## Objective
Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "LIQUIDITY SWEEP V3" trading pattern based on the provided runtime inputs.

---

## Runtime Inputs
- **Target Pairs**: `[USER_PROVIDED_PAIRS_FROM_INPUT]`
- **Target Exchanges**: `[DYNAMICALLY_FETCH_CONNECTED_EXCHANGES]`

---

## Core Iteration Matrix
You must iterate through every possible combination of the following variables:
- **Exchanges**: Use the provided [Target Exchanges] list
- **Trading Pairs**: Use the provided [Target Pairs] list
- **Regimes**: Use the output from the [ENSEMBLE CLASSIFIER - multiple timeframes]
- **Timeframes**: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`

---

## Data & Optimization Mandate
For each unique combination (e.g., Binance, BTC/USDT, 1h), you must:
1. Connect to that exchange's API (Binance)
2. Pull the necessary historical market data (OHLCV) for that pair and timeframe (BTC/USDT, 1h)
3. This data, combined with alternative data streams, is the required input for the discovery task

---

## Discovery Task (Per Combination)
Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize **NET_PROFIT**.

### Parameters to Discover
| Parameter | Test Range | Description |
|-----------|------------|-------------|
| `pierce_depth` | 0.05% to 0.5% | How far price pierces through the key level |
| `rejection_candles` | 1 to 5 | Number of candles showing rejection |
| `volume_spike_threshold` | 1.5x to 5x | Volume multiplier vs average |
| `reversal_candle_size` | 0.5 to 2.0 ATR | Size of reversal candle |
| `key_level_lookback` | 20 to 200 periods | How far back to identify key levels |
| `stop_distance` | 0.5 to 2.0 ATR | Stop loss distance |
| `target_multiple` | 1.5:1 to 4:1 | Risk-reward ratio |
| `min_stop_density_score` | 0.5 to 1.0 | Minimum stop cluster score |
| `max_spread_tolerance` | 1 to 10 bps | Maximum spread allowed |

---

## Validation, Governance, & Lifecycle

### Lifecycle Stage Rules

| Stage | Criteria | Position Size | Priority |
|-------|----------|---------------|----------|
| **DISCOVERY** | sample < 30 | 0.25x | low latency priority |
| **VALIDATION** | sample 30-100, p_value < 0.05 | 0.5x | medium priority |
| **MATURE** | sample > 100, sharpe > 1.5, adverse_selection < 0.3 | 1.0x | high priority |
| **DECAY** | performance_degradation > -20% OR death_signal triggered | 0x | monitoring only |
| **PAPER** | NET_PROFIT < 0 OR sharpe < 0.5 OR fill_rate < 0.7 | 0x (simulated) | testing only |

### Aggressive Decay Rules

1. **If** `rolling_30d_sharpe < 0.5 * lifetime_sharpe` → **IMMEDIATE** move to PAPER
2. **If** `adverse_selection_score > 0.6` → **REDUCE** position 50%
3. **If** `death_signals_count >= 2` → **DECAY** status
4. **If** `fill_rate < 0.7` → **PAUSE** trading

### Circuit Breakers

- `max_daily_loss`: X
- `max_correlation_spike`: X
- `unusual_market_threshold`: X
- `latency_threshold_ms`: X
- `consecutive_losses_limit`: N
- `max_adverse_selection`: X
- `regime_break_threshold`: X

---

## Output Requirement
For every discovered configuration (all statuses), generate and output a single JSON object. This object must precisely follow the "V3 Universal Discovery Template" below, with all placeholders `[...]` populated with the actual discovered parameters, calculated metrics, and metadata.

### Required JSON Output Template (LIQUIDITY SWEEP V3)

```json
{
  "pair": "[TRADING_PAIR]",
  "pattern": "LIQUIDITY SWEEP V3",
  "configurations": [
    {
      "id": "[DYNAMICALLY_GENERATED_ID]",
      "status": "[DISCOVERY/VALIDATION/MATURE/DECAY/PAPER]",
      "metadata": {
        "model_version": "[MODEL_VERSION]",
        "discovery_date": "[DISCOVERY_TIMESTAMP]",
        "engine_hash": "[ENGINE_HASH]",
        "runtime_env": "[RUNTIME_ENVIRONMENT]"
      },
      "context": {
        "pair": "[TRADING_PAIR]",
        "exchange": "[EXCHANGE_NAME]",
        "timeframe": "[TIMEFRAME_VALUE]"
      },
      "parameters": {
        "pierce_depth": "[val]",
        "rejection_candles": "[val]",
        "volume_spike_threshold": "[val]",
        "reversal_candle_size": "[val]",
        "key_level_lookback": "[val]",
        "stop_distance": "[val]",
        "target_multiple": "[val]",
        "min_stop_density_score": "[val]",
        "max_spread_tolerance": "[val]"
      },
      "performance": {
        "gross_WR": "[val]",
        "avg_win": "[val]",
        "avg_loss": "[val]",
        "exchange_fees": "[val]",
        "est_slippage": "[val]",
        "actual_slippage": "[val]",
        "NET_PROFIT": "[val]",
        "sample_size": "[val]"
      },
      "statistical_validation": {
        "sharpe_ratio": "[val]",
        "calmar_ratio": "[val]",
        "sortino_ratio": "[val]",
        "p_value": "[val]",
        "z_score": "[val]",
        "monte_carlo_var": "[val]",
        "stability_score": "[val]",
        "drawdown_duration": "[val]",
        "trade_clustering": "[val]",
        "rolling_30d_sharpe": "[val]",
        "lifetime_sharpe_ratio": "[val]"
      },
      "execution_metrics": {
        "fill_rate": "[val]",
        "partial_fill_rate": "[val]",
        "time_to_fill_ms": "[val]",
        "slippage_vs_mid_bps": "[val]",
        "adverse_selection_score": "[val]",
        "post_trade_drift_1m": "[val]",
        "post_trade_drift_5m": "[val]",
        "rejection_rate": "[val]"
      },
      "ensemble_regime_classification": {
        "regime_models": {
          "model_1h": {
            "timeframe": "[val]",
            "weight": "[val]",
            "prediction": "[val]"
          },
          "model_4h": {
            "timeframe": "[val]",
            "weight": "[val]",
            "prediction": "[val]"
          },
          "model_1d": {
            "timeframe": "[val]",
            "weight": "[val]",
            "prediction": "[val]"
          },
          "model_volatility": {
            "type": "[val]",
            "weight": "[val]",
            "prediction": "[val]"
          }
        },
        "final_regime_probability": {
          "trending": "[val]",
          "ranging": "[val]",
          "volatile": "[val]"
        },
        "regime_transition_probability": "[val]",
        "regime_stability_score": "[val]"
      },
      "alternative_data_signals": {
        "order_flow_imbalance": "[val]",
        "options_flow": {
          "put_call_ratio": "[val]",
          "gamma_exposure": "[val]",
          "dealer_positioning": "[val]"
        },
        "funding_rate": "[val]",
        "perpetual_basis": "[val]",
        "social_sentiment": {
          "twitter_score": "[val]",
          "reddit_mentions": "[val]",
          "sentiment_velocity": "[val]"
        },
        "whale_activity_score": "[val]",
        "exchange_inflow_outflow": "[val]"
      },
      "adversarial_analysis": {
        "adversarial_score": "[val]",
        "trap_probability": "[val]",
        "smart_money_alignment": "[val]",
        "similar_patterns_detected": "[val]",
        "competitor_activity_level": "[val]",
        "unusual_mm_behavior": "[val]",
        "spoofing_detected": "[val]"
      },
      "risk_allocation": {
        "kelly_fraction": "[val]",
        "correlation_adjusted_weight": "[val]",
        "regime_adjusted_size": "[val]",
        "max_position_size": "[val]",
        "current_allocation": "[val]",
        "var_95": "[val]",
        "cvar_95": "[val]"
      },
      "market_microstructure": {
        "avg_spread_bps": "[val]",
        "book_depth_ratio": "[val]",
        "book_imbalance": "[val]",
        "tick_size_impact": "[val]",
        "maker_rebate": "[val]",
        "taker_fee": "[val]",
        "level2_depth_score": "[val]",
        "microstructure_noise": "[val]"
      },
      "pattern_health": {
        "months_since_discovery": "[val]",
        "performance_degradation": "[val]",
        "degradation_velocity": "[val]",
        "death_signals": {
          "volume_profile_changed": "[val]",
          "new_algo_detected": "[val]",
          "correlation_spike": "[val]",
          "sharpe_below_50pct": "[val]",
          "unusual_fill_pattern": "[val]",
          "regime_break": "[val]"
        },
        "death_signal_count": "[val]",
        "resurrection_score": "[val]",
        "correlation_to_other_patterns": {
          "[pattern_name]": "[val]"
        }
      },
      "circuit_breakers": {
        "max_daily_loss": "[val]",
        "max_correlation_spike": "[val]",
        "unusual_market_threshold": "[val]",
        "latency_threshold_ms": "[val]",
        "consecutive_losses_limit": "[val]",
        "max_adverse_selection": "[val]",
        "regime_break_threshold": "[val]"
      },
      "meta_learning_outputs": {
        "pattern_failure_predictors": "[list]",
        "optimal_market_conditions": "[desc]",
        "edge_expiration_estimate": "[val]",
        "recommended_alternatives": "[list]"
      }
    }
  ]
}
```

---

## Implementation Notes

### Strategy Logic
The Liquidity Sweep pattern identifies when price temporarily pierces a key level (stop loss cluster) and then reverses. This is a trap for retail traders who place stops at obvious levels.

**Entry Conditions:**
1. Identify key support/resistance level with high stop density
2. Price pierces through level by `pierce_depth` %
3. Volume spike > `volume_spike_threshold` × average volume
4. Reversal candle appears within `rejection_candles` candles
5. Reversal candle size > `reversal_candle_size` ATR

**Exit Conditions:**
- Stop Loss: `stop_distance` ATR below/above entry
- Take Profit: `target_multiple` × stop distance

### Data Requirements
- Historical OHLCV data (minimum 200 candles for `key_level_lookback`)
- Volume data (for spike detection)
- Alternative data (optional but recommended):
  - Order flow data
  - Funding rates
  - Social sentiment

### Performance Metrics Priority
1. **NET_PROFIT** (primary optimization target)
2. **Sharpe Ratio** (risk-adjusted returns)
3. **Fill Rate** (execution feasibility)
4. **Adverse Selection Score** (edge degradation)
