# Training System - Quick Start Guide

**Last Updated**: October 23, 2025  
**Status**: Ready to Implement  
**First Target**: LIQUIDITY SWEEP V3 Strategy

---

## 📋 What We're Building

A complete training system to automatically discover profitable trading configurations by:
1. Fetching historical market data (OHLCV)
2. Testing thousands of parameter combinations
3. Validating with walk-forward analysis
4. Storing results in `trained_configurations` table
5. Making them available for live trading

---

## 🎯 Phase 1 Goals (Weeks 1-2)

✅ **Train LIQUIDITY SWEEP V3** on:
- 3 pairs: BTC/USDT, ETH/USDT, SOL/USDT
- 2 exchanges: Binance, Kraken
- 4 timeframes: 5m, 15m, 1h, 4h
- Total: 24 configurations to discover

✅ **Support 3 optimization methods**:
- Grid Search (exhaustive, slow, thorough)
- Random Search (fast, 99% quality of grid)
- Bayesian (smart, often better than grid!)

✅ **Flexible validation**:
- Walk-forward (train 3mo → test 1mo → roll)
- Configurable windows

✅ **Free data only**:
- OHLCV via ccxt (no paid APIs yet)
- Calculate our own indicators (ATR, SMA, etc.)

---

## 📁 Key Documents

| Document | Purpose | Read When |
|----------|---------|-----------|
| [TRAINING_IMPLEMENTATION_PLAN.md](./TRAINING_IMPLEMENTATION_PLAN.md) | Complete technical architecture | Implementing code |
| [training_specs/README.md](./training_specs/README.md) | Strategy specifications index | Understanding strategies |
| [training_specs/LIQUIDITY_SWEEP_V3.md](./training_specs/LIQUIDITY_SWEEP_V3.md) | Detailed LIQUIDITY SWEEP spec | Implementing signals |
| [training_specs/STRATEGY_COMPARISON.md](./training_specs/STRATEGY_COMPARISON.md) | Compare all 4 strategies | Planning future phases |
| [CIRCUIT_BREAKER_GUIDE.md](./CIRCUIT_BREAKER_GUIDE.md) | Risk management defaults | Setting up safety limits |
| [V2_GAP_ANALYSIS.md](./V2_GAP_ANALYSIS.md) | Current system gaps | Understanding big picture |

---

## 🚀 Implementation Sprints

### Sprint 1: Core Infrastructure
**Duration**: Week 1 (Days 1-5)

**Day 1-2**: Data Collection
- [ ] Create `training/data_collector.py`
- [ ] Implement ccxt OHLCV fetching
- [ ] Add indicator calculations (ATR, SMA)
- [ ] Test with BTC/USDT on Binance

**Day 3-4**: Backtest Engine
- [ ] Create `training/backtest_engine.py`
- [ ] Implement trade simulation logic
- [ ] Calculate performance metrics
- [ ] Test with dummy trades

**Day 5**: Strategy Implementation
- [ ] Create `training/strategies/liquidity_sweep.py`
- [ ] Implement signal detection logic
- [ ] Test on historical data
- [ ] Verify trades match expectations

---

### Sprint 2: Optimization Methods
**Duration**: Week 1 (Days 6-7) + Week 2 (Days 1-2)

**Day 6-7**: Grid & Random Search
- [ ] Create `training/optimizers/grid_search.py`
- [ ] Create `training/optimizers/random_search.py`
- [ ] Benchmark both methods
- [ ] Profile performance

**Day 1-2 (Week 2)**: Bayesian (Optional)
- [ ] Create `training/optimizers/bayesian.py`
- [ ] Integrate scikit-optimize
- [ ] Compare to grid/random
- [ ] Document when to use each

---

### Sprint 3: Validation & Storage
**Duration**: Week 2 (Days 3-5)

**Day 3-4**: Walk-Forward Validation
- [ ] Create `training/validator.py`
- [ ] Implement window splitting
- [ ] Calculate in-sample vs out-of-sample
- [ ] Detect overfitting

**Day 5**: Database Integration
- [ ] Create `training_jobs` table migration
- [ ] Create `training/configuration_writer.py`
- [ ] Implement JSON template generation
- [ ] Test full pipeline end-to-end

---

### Sprint 4: API & UI
**Duration**: Week 2 (Days 6-7) + Buffer

**Day 6**: Backend API
- [ ] Create `api/training_api.py`
- [ ] POST `/api/training/start` endpoint
- [ ] GET `/api/training/jobs/{id}` status endpoint
- [ ] GET `/api/training/jobs/{id}/results` endpoint

**Day 7**: Frontend UI
- [ ] Update `StrategyStudio.tsx` with training config panel
- [ ] Add market selection (pairs, exchanges, timeframes)
- [ ] Add optimization method selector
- [ ] Add runtime estimation

---

## 🔢 Resource Estimates

### Computational Cost

**Full Grid Search** (LIQUIDITY SWEEP):
- Parameter combinations: ~201,600
- Time per backtest: ~50ms
- Time per market: ~2.8 hours
- Total markets: 24 (3 pairs × 2 exchanges × 4 timeframes)
- **Sequential total: ~67 hours**
- **Parallel (8 cores): ~8.4 hours**

**Random Search** (1000 samples):
- Time per market: ~50 seconds
- **Total: ~20 minutes**

**Bayesian Optimization** (200 iterations):
- Time per market: ~10 seconds
- **Total: ~4 minutes**

### Recommendation
Start with **Random Search** for rapid iteration, then run **Bayesian** on promising markets for fine-tuning.

---

## 📊 Expected Results

After Phase 1 completion, you should have:

✅ **24+ configurations** in `trained_configurations` table
- Some in DISCOVERY (sample_size < 30)
- Some in VALIDATION (sample_size 30-100)
- Hopefully 1-2 in MATURE (sample_size > 100, sharpe > 1.5)

✅ **Performance metrics** for each:
- NET_PROFIT (primary optimization target)
- Sharpe Ratio (risk-adjusted returns)
- Win Rate, Avg Win, Avg Loss
- Max Drawdown, Calmar Ratio
- Sample Size (number of trades)

✅ **Validation results**:
- In-sample vs out-of-sample comparison
- Overfitting detection
- Statistical significance (p-value, z-score)

---

## 🎛️ Configuration Decisions Made

Based on your answers:

1. ✅ **Start with LIQUIDITY SWEEP** (simplest data requirements)
2. ✅ **Use parameter ranges from spec** (can refine later)
3. ✅ **Free data only** (OHLCV via ccxt)
4. ✅ **Multiple optimization methods** - Grid, Random, Bayesian (user selectable)
5. ✅ **Walk-forward validation** - 3mo train, 1mo test, 1wk gap (adjustable)
6. ✅ **Circuit breakers**:
   - max_daily_loss: 2%
   - max_correlation_spike: 0.8
   - unusual_market_threshold: 3.0σ
   - latency_threshold_ms: 500ms
   - consecutive_losses_limit: 5
   - max_adverse_selection: 0.6
   - regime_break_threshold: 0.3

---

## 🔧 Development Setup

### Backend Dependencies
```bash
pip install ccxt pandas numpy scipy scikit-optimize tqdm
```

### Database Migration
```bash
# Create training_jobs table
psql -d tradepulse -f sql/migrations/005_create_training_jobs.sql
```

### Directory Structure
```
training/
├── __init__.py
├── data_collector.py
├── backtest_engine.py
├── validator.py
├── configuration_writer.py
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py
│   └── liquidity_sweep.py
└── optimizers/
    ├── __init__.py
    ├── base_optimizer.py
    ├── grid_search.py
    ├── random_search.py
    └── bayesian.py
```

---

## 🧪 Testing Strategy

### Unit Tests (per component)
```python
# test_data_collector.py
def test_fetch_ohlcv_binance_btc():
    collector = DataCollector(['binance'])
    df = collector.fetch_ohlcv('binance', 'BTC/USDT', '5m', since='2024-01-01', until='2024-01-02')
    assert len(df) == 288  # 24 hours × 12 candles/hour
    assert 'close' in df.columns

# test_backtest_engine.py
def test_liquidity_sweep_signal_detection():
    strategy = LiquiditySweepStrategy()
    data = load_test_data('btc_liquidity_sweep_example.csv')
    params = {'pierce_depth': 0.002, 'volume_spike_threshold': 3.0, ...}
    
    signal = strategy.check_entry_signal(data, index=100, params=params)
    assert signal == True  # Known sweep at index 100

# test_optimizers.py
def test_grid_search_finds_optimum():
    optimizer = GridSearchOptimizer()
    backtest_engine = BacktestEngine('LIQUIDITY_SWEEP')
    data = load_test_data('btc_5m_3months.csv')
    
    param_space = {'pierce_depth': [0.001, 0.002], 'volume_spike_threshold': [2.0, 3.0]}
    best_params, best_score = optimizer.optimize(backtest_engine, data, param_space)
    
    assert best_score > 0  # Found profitable config
```

### Integration Tests (end-to-end)
```python
def test_full_training_pipeline():
    # 1. Collect data
    collector = DataCollector(['binance'])
    data = collector.fetch_ohlcv('binance', 'BTC/USDT', '5m', since='2024-01-01', until='2024-12-31')
    
    # 2. Optimize
    optimizer = RandomSearchOptimizer(n_samples=10)  # Small sample for test
    backtest_engine = BacktestEngine('LIQUIDITY_SWEEP')
    best_params, _ = optimizer.optimize(backtest_engine, data, LIQUIDITY_SWEEP_PARAM_SPACE)
    
    # 3. Validate
    validator = WalkForwardValidator(train_period=90, test_period=30, gap_period=7)
    validation_result = validator.validate(data, best_params, backtest_engine)
    
    # 4. Store
    writer = ConfigurationWriter()
    config_id = writer.write_configuration(
        strategy='LIQUIDITY_SWEEP_V3',
        pair='BTC/USDT',
        exchange='binance',
        timeframe='5m',
        parameters=best_params,
        metrics=validation_result.metrics
    )
    
    # 5. Verify
    assert config_id is not None
    config = db.get_configuration(config_id)
    assert config['lifecycle_stage'] in ['DISCOVERY', 'VALIDATION', 'MATURE']
```

---

## 📈 Success Criteria

**Phase 1 is complete when**:

1. ✅ Can run training for BTC/USDT on Binance 5m in < 5 minutes
2. ✅ Generated configuration stored in database with all required fields
3. ✅ Lifecycle stage assigned correctly based on metrics
4. ✅ Can re-run with different optimization methods (grid, random, bayesian)
5. ✅ At least 1 MATURE configuration discovered (sample_size > 100, sharpe > 1.5)
6. ✅ UI shows training progress and results
7. ✅ Full documentation of the training process

---

## 🚨 Known Challenges

### Challenge 1: Parameter Space Explosion
**Problem**: 201,600 combinations for full grid search  
**Solution**: Use Random Search (1000 samples) or Bayesian (200 iters) for speed

### Challenge 2: Overfitting
**Problem**: Parameters optimized on training data may not work on test data  
**Solution**: Walk-forward validation + out-of-sample testing + statistical significance checks

### Challenge 3: Data Quality
**Problem**: ccxt sometimes has gaps or errors in historical data  
**Solution**: Data validation, gap detection, forward-fill with caution

### Challenge 4: Computational Resources
**Problem**: Training 24 markets sequentially takes 67 hours with grid search  
**Solution**: Start with Random Search, add parallelization in Phase 2

### Challenge 5: False Discoveries
**Problem**: Finding "profitable" configs that are just luck  
**Solution**: Statistical significance testing (p-value < 0.05), large sample sizes (>100 trades)

---

## 🎓 Learning Resources

### Backtesting Best Practices
- *Evidence-Based Technical Analysis* by David Aronson
- *Advances in Financial Machine Learning* by Marcos López de Prado
- Walk-forward analysis methodology

### Optimization Methods
- Grid Search: Exhaustive but guaranteed to find best in grid
- Random Search: "Random Search for Hyper-Parameter Optimization" (Bergstra & Bengio, 2012)
- Bayesian: "Practical Bayesian Optimization" (Snoek et al., 2012)

### Statistical Validation
- Multiple testing correction (Bonferroni, FDR)
- Monte Carlo simulation for confidence intervals
- Sharpe ratio significance testing

---

## 🎯 Next Actions

1. **Review this document** ✅ (you're reading it!)
2. **Review [TRAINING_IMPLEMENTATION_PLAN.md](./TRAINING_IMPLEMENTATION_PLAN.md)** - detailed architecture
3. **Review [training_specs/LIQUIDITY_SWEEP_V3.md](./training_specs/LIQUIDITY_SWEEP_V3.md)** - strategy specification
4. **Set up development environment** - install dependencies, create directories
5. **Start Sprint 1** - begin with DataCollector implementation

---

## 💬 Questions Before Starting?

Common questions:

**Q: Why start with LIQUIDITY SWEEP?**  
A: Simplest data requirements (just OHLCV), clear entry/exit logic, good for proving the pipeline works.

**Q: Will Random Search really be as good as Grid Search?**  
A: Empirically, yes! Studies show random search covers the space well and often finds better solutions faster.

**Q: What if we don't find any MATURE configurations?**  
A: That's okay! DISCOVERY and VALIDATION are still valuable. We can paper trade them and watch them mature over time.

**Q: Can we train multiple strategies in parallel?**  
A: Phase 1 is sequential (simpler), but Phase 2+ can add parallelization across markets and strategies.

**Q: How do we know if a configuration is actually good or just lucky?**  
A: Statistical significance testing (p-value), large sample size, out-of-sample validation, and time (MATURE requires sustained performance).

---

**Ready to begin?** Let's start with Sprint 1, Day 1: Data Collection! 🚀
