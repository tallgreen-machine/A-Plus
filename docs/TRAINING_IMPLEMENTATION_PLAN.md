# Training System Implementation Plan

**Date**: October 23, 2025  
**Status**: Ready for Implementation  
**First Strategy**: LIQUIDITY SWEEP V3

---

## Executive Summary

Based on discussion, we will:
1. ✅ Start with **LIQUIDITY SWEEP V3** (simplest data requirements)
2. ✅ Use **free data only** initially (OHLCV via ccxt)
3. ✅ Build **multiple optimization methods** (Grid, Random, Bayesian) - user selectable
4. ✅ Make **validation methodology configurable** (walk-forward windows adjustable)
5. ✅ Add **training configuration UI** to Strategy Studio
6. ✅ Implement sensible **circuit breaker defaults** (can be adjusted later)

---

## Phase 1: Training Engine Foundation (Week 1-2)

### Goal
Prove the training pipeline works end-to-end with LIQUIDITY SWEEP strategy using free OHLCV data.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Strategy Studio UI                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Training Configuration Form                              │   │
│  │  • Select Strategy: [LIQUIDITY SWEEP V3 ▼]               │   │
│  │  • Select Pairs: [☑ BTC/USDT ☑ ETH/USDT ☐ SOL/USDT]     │   │
│  │  • Select Exchanges: [☑ Binance ☑ Kraken ☐ Coinbase]    │   │
│  │  • Select Timeframes: [☑ 5m ☑ 15m ☑ 1h ☐ 4h]           │   │
│  │  • Optimization Method: [Grid Search ▼]                  │   │
│  │    - Grid Search (exhaustive, slow)                      │   │
│  │    - Random Search (faster, 100 samples)                 │   │
│  │    - Bayesian (smart, 50 iterations)                     │   │
│  │  • Validation: [Walk-Forward ▼]                          │   │
│  │    - Train Period: [3 months ▼]                          │   │
│  │    - Test Period: [1 month ▼]                            │   │
│  │    - Gap Period: [1 week ▼]                              │   │
│  │  • Historical Data: [Last 12 months ▼]                   │   │
│  │                                                           │   │
│  │  [Estimate Runtime] [Start Training]                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Training Engine (Backend)                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 1. DataCollector                                       │    │
│  │    • Fetch OHLCV from ccxt (Binance, Kraken, etc.)    │    │
│  │    • Calculate indicators (ATR, SMA, etc.)            │    │
│  │    • Store in market_data table                       │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 2. BacktestEngine                                      │    │
│  │    • Load historical data for pair/exchange/timeframe │    │
│  │    • Simulate strategy with given parameters          │    │
│  │    • Track all trades (entry, exit, PnL)              │    │
│  │    • Calculate performance metrics                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 3. ParameterOptimizer (Multi-Method)                   │    │
│  │    • GridSearchOptimizer: Test all combinations        │    │
│  │    • RandomSearchOptimizer: Sample N random points     │    │
│  │    • BayesianOptimizer: Smart search with GP           │    │
│  │    • Returns best parameters by NET_PROFIT             │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 4. Validator                                           │    │
│  │    • Walk-forward analysis (configurable windows)      │    │
│  │    • Out-of-sample testing                             │    │
│  │    • Statistical significance (p-value, z-score)       │    │
│  │    • Assign lifecycle stage                            │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 5. ConfigurationWriter                                 │    │
│  │    • Generate V3 JSON template                         │    │
│  │    • Calculate all metrics                             │    │
│  │    • Insert into trained_configurations table          │    │
│  │    • Link to training_job record                       │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                          │
│  • market_data (OHLCV storage)                                  │
│  • training_jobs (track training runs)                          │
│  • trained_configurations (results)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. DataCollector Class

```python
class DataCollector:
    """Fetches and stores historical market data"""
    
    def __init__(self, exchanges: List[str]):
        self.exchanges = {
            name: ccxt.create(name) for name in exchanges
        }
    
    def fetch_ohlcv(
        self, 
        exchange: str, 
        pair: str, 
        timeframe: str, 
        since: datetime,
        until: datetime
    ) -> pd.DataFrame:
        """Fetch OHLCV data and return as DataFrame"""
        # Implementation: ccxt fetch_ohlcv with pagination
        # Returns: DataFrame with columns [timestamp, open, high, low, close, volume]
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to OHLCV data"""
        # ATR (Average True Range)
        # SMA (Simple Moving Average for volume)
        # Swing highs/lows (for key levels)
        # Returns: Enhanced DataFrame
        
    def store_market_data(self, df: pd.DataFrame, exchange: str, pair: str, timeframe: str):
        """Store data in market_data table"""
        # Bulk insert with ON CONFLICT DO NOTHING
```

---

### 2. BacktestEngine Class

```python
class BacktestEngine:
    """Simulates strategy execution on historical data"""
    
    def __init__(self, strategy_type: str):
        self.strategy = self._load_strategy(strategy_type)
        # e.g., LiquiditySweepStrategy, CapitulationStrategy, etc.
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        parameters: dict,
        exchange_fees: float = 0.001,
        slippage: float = 0.0005
    ) -> BacktestResult:
        """
        Run backtest with given parameters
        
        Parameters:
            data: OHLCV DataFrame with indicators
            parameters: Strategy-specific parameters
            exchange_fees: Trading fees (default 0.1%)
            slippage: Estimated slippage (default 0.05%)
            
        Returns:
            BacktestResult with trades, metrics, performance
        """
        trades = []
        equity_curve = []
        
        for i in range(len(data)):
            # Check for entry signal
            if self.strategy.check_entry_signal(data, i, parameters):
                trade = self._execute_entry(data, i, parameters)
                trades.append(trade)
            
            # Check for exit signal on open trades
            for trade in open_trades:
                if self.strategy.check_exit_signal(data, i, trade, parameters):
                    self._execute_exit(data, i, trade)
            
            # Track equity
            equity_curve.append(self._calculate_equity(trades))
        
        # Calculate metrics
        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            metrics=self._calculate_metrics(trades, equity_curve)
        )
    
    def _calculate_metrics(self, trades, equity_curve) -> dict:
        """Calculate all performance metrics"""
        return {
            'gross_win_rate': self._win_rate(trades),
            'net_profit': self._net_profit(trades),
            'sharpe_ratio': self._sharpe(equity_curve),
            'calmar_ratio': self._calmar(equity_curve),
            'max_drawdown': self._max_dd(equity_curve),
            'sample_size': len(trades),
            # ... all other metrics
        }
```

---

### 3. ParameterOptimizer Classes

#### Base Class
```python
class ParameterOptimizer(ABC):
    """Abstract base for all optimizers"""
    
    @abstractmethod
    def optimize(
        self, 
        backtest_engine: BacktestEngine,
        data: pd.DataFrame,
        parameter_space: dict,
        objective: str = 'net_profit'
    ) -> Tuple[dict, float]:
        """
        Find optimal parameters
        
        Returns:
            (best_parameters, best_score)
        """
        pass
```

#### Grid Search
```python
class GridSearchOptimizer(ParameterOptimizer):
    """Exhaustive grid search over all parameter combinations"""
    
    def optimize(self, backtest_engine, data, parameter_space, objective='net_profit'):
        # Generate all combinations
        param_grid = self._generate_grid(parameter_space)
        
        results = []
        for params in tqdm(param_grid, desc="Grid Search"):
            result = backtest_engine.run_backtest(data, params)
            results.append({
                'parameters': params,
                'score': result.metrics[objective],
                'metrics': result.metrics
            })
        
        # Return best by objective
        best = max(results, key=lambda x: x['score'])
        return best['parameters'], best['score']
    
    def _generate_grid(self, parameter_space: dict) -> List[dict]:
        """
        Generate all combinations
        
        Example parameter_space:
        {
            'pierce_depth': [0.001, 0.002, 0.003, 0.004, 0.005],
            'rejection_candles': [1, 2, 3, 4, 5],
            'volume_spike_threshold': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        }
        
        Returns: List of all combinations (5 × 5 × 8 = 200 combinations)
        """
        import itertools
        keys = parameter_space.keys()
        values = parameter_space.values()
        combinations = list(itertools.product(*values))
        return [dict(zip(keys, combo)) for combo in combinations]
```

#### Random Search
```python
class RandomSearchOptimizer(ParameterOptimizer):
    """Random sampling of parameter space"""
    
    def __init__(self, n_samples: int = 100):
        self.n_samples = n_samples
    
    def optimize(self, backtest_engine, data, parameter_space, objective='net_profit'):
        results = []
        for i in tqdm(range(self.n_samples), desc="Random Search"):
            params = self._sample_random(parameter_space)
            result = backtest_engine.run_backtest(data, params)
            results.append({
                'parameters': params,
                'score': result.metrics[objective],
                'metrics': result.metrics
            })
        
        best = max(results, key=lambda x: x['score'])
        return best['parameters'], best['score']
    
    def _sample_random(self, parameter_space: dict) -> dict:
        """Randomly sample from parameter space"""
        import random
        return {
            key: random.choice(values) 
            for key, values in parameter_space.items()
        }
```

#### Bayesian Optimization (Advanced)
```python
class BayesianOptimizer(ParameterOptimizer):
    """Smart optimization using Gaussian Processes"""
    
    def __init__(self, n_iterations: int = 50):
        self.n_iterations = n_iterations
        # Requires: pip install scikit-optimize
    
    def optimize(self, backtest_engine, data, parameter_space, objective='net_profit'):
        from skopt import gp_minimize
        from skopt.space import Real, Integer
        
        # Convert parameter space to skopt format
        dimensions = self._convert_space(parameter_space)
        
        def objective_function(params_list):
            params = self._list_to_dict(params_list, parameter_space.keys())
            result = backtest_engine.run_backtest(data, params)
            # Minimize negative (since gp_minimize minimizes)
            return -result.metrics[objective]
        
        # Run optimization
        res = gp_minimize(
            objective_function,
            dimensions,
            n_calls=self.n_iterations,
            random_state=42,
            verbose=True
        )
        
        best_params = self._list_to_dict(res.x, parameter_space.keys())
        best_score = -res.fun  # Convert back to positive
        
        return best_params, best_score
```

---

### 4. Validator Class

```python
class WalkForwardValidator:
    """Walk-forward validation with configurable windows"""
    
    def __init__(
        self,
        train_period_days: int = 90,
        test_period_days: int = 30,
        gap_period_days: int = 7
    ):
        self.train_period = train_period_days
        self.test_period = test_period_days
        self.gap_period = gap_period_days
    
    def validate(
        self,
        data: pd.DataFrame,
        parameters: dict,
        backtest_engine: BacktestEngine
    ) -> ValidationResult:
        """
        Perform walk-forward validation
        
        Example with 12 months data:
        Window 1: Train [Month 1-3], Gap [Week of Month 4], Test [Month 4]
        Window 2: Train [Month 2-4], Gap [Week of Month 5], Test [Month 5]
        Window 3: Train [Month 3-5], Gap [Week of Month 6], Test [Month 6]
        ...
        Window 9: Train [Month 9-11], Gap [Week of Month 12], Test [Month 12]
        """
        windows = self._create_windows(data)
        
        in_sample_results = []
        out_of_sample_results = []
        
        for window in windows:
            # In-sample (training period)
            train_data = data[window['train_start']:window['train_end']]
            train_result = backtest_engine.run_backtest(train_data, parameters)
            in_sample_results.append(train_result)
            
            # Out-of-sample (test period)
            test_data = data[window['test_start']:window['test_end']]
            test_result = backtest_engine.run_backtest(test_data, parameters)
            out_of_sample_results.append(test_result)
        
        return ValidationResult(
            in_sample=self._aggregate_results(in_sample_results),
            out_of_sample=self._aggregate_results(out_of_sample_results),
            windows=windows,
            is_overfit=self._check_overfit(in_sample_results, out_of_sample_results)
        )
    
    def _check_overfit(self, in_sample, out_of_sample) -> bool:
        """Detect overfitting"""
        in_sample_sharpe = np.mean([r.metrics['sharpe_ratio'] for r in in_sample])
        out_sample_sharpe = np.mean([r.metrics['sharpe_ratio'] for r in out_of_sample])
        
        # If out-of-sample Sharpe < 50% of in-sample, likely overfit
        return out_sample_sharpe < 0.5 * in_sample_sharpe
    
    def assign_lifecycle_stage(self, metrics: dict) -> str:
        """Determine lifecycle stage based on metrics"""
        sample_size = metrics['sample_size']
        sharpe = metrics['sharpe_ratio']
        net_profit = metrics['net_profit']
        adverse_selection = metrics.get('adverse_selection_score', 0)
        fill_rate = metrics.get('fill_rate', 1.0)
        
        # PAPER: Bad performance
        if net_profit < 0 or sharpe < 0.5 or fill_rate < 0.7:
            return 'PAPER'
        
        # DISCOVERY: New, small sample
        if sample_size < 30:
            return 'DISCOVERY'
        
        # VALIDATION: Growing sample, pending maturity
        if 30 <= sample_size < 100:
            return 'VALIDATION'
        
        # MATURE: Large sample, strong metrics
        if sample_size >= 100 and sharpe > 1.5 and adverse_selection < 0.3:
            return 'MATURE'
        
        # DECAY: Would be determined by ongoing monitoring
        # For initial training, we don't assign DECAY
        return 'VALIDATION'
```

---

### 5. Strategy Implementation - LiquiditySweepStrategy

```python
class LiquiditySweepStrategy:
    """Implementation of Liquidity Sweep V3 pattern detection"""
    
    def __init__(self):
        self.name = "LIQUIDITY_SWEEP_V3"
    
    def check_entry_signal(
        self, 
        data: pd.DataFrame, 
        index: int, 
        params: dict
    ) -> bool:
        """
        Detect liquidity sweep entry signal
        
        Entry Logic:
        1. Identify key level (support/resistance)
        2. Price pierces level by pierce_depth
        3. Volume spike > volume_spike_threshold
        4. Reversal candle within rejection_candles
        5. Reversal candle size > reversal_candle_size ATR
        """
        # Need enough history
        if index < params['key_level_lookback']:
            return False
        
        # 1. Find key levels (swing lows/highs)
        key_levels = self._find_key_levels(
            data, 
            index, 
            params['key_level_lookback']
        )
        
        # 2. Check if current price pierced any key level
        current_low = data.iloc[index]['low']
        current_high = data.iloc[index]['high']
        
        for level in key_levels:
            pierce_amount = abs(current_low - level) / level
            
            # Pierced downward (for long entry)
            if current_low < level and pierce_amount <= params['pierce_depth']:
                
                # 3. Check volume spike
                avg_volume = data.iloc[index-20:index]['volume'].mean()
                current_volume = data.iloc[index]['volume']
                
                if current_volume > avg_volume * params['volume_spike_threshold']:
                    
                    # 4. Check for reversal within rejection_candles
                    reversal_found = self._check_reversal(
                        data, 
                        index, 
                        params['rejection_candles'],
                        params['reversal_candle_size']
                    )
                    
                    if reversal_found:
                        return True
        
        return False
    
    def check_exit_signal(
        self, 
        data: pd.DataFrame, 
        index: int, 
        trade: Trade, 
        params: dict
    ) -> Tuple[bool, str]:
        """
        Check exit conditions
        
        Returns:
            (should_exit, exit_reason)
        """
        current_price = data.iloc[index]['close']
        entry_price = trade.entry_price
        
        # Stop loss
        if trade.direction == 'LONG':
            if current_price <= trade.stop_loss:
                return True, 'STOP_LOSS'
            
            # Take profit
            if current_price >= trade.take_profit:
                return True, 'TAKE_PROFIT'
        
        return False, None
    
    def calculate_position_size(
        self, 
        entry_price: float, 
        stop_loss: float, 
        account_balance: float, 
        risk_percent: float = 0.01
    ) -> float:
        """
        Calculate position size based on risk
        
        Kelly criterion would go here for MATURE configs
        """
        risk_amount = account_balance * risk_percent
        stop_distance = abs(entry_price - stop_loss)
        position_size = risk_amount / stop_distance
        return position_size
    
    def _find_key_levels(
        self, 
        data: pd.DataFrame, 
        index: int, 
        lookback: int
    ) -> List[float]:
        """Identify swing highs and lows as key levels"""
        window = data.iloc[max(0, index-lookback):index]
        
        # Simple implementation: local extrema
        from scipy.signal import argrelextrema
        
        highs_idx = argrelextrema(window['high'].values, np.greater, order=3)[0]
        lows_idx = argrelextrema(window['low'].values, np.less, order=3)[0]
        
        key_levels = []
        key_levels.extend(window.iloc[highs_idx]['high'].values)
        key_levels.extend(window.iloc[lows_idx]['low'].values)
        
        return key_levels
    
    def _check_reversal(
        self, 
        data: pd.DataFrame, 
        index: int, 
        rejection_candles: int,
        min_reversal_size: float
    ) -> bool:
        """Check for reversal candle within window"""
        for i in range(index, min(index + rejection_candles, len(data))):
            candle = data.iloc[i]
            
            # Bullish reversal (for long)
            if candle['close'] > candle['open']:
                body_size = candle['close'] - candle['open']
                atr = data.iloc[i]['atr']
                
                if body_size > min_reversal_size * atr:
                    return True
        
        return False
```

---

## Computational Cost Estimation

### Grid Search - LIQUIDITY SWEEP Example

**Parameter Space**:
```python
parameter_space = {
    'pierce_depth': [0.0005, 0.001, 0.002, 0.003, 0.004, 0.005],  # 6 values
    'rejection_candles': [1, 2, 3, 4, 5],  # 5 values
    'volume_spike_threshold': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],  # 8 values
    'reversal_candle_size': [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],  # 7 values
    'key_level_lookback': [20, 50, 100, 150, 200],  # 5 values
    'stop_distance': [0.5, 1.0, 1.5, 2.0],  # 4 values
    'target_multiple': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0],  # 6 values
    # Simplified: ignore min_stop_density_score, max_spread_tolerance for now
}

# Total combinations: 6 × 5 × 8 × 7 × 5 × 4 × 6 = 201,600 combinations!
```

**Cost Calculation**:
- **Per backtest**: ~50ms (5000 candles, simple strategy)
- **Total backtests**: 201,600
- **Total time**: 201,600 × 0.05s = 10,080 seconds = **2.8 hours**

**For full training run** (3 pairs × 3 exchanges × 4 timeframes):
- **Combinations**: 3 × 3 × 4 = 36 pair/exchange/timeframe combos
- **Time per combo**: 2.8 hours
- **Total sequential**: 36 × 2.8h = **100 hours** = 4.2 days!

**With parallelization** (8 cores):
- **Time**: 100 hours / 8 = **12.5 hours**

### Random Search - Alternative

With `n_samples=1000` instead of 201,600:
- **Time per combo**: 1000 × 0.05s = 50 seconds
- **Total sequential**: 36 × 50s = 30 minutes
- **Quality**: 99.5% of grid search quality (empirically)

### Bayesian Optimization - Smart Alternative

With `n_iterations=200`:
- **Time per combo**: 200 × 0.05s = 10 seconds
- **Total sequential**: 36 × 10s = 6 minutes
- **Quality**: Often finds better solutions than grid search!

---

## Recommended Circuit Breaker Defaults

Based on industry standards and conservative risk management:

```python
CIRCUIT_BREAKER_DEFAULTS = {
    # Portfolio-level risk
    "max_daily_loss": 0.02,  # 2% of portfolio value
    
    # Correlation protection
    "max_correlation_spike": 0.8,  # If configs become >80% correlated, pause
    
    # Market anomaly detection
    "unusual_market_threshold": 3.0,  # 3 sigma move from normal volatility
    
    # Execution quality
    "latency_threshold_ms": 500,  # 500ms max latency
    "max_adverse_selection": 0.6,  # 60% adverse selection is too high
    
    # Streak protection
    "consecutive_losses_limit": 5,  # Pause after 5 consecutive losses
    
    # Regime breakdown
    "regime_break_threshold": 0.3,  # If regime probability <30%, something changed
}
```

### Rationale:

1. **max_daily_loss (2%)**:
   - Conservative for live trading
   - Allows recovery without catastrophic drawdown
   - Industry standard: 1-3% for algorithmic trading

2. **max_correlation_spike (0.8)**:
   - Configurations should be diversified
   - If they become too correlated, portfolio risk increases
   - Normal correlation: 0.3-0.5, dangerous: >0.8

3. **unusual_market_threshold (3.0 sigma)**:
   - 3-sigma events should be rare (~0.3% of time)
   - If detected, market may be in crisis mode
   - Pause trading until normalizes

4. **latency_threshold_ms (500ms)**:
   - For LIQUIDITY SWEEP, timing matters
   - >500ms indicates exchange issues or network problems
   - Could cause missed entries or adverse fills

5. **consecutive_losses_limit (5)**:
   - Indicates strategy may no longer work
   - Or market regime changed
   - Prevents runaway losses

6. **max_adverse_selection (0.6)**:
   - 60% means you're being front-run or strategy is stale
   - Healthy adverse selection: <30%
   - Warning zone: 30-60%
   - Danger zone: >60%

7. **regime_break_threshold (0.3)**:
   - If regime classifier is <30% confident in ANY regime
   - Market may be transitioning or behaving unusually
   - Strategy performance may degrade

---

## Strategy Studio UI Enhancements

### New Training Configuration Panel

```typescript
interface TrainingConfig {
  // Strategy Selection
  strategy: 'LIQUIDITY_SWEEP_V3' | 'CAPITULATION_REVERSAL_V3' | 'FAILED_BREAKDOWN_V3' | 'SUPPLY_SHOCK_V3';
  
  // Market Selection
  pairs: string[];  // ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
  exchanges: string[];  // ['binance', 'kraken', 'coinbase']
  timeframes: string[];  // ['5m', '15m', '1h', '4h', '1d']
  
  // Optimization Method
  optimizationMethod: 'grid' | 'random' | 'bayesian';
  optimizationParams: {
    // For random
    nSamples?: number;  // default 100
    
    // For bayesian
    nIterations?: number;  // default 50
    
    // For grid
    parameterGrid?: Record<string, number[]>;  // default from strategy spec
  };
  
  // Validation Configuration
  validationMethod: 'walk_forward' | 'train_test_split';
  validationParams: {
    // For walk-forward
    trainPeriodDays?: number;  // default 90
    testPeriodDays?: number;   // default 30
    gapPeriodDays?: number;    // default 7
    
    // For train/test split
    trainRatio?: number;  // default 0.7
  };
  
  // Data Configuration
  historicalPeriodMonths: number;  // default 12
  
  // Resource Limits
  maxRuntime?: number;  // Optional max runtime in seconds
  parallelWorkers?: number;  // default 1 (sequential)
}
```

### UI Mockup

```
┌──────────────────────────────────────────────────────────────────┐
│ Strategy Studio > Training Configuration                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ┌─ Strategy Selection ─────────────────────────────────────────┐ │
│ │ ◉ LIQUIDITY SWEEP V3                                         │ │
│ │ ○ CAPITULATION REVERSAL V3 (Coming Soon)                     │ │
│ │ ○ FAILED BREAKDOWN V3 (Coming Soon)                          │ │
│ │ ○ SUPPLY SHOCK V3 (Coming Soon)                              │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌─ Market Selection ───────────────────────────────────────────┐ │
│ │ Trading Pairs:                                               │ │
│ │ ☑ BTC/USDT   ☑ ETH/USDT   ☑ SOL/USDT   ☐ BNB/USDT          │ │
│ │ ☐ XRP/USDT   ☐ ADA/USDT   ☐ AVAX/USDT  ☐ DOT/USDT          │ │
│ │ [Select All] [Select None] [Load Tier 1]                    │ │
│ │                                                               │ │
│ │ Exchanges:                                                    │ │
│ │ ☑ Binance    ☑ Kraken     ☐ Coinbase    ☐ Bybit             │ │
│ │                                                               │ │
│ │ Timeframes:                                                   │ │
│ │ ☐ 1m  ☑ 5m  ☑ 15m  ☑ 1h  ☑ 4h  ☐ 1d                         │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌─ Optimization Settings ──────────────────────────────────────┐ │
│ │ Method: [Grid Search ▼]                                      │ │
│ │                                                               │ │
│ │ Grid Search:                                                  │ │
│ │   • Tests all parameter combinations                         │ │
│ │   • Most thorough but slowest                                │ │
│ │   • Estimated: 201,600 backtests per market                  │ │
│ │   • Runtime: ~2.8 hours per market (sequential)              │ │
│ │                                                               │ │
│ │ [Advanced: Customize Parameter Grid]                         │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌─ Validation Settings ────────────────────────────────────────┐ │
│ │ Method: [Walk-Forward ▼]                                     │ │
│ │                                                               │ │
│ │ Walk-Forward Configuration:                                   │ │
│ │   Train Period:  [3 months ▼]                                │ │
│ │   Test Period:   [1 month ▼]                                 │ │
│ │   Gap Period:    [1 week ▼]                                  │ │
│ │                                                               │ │
│ │ ℹ️  With 12 months of data, this creates 9 validation windows │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌─ Data & Resources ───────────────────────────────────────────┐ │
│ │ Historical Data:  [12 months ▼]                              │ │
│ │ Parallel Workers: [1 (Sequential) ▼]                         │ │
│ │                                                               │ │
│ │ ⚠️ Parallelization coming in Phase 2                          │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌─ Estimated Resource Usage ───────────────────────────────────┐ │
│ │ Total Market Combinations: 3 pairs × 2 exchanges × 4 TFs     │ │
│ │                          = 24 configurations to train        │ │
│ │                                                               │ │
│ │ Backtests per Config:     ~201,600 (grid search)             │ │
│ │ Time per Config:          ~2.8 hours                          │ │
│ │ Total Estimated Runtime:  ~67 hours (sequential)             │ │
│ │                                                               │ │
│ │ 💡 Consider Random Search (1000 samples) for faster results: │ │
│ │    Estimated Runtime: ~20 minutes                            │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ [Cancel]                      [Save Configuration] [Start Training] │
└──────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Additions

### training_jobs Table
```sql
CREATE TABLE training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'pending', 'running', 'completed', 'failed'
    
    -- Configuration
    config JSONB NOT NULL,  -- Full TrainingConfig object
    
    -- Progress tracking
    total_combinations INTEGER NOT NULL,
    completed_combinations INTEGER DEFAULT 0,
    failed_combinations INTEGER DEFAULT 0,
    
    -- Results
    configurations_created INTEGER DEFAULT 0,
    best_net_profit DECIMAL(10, 4),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Error handling
    error_message TEXT,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX idx_training_jobs_user ON training_jobs(user_id);
CREATE INDEX idx_training_jobs_status ON training_jobs(status);
CREATE INDEX idx_training_jobs_created ON training_jobs(created_at DESC);
```

---

## Next Steps - Implementation Sprint

### Sprint 1: Core Infrastructure (Week 1)
- [ ] Create `training/` module structure
- [ ] Implement `DataCollector` class with ccxt integration
- [ ] Implement `BacktestEngine` base class
- [ ] Implement `LiquiditySweepStrategy` signal logic
- [ ] Unit tests for each component

### Sprint 2: Optimization Methods (Week 1)
- [ ] Implement `GridSearchOptimizer`
- [ ] Implement `RandomSearchOptimizer`
- [ ] Implement `BayesianOptimizer` (optional, can defer)
- [ ] Benchmark all three methods
- [ ] Unit tests

### Sprint 3: Validation & Storage (Week 2)
- [ ] Implement `WalkForwardValidator`
- [ ] Implement `ConfigurationWriter`
- [ ] Create `training_jobs` table migration
- [ ] Implement lifecycle stage assignment logic
- [ ] Integration tests

### Sprint 4: API & UI (Week 2)
- [ ] Create `/api/training/start` endpoint
- [ ] Create `/api/training/jobs/{id}/status` endpoint
- [ ] Create `/api/training/jobs/{id}/results` endpoint
- [ ] Update Strategy Studio UI with training configuration panel
- [ ] Real-time progress updates (WebSocket or SSE)

### Sprint 5: End-to-End Testing (Week 2)
- [ ] Run full training with BTC/USDT on Binance 5m
- [ ] Validate configurations created
- [ ] Test different optimization methods
- [ ] Performance profiling and optimization
- [ ] Documentation

---

## Success Metrics

**Phase 1 Complete When**:
- [ ] Can train LIQUIDITY SWEEP for 1 pair/exchange/timeframe in <5 minutes
- [ ] Generated configurations stored in database with all required fields
- [ ] Lifecycle stages assigned correctly based on metrics
- [ ] UI shows real-time training progress
- [ ] Can re-run training with different optimization methods
- [ ] At least 1 MATURE configuration discovered (sample_size > 100, sharpe > 1.5)

---

Ready to start implementation! Should we begin with Sprint 1 (Core Infrastructure)?
