# Strategy Comparison Matrix

Quick reference for discussing and comparing the 4 main trading strategies.

---

## Strategy Summary Table

| Strategy | Pattern Type | Best Regime | Rarity | Complexity | Data Needs |
|----------|--------------|-------------|--------|------------|------------|
| **LIQUIDITY SWEEP** | Counter-trend | Ranging | Common | ⭐⭐ Low | OHLCV + Volume |
| **CAPITULATION REVERSAL** | Exhaustion | Volatile | Medium | ⭐⭐⭐ Medium | OHLCV + Liquidations + Sentiment |
| **FAILED BREAKDOWN (SPRING)** | Wyckoff | Ranging | Rare | ⭐⭐⭐⭐ High | OHLCV + On-Chain + Order Flow |
| **SUPPLY SHOCK (MACRO)** | Momentum | All | Very Rare | ⭐⭐⭐⭐⭐ Very High | OHLCV + **NEWS FEED** |

---

## Parameter Count Comparison

| Strategy | Number of Parameters | Optimization Complexity |
|----------|---------------------|------------------------|
| **LIQUIDITY SWEEP** | 9 parameters | 9-dimensional search |
| **CAPITULATION REVERSAL** | 9 parameters | 9-dimensional search |
| **FAILED BREAKDOWN** | 9 parameters | 9-dimensional search |
| **SUPPLY SHOCK** | 9 parameters | 9-dimensional search |

**Note**: Each strategy has exactly 9 parameters by design for consistency.

---

## Data Requirements Breakdown

### LIQUIDITY SWEEP ✅ Easiest
```
Required:
✅ OHLCV data (via ccxt)
✅ Volume data (included in OHLCV)
✅ ATR indicator (calculated from OHLCV)

Optional:
⭕ Order flow data (for stop density score)
⭕ Spread data (for execution quality)
```

### CAPITULATION REVERSAL ⚠️ Medium Difficulty
```
Required:
✅ OHLCV data (via ccxt)
✅ Volume data (included in OHLCV)
✅ RSI indicator (calculated from OHLCV)
✅ ATR indicator (calculated from OHLCV)
⚠️ Liquidation data (CoinGlass, Glassnode)
⚠️ Funding rates (exchange APIs)
⚠️ Social sentiment (Twitter API, Reddit API)

Optional:
⭕ Options flow (Deribit API)
⭕ Fear & Greed index
```

### FAILED BREAKDOWN (SPRING) ⚠️ Hard
```
Required:
✅ OHLCV data (via ccxt)
✅ Volume data (included in OHLCV)
✅ ATR indicator (calculated from OHLCV)
⚠️ On-chain accumulation (Glassnode, IntoTheBlock)
⚠️ Exchange balance changes (Glassnode)
⚠️ Order flow imbalance (Level 2 orderbook data)

Optional:
⭕ Composite operator score (custom Wyckoff calculation)
⭕ Dormant coins moved
⭕ Miner distribution
```

### SUPPLY SHOCK (MACRO) 🔴 Very Hard
```
Required:
✅ OHLCV data (via ccxt)
✅ Volume data (included in OHLCV)
✅ ATR indicator (calculated from OHLCV)
🔴 NEWS FEED (CryptoCompare, CoinTelegraph, Bloomberg)
🔴 News sentiment analysis (NLP pipeline)
🔴 News credibility scoring
🔴 Event magnitude classification

Optional:
⭕ Macro indicators (DXY, SPY, VIX, bond yields)
⭕ Options flow (unusual activity detection)
⭕ Insider trading signals
⭕ Front-running detection
```

**Legend**:
- ✅ Easy (available via free APIs or calculable)
- ⚠️ Medium (requires paid APIs or custom calculation)
- 🔴 Hard (requires complex integration or NLP)
- ⭕ Optional (improves performance but not required)

---

## Implementation Roadmap

### Phase 1: MVP - LIQUIDITY SWEEP ONLY
**Timeline**: Week 1-2  
**Goal**: Prove the training pipeline works

```
Sprint 1.1: Data Pipeline
- [ ] Connect to ccxt for OHLCV
- [ ] Calculate ATR, volume averages
- [ ] Store in market_data table

Sprint 1.2: Backtest Engine
- [ ] Implement signal detection logic
- [ ] Calculate entry/exit points
- [ ] Track trades and PnL

Sprint 1.3: Optimization
- [ ] Grid search over 9 parameters
- [ ] Rank by NET_PROFIT
- [ ] Calculate Sharpe, win rate, etc.

Sprint 1.4: Storage
- [ ] Generate configuration JSON
- [ ] Insert into trained_configurations
- [ ] Assign lifecycle stage
```

**Deliverable**: 10+ LIQUIDITY SWEEP configurations in database

---

### Phase 2: Add CAPITULATION REVERSAL
**Timeline**: Week 3-4  
**Goal**: Add alternative data integration

```
Sprint 2.1: Liquidation Data
- [ ] Integrate CoinGlass API
- [ ] Pull 24h liquidation volumes
- [ ] Store in database

Sprint 2.2: Sentiment Data
- [ ] Twitter API integration
- [ ] Fear & Greed index
- [ ] Sentiment scoring

Sprint 2.3: Strategy Implementation
- [ ] RSI calculation
- [ ] Panic score composite
- [ ] Smart money divergence

Sprint 2.4: Training
- [ ] Run full training pipeline
- [ ] Generate configurations
- [ ] Validate against LIQUIDITY SWEEP
```

**Deliverable**: 10+ CAPITULATION REVERSAL configurations + 10+ LIQUIDITY SWEEP = 20+ total

---

### Phase 3: Add FAILED BREAKDOWN (SPRING)
**Timeline**: Week 5-6  
**Goal**: Add on-chain data and Wyckoff logic

```
Sprint 3.1: On-Chain Data
- [ ] Glassnode API integration
- [ ] Exchange balance tracking
- [ ] Accumulation score calculation

Sprint 3.2: Order Flow
- [ ] Level 2 orderbook data
- [ ] Order flow imbalance calculation
- [ ] Book depth analysis

Sprint 3.3: Wyckoff Implementation
- [ ] Range detection algorithm
- [ ] Spring pattern recognition
- [ ] Phase classification (A, B, C, D, E)

Sprint 3.4: Training
- [ ] Full training pipeline
- [ ] Generate configurations
- [ ] Validate spring detection
```

**Deliverable**: 30+ configurations across 3 strategies

---

### Phase 4: Add SUPPLY SHOCK (MACRO)
**Timeline**: Week 7-8  
**Goal**: Add news feed and event-driven logic

```
Sprint 4.1: News Integration
- [ ] CryptoCompare News API
- [ ] News sentiment NLP pipeline
- [ ] Source credibility database

Sprint 4.2: Event Detection
- [ ] Catalyst classification
- [ ] Event magnitude scoring
- [ ] Deduplication logic

Sprint 4.3: Macro Data
- [ ] DXY, SPY correlation tracking
- [ ] VIX level monitoring
- [ ] Bond yield data

Sprint 4.4: Training
- [ ] Full training pipeline
- [ ] Generate configurations
- [ ] Validate event detection
```

**Deliverable**: 40+ configurations across 4 strategies

---

## Strategy-Specific Challenges

### LIQUIDITY SWEEP
**Challenge**: Identifying "key levels" with high stop density  
**Solution**: Use swing highs/lows from `key_level_lookback` periods  
**Fallback**: Use round numbers (e.g., BTC $40,000, $50,000)

### CAPITULATION REVERSAL
**Challenge**: Distinguishing real capitulation from fake moves  
**Solution**: Use adversarial_analysis metrics + multi-signal confirmation  
**Fallback**: Require very extreme RSI (<10 or >90) for high confidence

### FAILED BREAKDOWN (SPRING)
**Challenge**: Identifying genuine accumulation vs noise  
**Solution**: Wyckoff volume analysis (weak breakdown + strong recovery)  
**Fallback**: Require very long ranges (100+ periods) for clear springs

### SUPPLY SHOCK (MACRO)
**Challenge**: Real-time news processing and false news detection  
**Solution**: Source credibility scoring + multiple source confirmation  
**Fallback**: Only trade "official" news (SEC announcements, exchange listings)

---

## Critical Questions for Discussion

### 1. Parameter Optimization Method
**Options**:
- **Grid Search**: Exhaustive, slow, guaranteed to find best in grid
- **Random Search**: Faster, still covers space well
- **Bayesian Optimization**: Smartest, but complex to implement
- **Genetic Algorithm**: Good for high-dimensional spaces

**Recommendation**: Start with **Grid Search** for LIQUIDITY SWEEP (simple, interpretable), then move to **Bayesian** for later strategies.

### 2. Walk-Forward Validation
**Options**:
- **Fixed Windows**: Train on 6 months, test on 1 month, roll forward
- **Expanding Windows**: Train on all data up to point, test on next period
- **Anchored Windows**: Always train from start, test on different periods

**Recommendation**: **Fixed Windows** with 3-month train, 1-month test, 1-month gap.

### 3. Lifecycle Stage Promotion
**Question**: How do configurations move from DISCOVERY → VALIDATION → MATURE?

**Options**:
- **Automatic**: Based purely on metrics (sample_size, sharpe, etc.)
- **Manual Review**: Human approves each promotion
- **Hybrid**: Auto DISCOVERY→VALIDATION, manual VALIDATION→MATURE

**Recommendation**: **Hybrid** - auto early stages, manual for live trading.

### 4. Circuit Breaker Values
**Need to Define**:
```python
circuit_breakers = {
    "max_daily_loss": ???,           # Suggestion: 2% of portfolio
    "max_correlation_spike": ???,     # Suggestion: 0.8 (configs become too correlated)
    "unusual_market_threshold": ???,  # Suggestion: VIX > 50 equivalent
    "latency_threshold_ms": ???,      # Suggestion: 500ms
    "consecutive_losses_limit": ???,  # Suggestion: 5 trades
    "max_adverse_selection": ???,     # Suggestion: 0.6
    "regime_break_threshold": ???     # Suggestion: regime prob < 0.3
}
```

### 5. Alternative Data Budget
**Question**: Which alternative data sources are worth paying for?

**Free**:
- OHLCV (ccxt)
- Funding rates (exchange APIs)
- Basic sentiment (Twitter API free tier)

**Paid**:
- Glassnode (~$800/month for pro)
- CoinGlass (~$300/month)
- CryptoCompare News (~$500/month)
- Bloomberg Terminal (~$2,000/month)

**Recommendation**: Start with **free data only** for Phase 1-2, add Glassnode for Phase 3.

---

## Performance Target Matrix

What should we expect from each strategy?

| Strategy | Target Win Rate | Target Sharpe | Target Sample Size (1 year) | Expected NET_PROFIT |
|----------|----------------|---------------|----------------------------|-------------------|
| **LIQUIDITY SWEEP** | 50-60% | 1.0-1.5 | 100-300 trades | 5-15% |
| **CAPITULATION REVERSAL** | 60-70% | 1.5-2.5 | 20-50 trades | 10-25% |
| **FAILED BREAKDOWN** | 55-65% | 1.2-2.0 | 10-30 trades | 8-20% |
| **SUPPLY SHOCK** | 65-75% | 2.0-3.0 | 5-15 trades | 15-40% |

**Notes**:
- LIQUIDITY SWEEP: Most frequent, lower edge per trade
- CAPITULATION REVERSAL: Medium frequency, higher edge
- FAILED BREAKDOWN: Rare, medium edge, requires patience
- SUPPLY SHOCK: Very rare, highest edge, event-dependent

---

## Recommended Discussion Topics

1. **Start with LIQUIDITY SWEEP only?** Or implement 2 strategies in parallel?
2. **Parameter ranges realistic?** Should we narrow/expand any?
3. **Lifecycle criteria too strict?** Sample size > 100 might take months
4. **Alternative data priority?** Which data sources to integrate first?
5. **Optimization budget?** How many parameter combinations per strategy?
6. **Backtesting period?** How much historical data to use?
7. **Multiple timeframes?** Train separate configs for 5m, 1h, 4h, 1d or combine?
8. **Ensemble approach?** Should we combine multiple strategies or keep separate?

---

**Ready to discuss!** 🚀
