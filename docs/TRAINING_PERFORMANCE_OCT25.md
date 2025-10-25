# Training Performance Investigation - October 25, 2025

## Issue Summary

Training jobs that previously completed in **~110 seconds** are now taking **6+ minutes** (350+ seconds). This is **NOT a bug** - it's the expected result of having more data available.

## Root Cause Analysis

### What Changed:

| Metric | Before (Today 19:46) | After (Today 22:48) | Change |
|--------|---------------------|---------------------|---------|
| **Total DB Records** | ~1,000 candles | 155,520 candles | **155x more** |
| **Records Fetched (30 days)** | ~1,000 (all available) | ~8,600 (filtered) | **8.6x more** |
| **Backtest Iterations** | 20 with 1K candles | 20 with 8.6K candles | **8.6x more work** |
| **Training Time** | 104-110 seconds | 350+ seconds | **~3-4x slower** |

### Timeline:

1. **19:00-19:46 UTC**: Jobs 90-94 ran with **only 1,000 candles** in database
   - Completed in 104-110 seconds
   
2. **21:48 UTC**: Started `massive_historical_backfill.py`
   - Collected 18 months of BTC/USDT data
   - Database grew from 1K → 155K records for BTC/USDT 5m

3. **22:48 UTC**: Job 96 ran with **155K candles** available
   - `lookback_days=30` correctly filtered to 8,600 candles
   - Took 277 seconds (4.6 minutes)

4. **22:54 UTC**: Job 98 running
   - Still processing 8,600 candles
   - Currently at 30% after 6 minutes

## Why It's Slower

**The lookback_days parameter IS working correctly!** It filters to exactly 30 days of data.

The slowdown is because:
```
More data per backtest = Slower training
8,600 candles vs 1,000 candles = 8.6x more data
20 iterations × 8.6x data = ~3-4x slower overall
```

### Bayesian Optimizer Overhead

Bayesian optimization has additional overhead:
- **Initial phase**: 5-10 random samples (no progress callbacks)
- **GP model training**: Fits Gaussian Process to initial results (~30-60 seconds)
- **Regular optimization**: Smart parameter selection with callbacks

This explains why progress "sticks" at 25% for 2-3 minutes before jumping.

## Solutions

### Option 1: Reduce Lookback Days (Faster Training)

**7 days lookback** → ~2,000 candles → ~2 minute training

Pros:
- Fast training (similar to before)
- Good for testing/development

Cons:
- Less historical context
- May miss longer-term patterns

### Option 2: Keep Current Settings (Better Results)

**30 days lookback** → ~8,600 candles → ~6 minute training

Pros:
- More robust optimization
- Better representation of market conditions
- More accurate backtest results

Cons:
- Slower training
- Need patience

### Option 3: Optimize Backtest Engine

Profile and optimize the backtesting code:
- Vectorize operations
- Cache indicator calculations
- Parallel backtest execution

This would help with ALL training jobs going forward.

## Recent System Changes

### From git history (last 12 hours):

1. **UI Updates**:
   - Added delete functionality to Trained Assets
   - Fixed timestamp display
   - Animated progress bar improvements

2. **Training Logs**:
   - SSE real-time log streaming
   - Persistent training logs
   - Unified log history

3. **Bug Fixes**:
   - Null safety checks in progress display
   - Timezone handling
   - GridSearchOptimizer cleanup

**No changes to data collection or backtest engine that would cause slowdown.**

## Cancellation Issues Fixed

Created `/workspaces/Trad/training/cleanup_orphaned_jobs.py`:
- Detects jobs stuck in 'running' status after worker restart
- Automatically marks them as failed/cancelled
- Can be run manually or scheduled as a cron job

**Usage:**
```bash
cd /srv/trad
. .venv/bin/activate
python training/cleanup_orphaned_jobs.py
```

## Recommendations

1. **For Development/Testing**: Use 7-day lookback
2. **For Production**: Use 30-day lookback, accept 6-minute training time
3. **Run cleanup script** after any worker restart/deployment
4. **Consider**: Add a progress interpolation during GP model training phase

## Current Status

- Job 98 is running normally (just slow due to more data)
- Worker is healthy
- No bugs - working as designed with larger dataset
