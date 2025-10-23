# FAILED BREAKDOWN (SPRING) V3 - Training Specification

## Objective
Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "FAILED BREAKDOWN (SPRING) V3" trading pattern based on the provided runtime inputs.

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
For each unique combination (e.g., Coinbase, SOL/USDC, 4h), you must:
1. Connect to that exchange's API (Coinbase)
2. Pull the necessary historical market data (OHLCV) for that pair and timeframe (SOL/USDC, 4h)
3. This data, combined with alternative data streams, is the required input for the discovery task

---

## Discovery Task (Per Combination)
Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize **NET_PROFIT**.

### Parameters to Discover
| Parameter | Test Range | Description |
|-----------|------------|-------------|
| `range_lookback_periods` | 20 to 200 | Periods to identify trading range |
| `breakdown_depth` | 0.5% to 2% | How far below support the breakdown goes |
| `volume_decline_threshold` | 0.3x to 0.7x avg | Volume decline indicating weakness |
| `recovery_speed` | 1 to 5 candles | Speed of recovery back into range |
| `spring_confirmation_volume` | 1.5x to 4x | Volume on spring confirmation |
| `stop_distance` | Below spring low | Stop placement below the spring |
| `target_multiple` | To range high | Target at top of range or beyond |
| `accumulation_score_min` | 0.6 to 0.9 | Minimum accumulation evidence |
| `wyckoff_phase_alignment` | Phase C/D detection | Wyckoff methodology alignment |

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

### Required JSON Output Template (FAILED BREAKDOWN V3)

```json
{
  "pair": "[TRADING_PAIR]",
  "pattern": "FAILED BREAKDOWN (SPRING) V3",
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
        "range_lookback_periods": "[val]",
        "breakdown_depth": "[val]",
        "volume_decline_threshold": "[val]",
        "recovery_speed": "[val]",
        "spring_confirmation_volume": "[val]",
        "stop_distance": "[val]",
        "target_multiple": "[val]",
        "accumulation_score_min": "[val]",
        "wyckoff_phase_alignment": "[val]"
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
        "on_chain_accumulation": "[val]",
        "exchange_balance_change": "[val]",
        "dormant_coins_moved": "[val]",
        "miner_distribution": "[val]"
      },
      "adversarial_analysis": {
        "adversarial_score": "[val]",
        "false_breakdown_trap": "[val]",
        "smart_money_positioning": "[val]",
        "composite_operator_score": "[val]",
        "distribution_detected": "[val]",
        "accumulation_confirmed": "[val]"
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

### Strategy Logic (Wyckoff Spring Pattern)
The Failed Breakdown (Spring) pattern is based on Wyckoff methodology. It identifies when composite operators (smart money) engineer a false breakdown below support to trap retail traders, then rapidly reverse the move to accumulate at better prices.

**Entry Conditions:**
1. **Identify Trading Range**: Use `range_lookback_periods` to identify a consolidation range with clear support/resistance
2. **Breakdown Detection**: Price breaks below support by `breakdown_depth` %
3. **Volume Clue**: Volume during breakdown is WEAK (< `volume_decline_threshold` × average) - indicates lack of genuine selling pressure
4. **Spring Recovery**: Price recovers back into range within `recovery_speed` candles
5. **Confirmation Volume**: Recovery happens with strong volume > `spring_confirmation_volume` × average
6. **Accumulation Evidence**: Accumulation score > `accumulation_score_min` (on-chain, order flow, etc.)
7. **Wyckoff Phase**: Confirm Phase C (test) or Phase D (sign of strength)

**Exit Conditions:**
- Stop Loss: Below spring low (the breakdown low)
- Take Profit: Range high or beyond (measuring move = range height projected upward)

### Wyckoff Phases
- **Phase A**: Stopping action (selling climax)
- **Phase B**: Building cause (accumulation)
- **Phase C**: Test (spring) - **THIS IS OUR PATTERN**
- **Phase D**: Sign of strength (markup begins)
- **Phase E**: Markup (trend)

### Data Requirements
- Historical OHLCV data (minimum 200 candles for range identification)
- Volume data (critical for weak breakdown + strong recovery detection)
- Alternative data (highly recommended):
  - On-chain accumulation metrics
  - Exchange balance changes (whales moving to/from exchanges)
  - Order flow imbalance
  - Composite operator score (Wyckoff-specific)

### Performance Metrics Priority
1. **NET_PROFIT** (primary optimization target)
2. **Fill Rate** (must execute at spring, not before/after)
3. **Adversarial Score** (false breakdown traps are the pattern, but can also trap us!)
4. **Sharpe Ratio** (risk-adjusted returns)

### Special Considerations
- **Pattern Rarity**: Springs are relatively rare compared to other patterns
- **False Positives**: Not every breakdown is a spring - many are genuine breakdowns
- **Regime Dependency**: Works best in ranging markets, poorly in trending markets
- **Timeframe**: Higher timeframes (4h, 1d) tend to have more reliable springs than lower timeframes
- **Volume Profile**: Volume analysis is CRITICAL - weak breakdown volume is the key signal
