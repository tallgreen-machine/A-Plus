# Intra-Episode Progress Tracking Implementation

## Overview
Add real-time progress updates **during** each training episode, showing candle-by-candle progress as the backtest processes historical data.

## Current Architecture

```
Training Job
  └─> Optimizer (Random/Grid/Bayesian)
      └─> evaluate_config() [✅ Has callbacks - DONE]
          └─> BacktestEngine.run_backtest()
              └─> strategy.generate_signals(data)  [❌ No callbacks]
              └─> _simulate_trades(data, signals)   [❌ No callbacks]
```

## What You'll See

**Current (Episode-level only):**
```
Progress: 5% (Episode 1/20)
Progress: 10% (Episode 2/20)
Progress: 15% (Episode 3/20)
...
```

**After Implementation (Candle-level):**
```
Progress: 5% (Episode 1/20) - Processing candle 500/10000 (5%)
Progress: 5% (Episode 1/20) - Processing candle 1000/10000 (10%)
Progress: 5% (Episode 1/20) - Processing candle 1500/10000 (15%)
...
Progress: 5% (Episode 1/20) - Processing candle 10000/10000 (100%)
Progress: 10% (Episode 2/20) - Processing candle 500/10000 (5%)
...
```

## Implementation Requirements

### 1. Add Callback Parameter to BacktestEngine

**File:** `/workspaces/Trad/training/backtest_engine.py`

```python
def run_backtest(
    self,
    data: pd.DataFrame,
    strategy_instance: Any,
    position_size_pct: float = 1.0,
    progress_callback: Optional[callable] = None  # NEW
) -> BacktestResult:
    """
    Run backtest simulation.
    
    Args:
        data: OHLCV DataFrame with indicators
        strategy_instance: Strategy object with generate_signals()
        position_size_pct: Position sizing multiplier
        progress_callback: Optional callback(current, total, stage)
                         Called periodically during backtest
    """
    total_candles = len(data)
    
    # Generate signals (50% of work)
    signals = strategy_instance.generate_signals(
        data, 
        progress_callback=lambda c, t: progress_callback(
            c, t * 2, 'signal_generation'
        ) if progress_callback else None
    )
    
    # Simulate trades (50% of work)
    trades = self._simulate_trades(
        data=data,
        signals=signals,
        strategy_params=strategy_instance.params,
        position_size_pct=position_size_pct,
        progress_callback=lambda c, t: progress_callback(
            total_candles + c, total_candles * 2, 'trade_simulation'
        ) if progress_callback else None
    )
    
    # ... rest of method
```

### 2. Add Callbacks to Signal Generation

**File:** `/workspaces/Trad/training/strategies/liquidity_sweep.py`

```python
def generate_signals(
    self, 
    data: pd.DataFrame,
    progress_callback: Optional[callable] = None  # NEW
) -> pd.DataFrame:
    """
    Generate trading signals from OHLCV data.
    
    Args:
        data: DataFrame with OHLCV + indicators
        progress_callback: Optional callback(current, total, stage)
    """
    log.info(f"Generating signals: {len(data)} candles")
    
    df = data.copy()
    total_candles = len(df)
    
    # ... existing setup code ...
    
    # Track progress every N candles (don't spam callbacks)
    update_frequency = max(1, total_candles // 100)  # Update at most 100 times
    
    for i, idx in enumerate(range(self.key_level_lookback, len(df))):
        # ... existing signal generation code ...
        
        # Fire callback periodically
        if progress_callback and (i % update_frequency == 0 or i == total_candles - 1):
            progress_callback(i + 1, total_candles, 'signals')
    
    # ... rest of method
```

### 3. Add Callbacks to Trade Simulation

**File:** `/workspaces/Trad/training/backtest_engine.py`

```python
def _simulate_trades(
    self,
    data: pd.DataFrame,
    signals: pd.DataFrame,
    strategy_params: Dict[str, Any],
    position_size_pct: float,
    progress_callback: Optional[callable] = None  # NEW
) -> List[Trade]:
    """
    Simulate trade execution based on signals.
    
    Args:
        data: OHLCV data
        signals: Trading signals
        strategy_params: Strategy parameters
        position_size_pct: Position size multiplier
        progress_callback: Optional callback(current, total, stage)
    """
    trades = []
    current_position = None
    
    df = data.copy()
    df = df.merge(signals, on='timestamp', how='left')
    df['signal'].fillna('HOLD', inplace=True)
    
    total_candles = len(df)
    update_frequency = max(1, total_candles // 100)
    
    for idx, row in df.iterrows():
        # ... existing trade simulation logic ...
        
        # Fire callback periodically
        if progress_callback and (idx % update_frequency == 0 or idx == total_candles - 1):
            progress_callback(idx + 1, total_candles, 'trades')
    
    return trades
```

### 4. Wire Callbacks Through Optimizer

**File:** `/workspaces/Trad/training/optimizers/random_search.py`

```python
def evaluate_config(params_tuple):
    """Evaluate a single parameter configuration."""
    i, params = params_tuple
    try:
        strategy = strategy_class(params)
        
        # Create nested callback for intra-episode progress
        def backtest_progress_callback(candle_num, total_candles, stage):
            """Nested callback for candle-level progress."""
            if progress_callback:
                # Calculate sub-progress within this episode
                episode_progress = (candle_num / total_candles) * 100
                # Fire parent callback with metadata
                progress_callback(
                    i + 1, 
                    len(all_params), 
                    objective_value,
                    metadata={
                        'candles_processed': candle_num,
                        'total_candles': total_candles,
                        'stage': stage,
                        'episode_progress': episode_progress
                    }
                )
        
        backtest_result = backtest_engine.run_backtest(
            data=data,
            strategy_instance=strategy,
            progress_callback=backtest_progress_callback  # NEW
        )
        
        # ... rest of method
```

### 5. Update Database Schema

**File:** `/workspaces/Trad/sql/schema/training_jobs.sql`

```sql
ALTER TABLE training_jobs
ADD COLUMN IF NOT EXISTS candles_processed INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_candles INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS backtest_stage VARCHAR(50) DEFAULT NULL;
```

### 6. Update ProgressCallback Class

**File:** `/workspaces/Trad/training/rq_jobs.py`

```python
class ProgressCallback:
    """Picklable progress callback with candle-level tracking."""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.last_log_time = 0
        self.last_db_update = 0
        
    def __call__(
        self, 
        iteration: int, 
        total: int, 
        score: float,
        metadata: Optional[Dict] = None  # NEW
    ):
        """
        Store progress state and update database.
        
        Args:
            iteration: Current episode number
            total: Total episodes
            score: Current objective score
            metadata: Optional dict with:
                     - candles_processed: int
                     - total_candles: int
                     - stage: str ('signals', 'trades')
                     - episode_progress: float (0-100)
        """
        import time
        import psycopg2
        
        try:
            step_pct = (iteration / total) * 100
            current_time = time.time()
            
            # Throttle logging to every 1 second
            if current_time - self.last_log_time >= 1.0:
                if metadata:
                    log.info(
                        f"🔔 Progress: Episode {iteration}/{total} ({step_pct:.1f}%) - "
                        f"Candle {metadata.get('candles_processed', 0)}/"
                        f"{metadata.get('total_candles', 0)} "
                        f"({metadata.get('episode_progress', 0):.1f}%) "
                        f"[{metadata.get('stage', 'unknown')}]"
                    )
                else:
                    log.info(f"🔔 Progress: Episode {iteration}/{total} ({step_pct:.1f}%), score={score:.4f}")
                self.last_log_time = current_time
            
            # Update DB every 5 seconds (not every callback)
            if current_time - self.last_db_update >= 5.0:
                try:
                    db_host = os.getenv('DB_HOST', 'localhost')
                    db_port = os.getenv('DB_PORT', '5432')
                    db_user = os.getenv('DB_USER', 'traduser')
                    db_pass = os.getenv('DB_PASSWORD', 'TRAD123!')
                    db_name = os.getenv('DB_NAME', 'trad')
                    
                    conn = psycopg2.connect(
                        host=db_host, port=db_port,
                        user=db_user, password=db_pass,
                        dbname=db_name, connect_timeout=5
                    )
                    cur = conn.cursor()
                    
                    score_value = float(score) if score is not None else None
                    
                    if metadata:
                        # Update with candle-level details
                        cur.execute("""
                            UPDATE training_jobs
                            SET progress = %s,
                                current_episode = %s,
                                total_episodes = %s,
                                current_reward = %s,
                                current_loss = %s,
                                current_stage = %s,
                                candles_processed = %s,
                                total_candles = %s,
                                backtest_stage = %s
                            WHERE id = %s
                        """, (
                            round(step_pct, 2),
                            iteration,
                            total,
                            score_value if score_value and score_value > 0 else None,
                            abs(score_value) if score_value and score_value < 0 else None,
                            'Training',
                            metadata.get('candles_processed', 0),
                            metadata.get('total_candles', 0),
                            metadata.get('stage', None),
                            int(self.job_id)
                        ))
                    else:
                        # Fallback to episode-level only
                        cur.execute("""
                            UPDATE training_jobs
                            SET progress = %s,
                                current_episode = %s,
                                total_episodes = %s,
                                current_reward = %s,
                                current_loss = %s,
                                current_stage = 'Training'
                            WHERE id = %s
                        """, (
                            round(step_pct, 2),
                            iteration,
                            total,
                            score_value if score_value and score_value > 0 else None,
                            abs(score_value) if score_value and score_value < 0 else None,
                            int(self.job_id)
                        ))
                    
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    self.last_db_update = current_time
                    log.info(f"✅ DB updated: {step_pct:.1f}% (episode {iteration}/{total})")
                except Exception as e:
                    log.error(f"❌ DB update failed: {e}")
                    
        except Exception as e:
            log.error(f"❌ Callback error: {e}")
```

### 7. Update Frontend Display

**File:** `/workspaces/Trad/tradepulse-iq-dashboard/src/components/TrainingJobCard.tsx`

```typescript
interface TrainingJob {
  // ... existing fields ...
  candles_processed?: number;
  total_candles?: number;
  backtest_stage?: string;
}

// In the render:
{job.progress > 0 && (
  <div className="mt-2">
    <div className="flex justify-between text-sm mb-1">
      <span>Episode {job.current_episode}/{job.total_episodes}</span>
      <span>{job.progress.toFixed(1)}%</span>
    </div>
    <ProgressBar value={job.progress} />
    
    {/* NEW: Candle-level progress */}
    {job.candles_processed && job.total_candles && (
      <div className="text-xs text-gray-500 mt-1">
        Processing candle {job.candles_processed.toLocaleString()}/
        {job.total_candles.toLocaleString()} 
        ({((job.candles_processed / job.total_candles) * 100).toFixed(1)}%)
        {job.backtest_stage && ` - ${job.backtest_stage}`}
      </div>
    )}
  </div>
)}
```

## Performance Considerations

### 1. Callback Frequency
- **Problem:** Calling callback for every candle = 10,000 calls per episode
- **Solution:** Throttle to max 100 updates per episode
  ```python
  update_frequency = max(1, total_candles // 100)
  if idx % update_frequency == 0:
      progress_callback(...)
  ```

### 2. Database Updates
- **Problem:** DB writes are slow, can't update for every candle
- **Solution:** Update DB every 5 seconds (time-based throttling)
  ```python
  if current_time - self.last_db_update >= 5.0:
      # Update database
  ```

### 3. Parallel Worker Issues
- **Problem:** Callbacks from parallel workers can conflict
- **Solution:** Each worker has its own callback instance with job_id
  - Already implemented with `ProgressCallback` class

### 4. Logging Overhead
- **Problem:** Excessive logging slows down training
- **Solution:** Log at INFO level every 1 second, DEBUG for every update
  ```python
  if current_time - self.last_log_time >= 1.0:
      log.info(...)  # Only log once per second
  ```

## Estimated Impact

### Before (Current):
- Updates: ~20 per job (1 per episode)
- Granularity: 5% increments (20 episodes)
- User Experience: "Sits at 5% for 30 seconds"

### After (Intra-Episode):
- Updates: ~2,000 per job (100 per episode × 20 episodes)
- Granularity: 0.05% increments (1% of 5%)
- User Experience: "Smooth progress bar movement"

### Performance Cost:
- Signal generation: +1-2% overhead (100 callback calls per 10k candles)
- Trade simulation: +1-2% overhead (100 callback calls)
- Total: ~2-4% slower training (acceptable trade-off)

## Implementation Steps

1. **Add database columns** (5 min)
   ```bash
   psql -U traduser -d trad -f sql/schema/training_jobs_intra_episode.sql
   ```

2. **Update BacktestEngine** (15 min)
   - Add `progress_callback` parameter
   - Wire to `generate_signals()` and `_simulate_trades()`

3. **Update Strategy classes** (10 min each)
   - Add `progress_callback` to `generate_signals()`
   - Add throttled callback calls

4. **Update ProgressCallback** (10 min)
   - Add `metadata` parameter
   - Update DB query with candle fields
   - Add time-based throttling

5. **Update Optimizers** (10 min)
   - Create nested callback in `evaluate_config()`
   - Pass to `run_backtest()`

6. **Update Frontend** (15 min)
   - Add candle progress display
   - Format numbers with commas
   - Show current stage

7. **Test & Deploy** (30 min)
   - Test with 10k candle job
   - Verify smooth progress
   - Monitor performance impact

**Total Time: ~2 hours**

## Alternatives Considered

### 1. Frontend Interpolation (Rejected)
- Pro: No backend changes needed
- Con: Shows fake progress, not actual progress
- Reason: User explicitly requested "real backend progress"

### 2. Redis PubSub (Overkill)
- Pro: True real-time streaming
- Con: Complex architecture, additional service
- Reason: Current SSE + DB polling is sufficient

### 3. Worker-level Callbacks Only (Current)
- Pro: Simple, already implemented
- Con: Coarse-grained (episode-level only)
- Reason: User wants finer granularity

## Conclusion

This implementation provides **real-time candle-level progress** with minimal performance overhead (~2-4%). The callback architecture is already in place; we just need to add one more layer of callbacks at the backtest level.

The key insight is that training has **3 levels of progress**:
1. **Job level:** 0-100% (entire training job)
2. **Episode level:** 1/20, 2/20, etc. (already implemented ✅)
3. **Candle level:** 500/10000, 1000/10000, etc. (proposed ⚡)

By adding level 3, users get smooth, continuous progress updates that show exactly what the system is doing at any moment.
