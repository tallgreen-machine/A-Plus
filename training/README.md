# V2 Training System

**Purpose**: Find optimal parameters for trading strategies using ML-powered optimization algorithms.

**Architecture**: Rule-based parameter search (NO neural networks, fully transparent).

---

## Components

### Core Modules

```
training/
├── data_collector.py          # Database-first OHLCV fetching
├── backtest_engine.py          # Trade simulation & metrics
├── validator.py                # Walk-forward validation
├── configuration_writer.py     # V3 JSON generation & DB insertion
├── optimizers/
│   ├── grid_search.py         # Exhaustive parameter search
│   ├── random_search.py       # Monte Carlo sampling
│   └── bayesian.py            # ML-powered Gaussian Process optimization
└── strategies/
    ├── liquidity_sweep.py     # Key level pierce detection
    ├── capitulation_reversal.py   # (Future)
    ├── failed_breakdown.py        # (Future)
    └── supply_shock.py            # (Future)
```

---

## Quick Start

### 1. Train a Strategy

```python
from training.data_collector import DataCollector
from training.backtest_engine import BacktestEngine
from training.strategies.liquidity_sweep import LiquiditySweepStrategy
from training.optimizers.bayesian import BayesianOptimizer
from training.validator import WalkForwardValidator
from training.configuration_writer import ConfigurationWriter

# Step 1: Collect data (database-first)
collector = DataCollector()
data = collector.fetch_ohlcv(
    symbol='BTC/USDT',
    exchange='binance',
    timeframe='5m',
    lookback_days=90
)

# Step 2: Define parameter space
param_space = {
    'pierce_depth': (0.001, 0.005),           # 0.1% to 0.5%
    'volume_spike_threshold': (1.5, 5.0),     # 1.5x to 5x
    'reversal_candles': [1, 2, 3, 4, 5],      # Discrete
    'min_distance_from_level': (0.0005, 0.003),
    'atr_multiplier_sl': (1.0, 3.0),
    'risk_reward_ratio': (1.5, 4.0),
    'max_holding_periods': [10, 20, 30, 50, 100]
}

# Step 3: Run optimization (Bayesian = ML-powered)
optimizer = BayesianOptimizer()
engine = BacktestEngine()

best_config = optimizer.optimize(
    backtest_engine=engine,
    data=data,
    strategy_class=LiquiditySweepStrategy,
    parameter_space=param_space,
    objective='sharpe_ratio',
    n_calls=200  # Only 200 evaluations (ML finds optimal region)
)

# Step 4: Validate (walk-forward)
validator = WalkForwardValidator(
    train_window_days=60,
    test_window_days=30,
    gap_days=7
)

validated_config = validator.validate(
    config=best_config,
    data=data,
    strategy_class=LiquiditySweepStrategy
)

# Step 5: Save to database
writer = ConfigurationWriter()
config_id = writer.save_configuration(
    strategy='LIQUIDITY_SWEEP',
    parameters=validated_config['parameters'],
    metrics=validated_config['metrics'],
    lifecycle_stage='DISCOVERY'  # Based on metrics
)

print(f"✅ Configuration {config_id} saved with Sharpe {validated_config['metrics']['sharpe_ratio']:.2f}")
```

---

## Optimization Methods

### Grid Search (Exhaustive)
```python
from training.optimizers.grid_search import GridSearchOptimizer

optimizer = GridSearchOptimizer()
result = optimizer.optimize(
    backtest_engine=engine,
    data=data,
    strategy_class=LiquiditySweepStrategy,
    parameter_space=param_space
)
# Tries EVERY combination (slow but thorough)
```

### Random Search (Fast Exploration)
```python
from training.optimizers.random_search import RandomSearchOptimizer

optimizer = RandomSearchOptimizer()
result = optimizer.optimize(
    backtest_engine=engine,
    data=data,
    strategy_class=LiquiditySweepStrategy,
    parameter_space=param_space,
    n_iterations=500  # Random samples
)
# Fast, often finds good solutions
```

### Bayesian Optimization (ML-Powered) ⭐
```python
from training.optimizers.bayesian import BayesianOptimizer

optimizer = BayesianOptimizer()
result = optimizer.optimize(
    backtest_engine=engine,
    data=data,
    strategy_class=LiquiditySweepStrategy,
    parameter_space=param_space,
    n_calls=200  # Gaussian Process learns optimal regions
)
# RECOMMENDED: Intelligent search using ML model
```

---

## Data Collection Strategy

### Database-First (360x Faster)
```python
collector = DataCollector()

# Priority 1: Try database (instant)
df = collector.fetch_ohlcv(
    symbol='BTC/USDT',
    exchange='binance',
    timeframe='5m',
    lookback_days=90
)
# Uses existing market_data table (20,437 records)

# Priority 2: API fallback (if missing)
# Automatically fetches from exchange and caches to database
```

**Performance**:
- Database: 50ms per symbol
- API: 10-30 seconds per symbol
- Result: **360x faster** training

---

## Walk-Forward Validation

Prevents overfitting by testing on unseen future data:

```python
validator = WalkForwardValidator(
    train_window_days=60,   # Train on 60 days
    test_window_days=30,    # Test on next 30 days
    gap_days=7              # 7-day gap (no lookahead)
)

result = validator.validate(config, data, strategy_class)

# Splits data:
# [Train: Day 1-60] [Gap: Day 61-67] [Test: Day 68-97]
# [Train: Day 31-90] [Gap: Day 91-97] [Test: Day 98-127]
# ... continues sliding windows

# Metrics averaged across all test periods
```

**Overfitting Detection**:
- If `test_sharpe < 0.7 × train_sharpe` → Flag as overfit
- If `test_win_rate < 0.8 × train_win_rate` → Flag as overfit

---

## Output: V3 Configuration Format

```json
{
  "configId": "LIQUIDITY_SWEEP_V3_20251023_145632_a1b2c3",
  "version": "3.0.0",
  "strategy": "LIQUIDITY_SWEEP",
  "createdAt": "2025-10-23T14:56:32Z",
  
  "parameters": {
    "pierce_depth": 0.0023,
    "volume_spike_threshold": 3.2,
    "reversal_candles": 3,
    "min_distance_from_level": 0.0012,
    "atr_multiplier_sl": 2.1,
    "risk_reward_ratio": 2.5,
    "max_holding_periods": 30
  },
  
  "metrics": {
    "net_profit_pct": 15.3,
    "gross_win_rate": 0.58,
    "profit_factor": 1.82,
    "sharpe_ratio": 2.1,
    "max_drawdown_pct": -8.2,
    "total_trades": 127,
    "avg_win_pct": 1.8,
    "avg_loss_pct": -1.2
  },
  
  "validation": {
    "method": "walk_forward",
    "train_window_days": 60,
    "test_window_days": 30,
    "gap_days": 7,
    "test_sharpe_ratio": 1.9,
    "overfitting_detected": false
  },
  
  "lifecycle": {
    "current_stage": "DISCOVERY",
    "max_allocation_pct": 2.0,
    "confidence_score": 0.72
  },
  
  "circuit_breakers": {
    "max_daily_loss_pct": 2.0,
    "max_position_size_pct": 5.0,
    "max_drawdown_pct": 10.0,
    "max_consecutive_losses": 5,
    "daily_trade_limit": 10,
    "cooldown_after_loss_minutes": 30,
    "min_sharpe_ratio": 1.0
  }
}
```

Stored in `trained_configurations` table.

---

## Performance Targets

### Phase 1: Single Strategy Training
- **Task**: Train LIQUIDITY_SWEEP for BTC/USDT 5m (90 days)
- **Method**: Bayesian Optimization (200 evaluations)
- **Time**: < 5 minutes
- **Output**: 1 DISCOVERY configuration

### Phase 2: Multi-Asset Training
- **Task**: Train LIQUIDITY_SWEEP for 10 symbols (90 days each)
- **Method**: Bayesian Optimization (200 evaluations × 10)
- **Time**: < 30 minutes (parallel processing)
- **Output**: 10 configurations (best per symbol)

### Phase 3: Multi-Strategy Training
- **Task**: Train all 4 strategies for 10 symbols
- **Method**: Bayesian Optimization
- **Time**: < 2 hours (parallelized)
- **Output**: 40 configurations

---

## References

**Documentation**:
- [Training Implementation Plan](../docs/TRAINING_IMPLEMENTATION_PLAN.md) - Complete architecture
- [Training Quick Start](../docs/TRAINING_QUICK_START.md) - Sprint guide
- [LIQUIDITY_SWEEP Spec](../docs/training_specs/LIQUIDITY_SWEEP_V3.md) - Strategy details
- [ML for Parameter Optimization](../docs/ML_FOR_PARAMETER_OPTIMIZATION.md) - Why Bayesian > RL
- [Training Data Strategy](../docs/TRAINING_DATA_STRATEGY.md) - Database-first approach
- [Circuit Breaker Guide](../docs/CIRCUIT_BREAKER_GUIDE.md) - Risk management defaults

**Database Schema**:
- `trained_configurations` table - Configuration storage (70 columns)
- `market_data` table - OHLCV data (20,437 records)
- `training_jobs` table - Job tracking (to be created)

---

## Next Steps

1. ✅ Directory structure created
2. ⏳ Implement DataCollector (database-first)
3. ⏳ Implement BacktestEngine
4. ⏳ Implement LiquiditySweepStrategy
5. ⏳ Implement BayesianOptimizer
6. ⏳ Implement WalkForwardValidator
7. ⏳ Implement ConfigurationWriter
8. ⏳ Create training API endpoints
9. ⏳ Test end-to-end pipeline

**Let's build!** 🚀
