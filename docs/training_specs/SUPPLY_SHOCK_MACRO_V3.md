# SUPPLY SHOCK (MACRO) V3 - Training Specification

## Objective
Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "SUPPLY SHOCK (MACRO) V3" trading pattern based on the provided runtime inputs.

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
For each unique combination (e.g., Bybit, ADA/USDT, 1d), you must:
1. Connect to that exchange's API (Bybit)
2. Pull the necessary historical market data (OHLCV) for that pair and timeframe (ADA/USDT, 1d)
3. This data, combined with alternative data streams, is the required input for the discovery task

---

## Discovery Task (Per Combination)
Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize **NET_PROFIT**.

### Parameters to Discover
| Parameter | Test Range | Description |
|-----------|------------|-------------|
| `gap_threshold` | 1% to 5% | Price gap from previous close (catalyst strength) |
| `volume_surge_multiplier` | 5x to 20x | Volume multiplier vs average |
| `momentum_persistence` | 3 to 10 candles | Number of consecutive directional candles |
| `news_sentiment_score` | -1 to +1 | News sentiment strength and direction |
| `no_retracement_periods` | 5 to 20 | Periods without significant pullback |
| `trail_stop_activation` | 1.5 to 3.0 ATR | When to activate trailing stop |
| `position_hold_maximum` | 5 to 30 candles | Maximum holding period |
| `catalyst_strength_minimum` | 0.6 to 0.9 | Minimum catalyst strength score |
| `continuation_probability` | 0.6 to 0.9 | Probability momentum continues |

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

### Required JSON Output Template (SUPPLY SHOCK V3)

```json
{
  "pair": "[TRADING_PAIR]",
  "pattern": "SUPPLY SHOCK (MACRO) V3",
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
        "gap_threshold": "[val]",
        "volume_surge_multiplier": "[val]",
        "momentum_persistence": "[val]",
        "news_sentiment_score": "[val]",
        "no_retracement_periods": "[val]",
        "trail_stop_activation": "[val]",
        "position_hold_maximum": "[val]",
        "catalyst_strength_minimum": "[val]",
        "continuation_probability": "[val]"
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
          "unusual_options_activity": "[val]"
        },
        "funding_rate": "[val]",
        "perpetual_basis": "[val]",
        "macro_indicators": {
          "dxy_correlation": "[val]",
          "spy_correlation": "[val]",
          "vix_level": "[val]",
          "bond_yield_direction": "[val]"
        },
        "news_analytics": {
          "headline_count": "[val]",
          "sentiment_score": "[val]",
          "source_credibility": "[val]",
          "event_magnitude": "[val]"
        }
      },
      "adversarial_analysis": {
        "adversarial_score": "[val]",
        "fake_news_probability": "[val]",
        "insider_trading_signals": "[val]",
        "pump_dump_indicators": "[val]",
        "coordinated_manipulation": "[val]",
        "front_running_detected": "[val]"
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
The Supply Shock (Macro) pattern identifies major market-moving events (news catalysts, regulatory changes, protocol upgrades, etc.) that create immediate and sustained directional momentum. This is a momentum-continuation strategy that rides the initial shock wave.

**Entry Conditions:**
1. **Catalyst Detection**: Major news event with strength > `catalyst_strength_minimum`
2. **Gap Detection**: Price gaps by > `gap_threshold` % from previous close
3. **Volume Surge**: Volume > `volume_surge_multiplier` × average volume
4. **Momentum Confirmation**: `momentum_persistence` consecutive directional candles
5. **News Sentiment**: Sentiment score matches direction (positive for longs, negative for shorts)
6. **No Retracement**: Price doesn't retrace significantly for `no_retracement_periods` candles
7. **Continuation Probability**: ML model predicts > `continuation_probability` chance of continuation

**Exit Conditions:**
- **Trailing Stop**: Activate after move of `trail_stop_activation` ATR, then trail
- **Time Exit**: Close after `position_hold_maximum` candles (momentum exhausts)
- **Reversal Signal**: Exit if momentum breaks (retracement appears)

### Catalyst Types
- **Regulatory**: SEC approvals, bans, lawsuits, policy changes
- **Protocol**: Upgrades, hard forks, network changes
- **Institutional**: Major company announcements (Tesla buying BTC, etc.)
- **Macro**: Fed decisions, inflation data, geopolitical events
- **Technical**: Major exchange listings, delistings
- **Black Swan**: Hacks, exchange failures, major bugs

### Data Requirements
- Historical OHLCV data
- Volume data (critical for surge detection)
- **News data** (critical - must have real-time news feed):
  - News headlines with timestamps
  - Sentiment analysis
  - Source credibility scores
  - Event magnitude classification
- Alternative data (highly recommended):
  - Social media sentiment velocity
  - Options flow (unusual activity)
  - Macro correlations (DXY, SPY, VIX, bonds)
  - Insider trading signals

### Performance Metrics Priority
1. **NET_PROFIT** (primary optimization target)
2. **Sharpe Ratio** (momentum can be volatile)
3. **Adverse Selection Score** (fake news is common)
4. **Fill Rate** (must execute quickly after catalyst)

### Special Considerations
- **Latency Critical**: Must detect and execute FAST (seconds matter)
- **Fake News**: Use `adversarial_analysis` to detect pump & dump schemes, fake news
- **Slippage**: Can be extreme during major events
- **Regime Independence**: Works in all regimes (trending, ranging, volatile)
- **Rarity**: True supply shocks are rare but extremely profitable when caught
- **Front-Running**: Watch for insider trading signals and front-running
- **Timeframe**: Higher timeframes (4h, 1d) more reliable than lower (1m, 5m)
- **Holding Period**: Typically short (5-30 candles) - momentum exhausts quickly

### News Analytics Integration
This strategy REQUIRES real-time news integration:
1. **News Feed**: Integrate CryptoCompare, CoinTelegraph, Bloomberg, Reuters
2. **NLP Pipeline**: Sentiment analysis, entity extraction, event classification
3. **Credibility Scoring**: Rank sources by reliability
4. **Event Magnitude**: Classify events by market impact potential
5. **Deduplication**: Avoid trading the same news multiple times
