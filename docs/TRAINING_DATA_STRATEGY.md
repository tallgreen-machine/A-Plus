# Training Data Strategy & RL Integration Plan

**Date**: 2025-10-23  
**Purpose**: Clarify data sourcing for training and RL system integration with V2 UI

---

## Issue #1: Training Data Source

### Current Situation
✅ **20,437 records** already stored in `market_data` table
- **10 symbols** across **4 exchanges**
- Timestamp range: 1736174400000 to 1761066900000 (Unix timestamps)
- Collected via `data/real_exchange_data_collector.py`

### ❌ Problem with Original Plan
The `TRAINING_IMPLEMENTATION_PLAN.md` suggested:

```python
class DataCollector:
    def fetch_ohlcv(self, symbol, exchange, timeframe, lookback_days=90):
        # Fetches from exchange during training
        exchange_client = ccxt.binanceus()
        ohlcv = exchange_client.fetch_ohlcv(...)  # ❌ SLOW, rate-limited
```

**Issues**:
1. **Slow**: API rate limits (10-20 requests/min)
2. **Redundant**: We already have data in database
3. **Costly**: Uses API quota unnecessarily
4. **Unreliable**: Network failures during training

---

## ✅ Revised Data Strategy: Database-First

### Architecture Change

```python
class DataCollector:
    """
    REVISED: Fetch from database first, fall back to API only if missing
    """
    
    def __init__(self):
        self.db_conn = get_db_conn()
        self.exchanges = self._init_ccxt_exchanges()  # Fallback only
    
    def fetch_ohlcv(self, symbol, exchange, timeframe, lookback_days=90):
        """
        1. Try database first (fast)
        2. If missing, fetch from API and cache
        3. Calculate indicators (ATR, SMA) on retrieved data
        """
        
        # PRIMARY: Database fetch
        ohlcv_df = self._fetch_from_database(symbol, exchange, timeframe, lookback_days)
        
        if ohlcv_df.empty:
            # FALLBACK: API fetch + cache
            ohlcv_df = self._fetch_from_api_and_cache(symbol, exchange, timeframe, lookback_days)
        
        # Add indicators
        ohlcv_df = self._calculate_indicators(ohlcv_df)
        
        return ohlcv_df
    
    def _fetch_from_database(self, symbol, exchange, timeframe, lookback_days):
        """Query existing market_data table"""
        end_ts = int(time.time())
        start_ts = end_ts - (lookback_days * 86400)
        
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = %s 
              AND exchange = %s
              AND timestamp >= %s 
              AND timestamp <= %s
            ORDER BY timestamp ASC
        """
        
        with self.db_conn.cursor() as cur:
            cur.execute(query, (symbol, exchange, start_ts, end_ts))
            rows = cur.fetchall()
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    
    def _fetch_from_api_and_cache(self, symbol, exchange, timeframe, lookback_days):
        """Fallback: Fetch from API and store in database"""
        exchange_client = self.exchanges[exchange]
        
        since = int((time.time() - lookback_days * 86400) * 1000)
        ohlcv = exchange_client.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        
        # Cache to database
        self._insert_ohlcv_batch(symbol, exchange, ohlcv)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = df['timestamp'] // 1000  # ms -> seconds
        
        return df
    
    def _insert_ohlcv_batch(self, symbol, exchange, ohlcv_data):
        """Insert fetched data into market_data table for future use"""
        with self.db_conn.cursor() as cur:
            for candle in ohlcv_data:
                timestamp, open_p, high, low, close, volume = candle
                timestamp_s = timestamp // 1000
                
                cur.execute("""
                    INSERT INTO market_data (exchange, symbol, timestamp, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (exchange, symbol, timestamp) DO NOTHING
                """, (exchange, symbol, timestamp_s, open_p, high, low, close, volume))
        
        self.db_conn.commit()
```

### Performance Comparison

| Method | Speed | Data Freshness | Rate Limits |
|--------|-------|----------------|-------------|
| **Database-first** (Revised) | 🚀 <50ms | ✅ Recent cache | ✅ None |
| **API-first** (Original) | 🐌 5-10 seconds | ✅ Real-time | ❌ 10-20 req/min |

### Training Pipeline Impact

**Before** (Original Plan):
```
Start Training → Fetch 90 days BTC/USDT from API (10s) 
              → Fetch 90 days ETH/USDT from API (10s)
              → ... (30 minutes for 3 pairs × 2 exchanges × 4 timeframes)
              → Run backtest
```

**After** (Revised):
```
Start Training → Query DB for BTC/USDT (50ms)
              → Query DB for ETH/USDT (50ms)
              → ... (5 seconds for all combinations)
              → Run backtest
```

**Speedup**: ~360x faster data loading

---

## Issue #2: RL System Integration with V2 UI

### Current State Analysis

**V2 UI Assumes**:
- Trained configurations stored in `trained_configurations` table
- Lifecycle stages: MATURE, VALIDATION, DISCOVERY, DECAY, PAPER
- Performance metrics: net_profit, gross_win_rate, sharpe_ratio
- Strategy-specific parameters in JSON

**RL System Produces**:
- PPO model files (`.pkl`) with neural network weights
- Training results in `pattern_training_results` table
- Portfolio allocation decisions (not entry/exit signals)

### The Mismatch

```
┌─────────────────────────────────────────────────┐
│         V2 Strategy Studio UI                   │
│  Expects: Strategy configs with parameters      │
│  Display: Net profit %, Win rate, Sharpe       │
│  Actions: Activate/deactivate, Edit params     │
└─────────────────────────────────────────────────┘
                     ↓ ❌ Incompatible
┌─────────────────────────────────────────────────┐
│         Existing RL System Output               │
│  Produces: PPO model.pkl files                  │
│  Stores: pattern_training_results table         │
│  Purpose: Portfolio weight decisions            │
└─────────────────────────────────────────────────┘
```

---

## ✅ Solution: Hybrid Architecture

### Option 1: Keep Systems Separate (Recommended)

**Rationale**: Different use cases, minimal overlap

```
┌──────────────────────────────────────────────────────────────┐
│                    TradePulse V2 Platform                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────┐  ┌────────────────────────┐ │
│  │  Strategy Studio (V2 UI)   │  │  RL Portfolio Manager  │ │
│  │                            │  │  (Separate Interface)  │ │
│  │  • Parameter Optimization  │  │                        │ │
│  │  • Grid/Random/Bayesian    │  │  • Multi-asset         │ │
│  │  • Signal generation       │  │  • Portfolio weights   │ │
│  │  • Liquidity Sweep, etc.   │  │  • PPO training        │ │
│  │                            │  │                        │ │
│  │  Output:                   │  │  Output:               │ │
│  │  trained_configurations    │  │  model.pkl files       │ │
│  │  table                     │  │  pattern_training_     │ │
│  │                            │  │  results table         │ │
│  └────────────────────────────┘  └────────────────────────┘ │
│           ↓                              ↓                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Execution Layer (main.py)                     │ │
│  │                                                        │ │
│  │  • Load active configs from trained_configurations    │ │
│  │  • Execute rule-based strategies                      │ │
│  │  • Optionally: Query RL model for portfolio balance   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**Implementation**:
1. **V2 UI**: Only shows `trained_configurations` (parameter-based strategies)
2. **New RL Tab**: Separate page for RL model management
3. **Execution**: Trading bot uses both systems for different decisions

---

### Option 2: Convert RL Results to Configurations (Complex)

**Not recommended** - Forces incompatible paradigms together

Would require:
1. Translate PPO model weights into "fake" strategy parameters
2. Convert portfolio decisions into entry/exit signals
3. Create artificial lifecycle stages for RL models
4. Complex mapping logic that obscures true behavior

---

## Recommended Integration Strategy

### Phase 1: Keep Separate, Add RL Dashboard (Week 3-4)

**New V2 Route**: `/rl-portfolio`

```typescript
// tradepulse-v2/pages/RLPortfolio.tsx
export default function RLPortfolio() {
  return (
    <div>
      <h1>RL Portfolio Manager</h1>
      
      {/* Show PPO model status */}
      <ModelStatus model={currentPPOModel} />
      
      {/* Training interface */}
      <TrainingPanel 
        symbols={['BTC/USDT', 'ETH/USDT', 'SOL/USDT']}
        onStartTraining={startPPOTraining}
      />
      
      {/* Current allocations */}
      <PortfolioWeights weights={rlWeights} />
      
      {/* Training history */}
      <TrainingHistory results={patternTrainingResults} />
    </div>
  );
}
```

**Backend**: Extend `api/training.py` with RL-specific endpoints

```python
@router.get("/api/rl/models")
async def get_rl_models():
    """List available PPO models"""
    # Scan ml/trained_assets/*.pkl
    pass

@router.post("/api/rl/train")
async def start_rl_training(symbols: List[str]):
    """Launch PPO training job"""
    # Call policy/train_strategy_aware.py
    pass

@router.get("/api/rl/allocations")
async def get_current_allocations():
    """Get RL model's portfolio recommendations"""
    # Load PPO model, predict weights
    pass
```

---

### Phase 2: Execution Layer Integration (Week 5)

**Hybrid Trading Bot**:

```python
# main.py (simplified)

class HybridTradingBot:
    def __init__(self):
        # Rule-based strategies from Strategy Studio
        self.active_configs = self._load_active_configs()
        
        # RL portfolio manager (optional)
        self.rl_model = self._load_rl_model() if USE_RL else None
    
    def execute_trading_cycle(self):
        """
        1. Rule-based strategies generate entry/exit signals
        2. RL model suggests portfolio allocation
        3. Combine both for final decision
        """
        
        # STRATEGY STUDIO: Get signals
        signals = []
        for config in self.active_configs:
            strategy = self._instantiate_strategy(config)
            signal = strategy.check_signal(current_data)
            if signal:
                signals.append(signal)
        
        # RL PORTFOLIO: Get allocation weights (optional)
        if self.rl_model:
            state = self._build_rl_state()
            portfolio_weights = self.rl_model.predict(state)
            
            # Adjust signal sizing based on RL recommendation
            for signal in signals:
                symbol = signal.symbol
                rl_weight = portfolio_weights.get(symbol, 0)
                signal.position_size *= rl_weight
        
        # Execute combined signals
        self._execute_signals(signals)
    
    def _load_active_configs(self):
        """Load from trained_configurations table (V2 UI)"""
        query = "SELECT * FROM trained_configurations WHERE is_active = TRUE"
        # ...
    
    def _load_rl_model(self):
        """Load PPO model from ml/trained_assets/"""
        from stable_baselines3 import PPO
        return PPO.load("ml/trained_assets/ppo_portfolio_v1.pkl")
```

**Use Case**:
- **Strategy Studio configs**: Determine WHEN to enter/exit (signals)
- **RL Model**: Determine HOW MUCH to allocate (position sizing)

---

## Updated Training Implementation Plan

### Revised DataCollector (database-first)

```python
# training/data_collector.py

import pandas as pd
import numpy as np
import time
from shared.db import get_db_conn
from typing import Optional

class DataCollector:
    """
    REVISED: Database-first data collection with API fallback
    Reuses existing market_data table from data/real_exchange_data_collector.py
    """
    
    def __init__(self):
        self.db_conn = get_db_conn()
        # Only initialize if needed for fallback
        self._exchange_clients = None
    
    def fetch_ohlcv(
        self, 
        symbol: str, 
        exchange: str, 
        timeframe: str = '5m',
        lookback_days: int = 90
    ) -> pd.DataFrame:
        """
        Primary method: Fetch OHLCV data
        
        Priority:
        1. Database (instant)
        2. API fallback (if missing)
        
        Returns DataFrame with columns:
        ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'atr', 'sma_20']
        """
        
        # Try database first
        df = self._fetch_from_database(symbol, exchange, lookback_days)
        
        # Fallback to API if empty
        if df.empty:
            logger.warning(f"No data in DB for {symbol} on {exchange}, fetching from API...")
            df = self._fetch_from_api_and_cache(symbol, exchange, timeframe, lookback_days)
        
        # Calculate indicators
        df = self._calculate_indicators(df)
        
        return df
    
    def _fetch_from_database(
        self, 
        symbol: str, 
        exchange: str, 
        lookback_days: int
    ) -> pd.DataFrame:
        """Query existing market_data table"""
        
        end_ts = int(time.time())
        start_ts = end_ts - (lookback_days * 86400)
        
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = %s 
              AND exchange = %s
              AND timestamp >= %s 
              AND timestamp <= %s
            ORDER BY timestamp ASC
        """
        
        with self.db_conn.cursor() as cur:
            cur.execute(query, (symbol, exchange, start_ts, end_ts))
            rows = cur.fetchall()
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(
            rows, 
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        logger.info(f"✅ Loaded {len(df)} candles from database for {symbol}")
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ATR and SMA indicators"""
        
        if df.empty:
            return df
        
        # Average True Range (ATR)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        
        # Simple Moving Average
        df['sma_20'] = df['close'].rolling(window=20).mean()
        
        # Drop NaN rows from indicator calculation
        df = df.dropna()
        
        return df
    
    def _fetch_from_api_and_cache(
        self, 
        symbol: str, 
        exchange: str,
        timeframe: str,
        lookback_days: int
    ) -> pd.DataFrame:
        """
        Fallback: Fetch from exchange API and cache to database
        Uses same pattern as data/real_exchange_data_collector.py
        """
        
        if self._exchange_clients is None:
            self._init_exchange_clients()
        
        if exchange not in self._exchange_clients:
            logger.error(f"Exchange {exchange} not available")
            return pd.DataFrame()
        
        exchange_client = self._exchange_clients[exchange]
        
        # Calculate time window
        since = int((time.time() - lookback_days * 86400) * 1000)  # ms
        
        try:
            ohlcv = exchange_client.fetch_ohlcv(
                symbol, 
                timeframe, 
                since=since, 
                limit=1000
            )
            
            # Cache to database
            self._insert_ohlcv_batch(symbol, exchange, ohlcv)
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = df['timestamp'] // 1000  # ms -> seconds
            
            logger.info(f"✅ Fetched {len(df)} candles from {exchange} API for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"API fetch failed: {e}")
            return pd.DataFrame()
    
    def _init_exchange_clients(self):
        """Initialize CCXT clients (copied from data/real_exchange_data_collector.py)"""
        import ccxt
        
        self._exchange_clients = {
            'binanceus': ccxt.binanceus(),
            'coinbase': ccxt.coinbase(),
            'kraken': ccxt.kraken(),
            'bitstamp': ccxt.bitstamp(),
        }
        
        for name, client in self._exchange_clients.items():
            try:
                client.load_markets()
                logger.info(f"✅ Initialized {name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize {name}: {e}")
    
    def _insert_ohlcv_batch(self, symbol: str, exchange: str, ohlcv_data: list):
        """Insert fetched data into market_data table for future use"""
        
        with self.db_conn.cursor() as cur:
            for candle in ohlcv_data:
                timestamp_ms, open_p, high, low, close, volume = candle
                timestamp_s = timestamp_ms // 1000
                
                cur.execute("""
                    INSERT INTO market_data (exchange, symbol, timestamp, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (exchange, symbol, timestamp) DO NOTHING
                """, (exchange, symbol, timestamp_s, open_p, high, low, close, volume))
        
        self.db_conn.commit()
        logger.info(f"💾 Cached {len(ohlcv_data)} candles to database")
```

---

## Summary & Next Steps

### ✅ Decisions Made

1. **Training Data Source**: 
   - ✅ Database-first (use existing `market_data` table)
   - ✅ API fallback only if missing
   - ✅ 360x faster data loading

2. **RL System Integration**:
   - ✅ Keep separate from Strategy Studio
   - ✅ Add new `/rl-portfolio` route in V2 UI
   - ✅ Use RL for position sizing, configs for signals

### 📋 Implementation Checklist

**Week 1** (Parameter Optimization System):
- [x] Review existing infrastructure
- [ ] Create `training/data_collector.py` (database-first version)
- [ ] Create `training/backtest_engine.py`
- [ ] Create `training/strategies/liquidity_sweep.py`

**Week 2** (Optimization & Validation):
- [ ] Create `training/optimizers/` (grid, random, bayesian)
- [ ] Create `training/validator.py`
- [ ] Create `training_jobs` table
- [ ] API endpoints for training

**Week 3-4** (RL Integration):
- [ ] Create `tradepulse-v2/pages/RLPortfolio.tsx`
- [ ] Extend `api/training.py` with RL endpoints
- [ ] RL model viewer UI

**Week 5** (Execution Layer):
- [ ] Hybrid trading bot implementation
- [ ] Signal generation from configs
- [ ] Position sizing from RL model

---

## Ready to Proceed?

With these clarifications:
1. ✅ We'll use existing database data (not fetch during training)
2. ✅ RL system stays separate but integrates at execution layer
3. ✅ V2 UI shows parameter-based configs only

**Start Sprint 1, Day 1: Create database-first DataCollector?** 🚀
