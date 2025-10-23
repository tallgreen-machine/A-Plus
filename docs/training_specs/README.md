# Training Specifications Index

This directory contains the complete training specifications for all V3 trading strategies. These documents were extracted from the V2 Dashboard Strategy Studio mock data and serve as the authoritative guide for implementing the training system.

---

## Overview

Each strategy specification defines:
- **Objective**: What the strategy aims to accomplish
- **Core Iteration Matrix**: Exchange × Pair × Timeframe × Regime combinations
- **Parameter Search Spaces**: Ranges for optimization
- **Lifecycle Management**: DISCOVERY → VALIDATION → MATURE → DECAY → PAPER
- **Output Schema**: V3 Universal Discovery Template (JSON)
- **Implementation Notes**: Strategy logic, entry/exit conditions, special considerations

---

## Strategy Specifications

### 1. [LIQUIDITY SWEEP V3](./LIQUIDITY_SWEEP_V3.md)
**Pattern Type**: Counter-trend reversal  
**Core Concept**: Identifies when price temporarily pierces a key level (stop loss cluster) and then reverses  
**Best Regime**: Ranging markets with clear support/resistance  
**Sample Size Target**: 100+ samples for MATURE status  

**Key Parameters**:
- `pierce_depth`: 0.05% to 0.5%
- `rejection_candles`: 1 to 5
- `volume_spike_threshold`: 1.5x to 5x
- `key_level_lookback`: 20 to 200 periods

**Data Dependencies**: OHLCV, Volume, Order Flow (optional)

---

### 2. [CAPITULATION REVERSAL V3](./CAPITULATION_REVERSAL_V3.md)
**Pattern Type**: Exhaustion reversal  
**Core Concept**: Catches extreme panic selling/buying followed by exhaustion reversal  
**Best Regime**: Volatile markets  
**Sample Size Target**: 100+ samples for MATURE status  

**Key Parameters**:
- `volume_explosion_threshold`: 3x to 10x avg
- `price_move_speed`: 2% to 10% per candle
- `sentiment_extreme_threshold`: RSI <20 or >80
- `exhaustion_wick_ratio`: 1.5 to 4.0
- `panic_score_minimum`: 0.6 to 0.9

**Data Dependencies**: OHLCV, Volume, RSI, Liquidation Data, Funding Rates, Social Sentiment

---

### 3. [FAILED BREAKDOWN (SPRING) V3](./FAILED_BREAKDOWN_SPRING_V3.md)
**Pattern Type**: Wyckoff accumulation  
**Core Concept**: False breakdown below support (spring) engineered by composite operators  
**Best Regime**: Ranging markets (consolidation)  
**Sample Size Target**: 100+ samples for MATURE status  

**Key Parameters**:
- `range_lookback_periods`: 20 to 200
- `breakdown_depth`: 0.5% to 2% below support
- `volume_decline_threshold`: 0.3x to 0.7x avg (WEAK breakdown volume)
- `recovery_speed`: 1 to 5 candles
- `spring_confirmation_volume`: 1.5x to 4x (STRONG recovery volume)
- `accumulation_score_min`: 0.6 to 0.9

**Data Dependencies**: OHLCV, Volume, On-Chain Accumulation, Order Flow, Composite Operator Score

---

### 4. [SUPPLY SHOCK (MACRO) V3](./SUPPLY_SHOCK_MACRO_V3.md)
**Pattern Type**: Momentum continuation  
**Core Concept**: Major news catalysts creating sustained directional momentum  
**Best Regime**: All regimes (regime-independent)  
**Sample Size Target**: 100+ samples for MATURE status (but events are rare)  

**Key Parameters**:
- `gap_threshold`: 1% to 5% from previous close
- `volume_surge_multiplier`: 5x to 20x
- `momentum_persistence`: 3 to 10 consecutive candles
- `news_sentiment_score`: -1 to +1
- `catalyst_strength_minimum`: 0.6 to 0.9
- `trail_stop_activation`: 1.5 to 3.0 ATR

**Data Dependencies**: OHLCV, Volume, **NEWS FEED (CRITICAL)**, Sentiment Analysis, Macro Indicators, Options Flow

---

## Common Elements Across All Strategies

### Lifecycle Stage Rules (Applies to ALL strategies)

| Stage | Sample Size | Position Size | Sharpe | Adverse Selection |
|-------|-------------|---------------|--------|-------------------|
| **DISCOVERY** | < 30 | 0.25x | Any | Any |
| **VALIDATION** | 30-100 | 0.5x | p_value < 0.05 | Any |
| **MATURE** | > 100 | 1.0x | > 1.5 | < 0.3 |
| **DECAY** | Any | 0x | degradation > -20% | OR death_signal |
| **PAPER** | Any | 0x (sim) | < 0.5 OR NET_PROFIT < 0 | OR fill_rate < 0.7 |

### Aggressive Decay Rules (Applies to ALL strategies)

1. **If** `rolling_30d_sharpe < 0.5 * lifetime_sharpe` → **IMMEDIATE** move to PAPER
2. **If** `adverse_selection_score > 0.6` → **REDUCE** position 50%
3. **If** `death_signals_count >= 2` → **DECAY** status
4. **If** `fill_rate < 0.7` → **PAUSE** trading

### Circuit Breakers (Applies to ALL strategies)

- `max_daily_loss`: Global risk limit
- `max_correlation_spike`: Correlation breakdown detection
- `unusual_market_threshold`: Anomaly detection
- `latency_threshold_ms`: Execution latency limit
- `consecutive_losses_limit`: Streak protection
- `max_adverse_selection`: Edge degradation limit
- `regime_break_threshold`: Regime change detection

---

## V3 Universal Discovery Template Schema

All strategies output the same JSON schema with these top-level sections:

```json
{
  "pair": "string",
  "pattern": "string (strategy name)",
  "configurations": [
    {
      "id": "string (UUID)",
      "status": "DISCOVERY|VALIDATION|MATURE|DECAY|PAPER",
      "metadata": {...},
      "context": {...},
      "parameters": {...},              // Strategy-specific parameters
      "performance": {...},              // Core performance metrics
      "statistical_validation": {...},   // Sharpe, Calmar, p-value, etc.
      "execution_metrics": {...},        // Fill rate, slippage, adverse selection
      "ensemble_regime_classification": {...},  // Multi-timeframe regime detection
      "alternative_data_signals": {...}, // Order flow, funding, sentiment, etc.
      "adversarial_analysis": {...},     // Trap detection, manipulation indicators
      "risk_allocation": {...},          // Kelly, VaR, CVaR, position sizing
      "market_microstructure": {...},    // Spread, depth, tick size, fees
      "pattern_health": {...},           // Degradation, death signals, correlations
      "circuit_breakers": {...},         // Risk limits
      "meta_learning_outputs": {...}     // Failure predictors, alternatives
    }
  ]
}
```

---

## Training Pipeline Architecture

### Phase 1: Data Collection
1. Connect to exchange APIs (ccxt)
2. Pull historical OHLCV for each pair × timeframe
3. Calculate technical indicators (RSI, ATR, etc.)
4. Fetch alternative data (funding, sentiment, etc.)

### Phase 2: Parameter Optimization
1. Define parameter search grid for strategy
2. Run backtests for each parameter combination
3. Calculate performance metrics (NET_PROFIT, Sharpe, etc.)
4. Rank configurations by NET_PROFIT

### Phase 3: Validation
1. Walk-forward analysis (train period → test period)
2. Out-of-sample testing
3. Statistical significance testing (p-value, z-score)
4. Assign lifecycle stage (DISCOVERY/VALIDATION/MATURE)

### Phase 4: Storage
1. Generate configuration ID (UUID)
2. Populate V3 Universal Discovery Template
3. Insert into `trained_configurations` table
4. Link to `training_jobs` table for tracking

---

## Implementation Priority

Based on data requirements and complexity:

1. **LIQUIDITY SWEEP** (Start Here)
   - Simplest data requirements (just OHLCV + Volume)
   - Clear entry/exit logic
   - Good for testing training pipeline

2. **CAPITULATION REVERSAL** (Second)
   - Requires liquidation data and sentiment
   - More complex signal logic
   - Tests alternative data integration

3. **FAILED BREAKDOWN (SPRING)** (Third)
   - Requires on-chain data and order flow
   - Wyckoff logic is sophisticated
   - Tests regime classification

4. **SUPPLY SHOCK (MACRO)** (Last)
   - Requires real-time news feed integration
   - Event-driven (not continuous)
   - Most complex data pipeline

---

## Next Steps

1. **Review and Discuss**: Examine each specification for completeness and clarity
2. **Refine Parameter Ranges**: Adjust ranges based on domain knowledge
3. **Design Training Engine**: Build the backtesting and optimization framework
4. **Implement LIQUIDITY SWEEP**: Start with simplest strategy as proof-of-concept
5. **Iterate**: Refine training pipeline based on results

---

## Questions to Address

1. **Parameter Optimization Method**: Grid search? Bayesian optimization? Genetic algorithms?
2. **Data Sources**: Which exchanges for historical data? Which APIs for alternative data?
3. **Regime Classification**: Implement ensemble classifier or use simpler heuristics?
4. **Validation Methodology**: Walk-forward period length? Train/test split ratio?
5. **Performance Thresholds**: Are the lifecycle stage criteria too strict/loose?
6. **Circuit Breakers**: What should the actual values be (X, N)?
7. **Alternative Data**: Which alternative data sources are realistic to integrate?
8. **Computational Budget**: How long should a full training run take? Parallel vs sequential?

---

**Last Updated**: 2025-10-23  
**Schema Version**: V3  
**Status**: Ready for Implementation Discussion
