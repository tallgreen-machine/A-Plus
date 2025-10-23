# CAPITULATION REVERSAL V3 - Training Specification

## Objective
Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "CAPITULATION REVERSAL V3" trading pattern based on the provided runtime inputs.

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
For each unique combination (e.g., Kraken, ETH/USDT, 5m), you must:
1. Connect to that exchange's API (Kraken)
2. Pull the necessary historical market data (OHLCV) for that pair and timeframe (ETH/USDT, 5m)
3. This data, combined with alternative data streams, is the required input for the discovery task

---

## Discovery Task (Per Combination)
Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize **NET_PROFIT**.

### Parameters to Discover
| Parameter | Test Range | Description |
|-----------|------------|-------------|
| `volume_explosion_threshold` | 3x to 10x avg | Volume surge multiplier indicating panic |
| `price_move_speed` | 2% to 10% per candle | Speed of price collapse |
| `sentiment_extreme_threshold` | RSI <20 or >80 | RSI levels indicating extreme sentiment |
| `exhaustion_wick_ratio` | 1.5 to 4.0 | Wick size ratio vs candle body (exhaustion) |
| `reversal_confirmation_candles` | 1 to 3 | Number of candles confirming reversal |
| `stop_distance` | 1.0 to 3.0 ATR | Stop loss distance below entry |
| `target_multiple` | 2:1 to 5:1 | Risk-reward ratio |
| `panic_score_minimum` | 0.6 to 0.9 | Minimum panic composite score |
| `smart_money_divergence` | 0.4 to 0.8 | Smart money buying vs retail selling |

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

### Required JSON Output Template (CAPITULATION REVERSAL V3)

```json
{
  "pair": "[TRADING_PAIR]",
  "pattern": "CAPITULATION REVERSAL V3",
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
        "volume_explosion_threshold": "[val]",
        "price_move_speed": "[val]",
        "sentiment_extreme_threshold": "[val]",
        "exhaustion_wick_ratio": "[val]",
        "reversal_confirmation_candles": "[val]",
        "stop_distance": "[val]",
        "target_multiple": "[val]",
        "panic_score_minimum": "[val]",
        "smart_money_divergence": "[val]"
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
          "dealer_positioning": "[val]",
          "vix_term_structure": "[val]"
        },
        "funding_rate": "[val]",
        "perpetual_basis": "[val]",
        "social_sentiment": {
          "fear_greed_index": "[val]",
          "panic_words_frequency": "[val]",
          "capitulation_mentions": "[val]"
        },
        "long_liquidations_24h": "[val]",
        "short_liquidations_24h": "[val]"
      },
      "adversarial_analysis": {
        "adversarial_score": "[val]",
        "fake_capitulation_probability": "[val]",
        "smart_money_accumulation": "[val]",
        "institutional_buying_detected": "[val]",
        "wash_trading_score": "[val]",
        "manipulation_indicators": "[val]"
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
The Capitulation Reversal pattern identifies extreme panic selling (or buying in a short) where price collapses rapidly with massive volume, followed by an exhaustion reversal. This catches the moment when weak hands capitulate and smart money accumulates.

**Entry Conditions:**
1. Volume explosion > `volume_explosion_threshold` × average volume
2. Price moves `price_move_speed` % per candle (rapid collapse)
3. RSI reaches extreme (`sentiment_extreme_threshold` < 20 for longs, > 80 for shorts)
4. Exhaustion wick appears with ratio > `exhaustion_wick_ratio`
5. Reversal confirmed within `reversal_confirmation_candles` candles
6. Panic score > `panic_score_minimum` (composite indicator)
7. Smart money divergence detected > `smart_money_divergence` (large players buying while retail sells)

**Exit Conditions:**
- Stop Loss: `stop_distance` ATR below/above exhaustion low/high
- Take Profit: `target_multiple` × stop distance

### Data Requirements
- Historical OHLCV data
- Volume data (critical for explosion detection)
- RSI indicator
- Alternative data (highly recommended):
  - Liquidation data (long/short liquidations)
  - Funding rates (perpetual futures)
  - Social sentiment (fear/greed, panic mentions)
  - Options flow (put/call ratio, dealer positioning)
  - Order flow imbalance

### Performance Metrics Priority
1. **NET_PROFIT** (primary optimization target)
2. **Sharpe Ratio** (volatility-adjusted returns critical for this strategy)
3. **Adverse Selection Score** (fake capitulations are common)
4. **Fill Rate** (must execute during panic)

### Special Considerations
- **False Signals**: Capitulation can be faked by market makers. Use `adversarial_analysis` to detect fake capitulation
- **Slippage**: High during panic - `actual_slippage` often exceeds `est_slippage`
- **Timing**: Entry timing is critical - too early catches falling knife, too late misses reversal
- **Regime Dependency**: Works best in volatile regimes, poorly in ranging markets
