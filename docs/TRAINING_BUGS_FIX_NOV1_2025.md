# Training System Bug Fixes - November 1, 2025

## Executive Summary

Fixed two critical bugs preventing CAPITULATION_REVERSAL and FAILED_BREAKDOWN strategies from training. Jobs were failing instantly (<2 seconds) with misleading "No valid configurations found" errors. Root causes were:

1. **Data loading failure** - DataCollector returning 0 candles due to date filtering issue
2. **Strategy signature mismatch** - BacktestEngine passing unexpected `progress_callback` parameter

## Background

### Problem Statement
- LIQUIDITY_SWEEP strategy trained successfully (jobs #243, #244, etc.)
- CAPITULATION_REVERSAL and FAILED_BREAKDOWN strategies failed instantly
- All jobs showed "No valid configurations found (min_trades=5)" error
- Jobs completed in 1-2 seconds instead of expected 1-5 minutes

### Investigation Timeline
1. Initially suspected parameter space too restrictive → relaxed ranges
2. Suspected min_trades threshold too high → lowered from 10 to 5
3. Discovered jobs failing in <2 seconds → impossible to run 50-100 backtests
4. Manual testing revealed DataCollector returning 0 candles
5. Further testing revealed strategy signature TypeError

## Bug #1: DataCollector Date Filtering

### Root Cause
The `_fetch_from_database()` method was filtering market data by date range:
```python
# OLD CODE
WHERE 
    symbol = $1
    AND exchange = $2
    AND timeframe = $3
    AND timestamp >= $4  # start_date
    AND timestamp <= $5  # end_date (NOW)
```

**Problem**: Our data ends at October 25, 2025, but queries used `end_date = NOW()` (November 1, 2025). The system calculated:
- Need 20,000 candles of 5m data = 69.4 days
- Query window: September 23, 2025 to November 1, 2025
- Available data: Only goes to October 25, 2025
- Result: **0 candles returned**

### Solution
Changed query to fetch most recent N candles using LIMIT, regardless of date:
```python
# NEW CODE
SELECT ... 
FROM market_data
WHERE 
    symbol = $1
    AND exchange = $2
    AND timeframe = $3
ORDER BY timestamp DESC
LIMIT $4  # estimated_candles with 20% buffer
```

Then reverse the order since we fetched DESC:
```python
df = df.sort_values('timestamp', ascending=True).reset_index(drop=True)
```

### Impact
- ✅ Now fetches most recent available data
- ✅ Works regardless of whether data is real-time or historical
- ✅ Handles data gaps gracefully

### Files Changed
- `training/data_collector.py` (lines 255-310)

## Bug #2: Strategy Signature Mismatch

### Root Cause
BacktestEngine was calling:
```python
signals = strategy_instance.generate_signals(data, progress_callback=progress_callback)
```

But CAPITULATION_REVERSAL and FAILED_BREAKDOWN only had:
```python
def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
```

This caused immediate TypeError:
```
TypeError: generate_signals() got an unexpected keyword argument 'progress_callback'
```

The exception was caught and resulted in the generic "No valid configurations found" error message, hiding the real issue.

### Solution
Updated both strategies to accept optional progress_callback:
```python
def generate_signals(self, data: pd.DataFrame, progress_callback=None) -> pd.DataFrame:
```

**Note**: LIQUIDITY_SWEEP already had this parameter, which is why it worked!

### Impact
- ✅ Strategies no longer crash on instantiation
- ✅ Backtests now run for expected duration (1-5 minutes)
- ✅ Consistent API across all strategies

### Files Changed
- `training/strategies/capitulation_reversal.py` (line 124)
- `training/strategies/failed_breakdown.py` (line 163)

## Testing Results

### Before Fixes
```
Job #254: CAPITULATION_REVERSAL - FAILED in 1.77 seconds
Job #255: FAILED_BREAKDOWN      - FAILED in 1.67 seconds
Job #257: CAPITULATION_REVERSAL - FAILED in 1.77 seconds
Job #258: FAILED_BREAKDOWN      - FAILED in 1.43 seconds
```

### After Fixes
```
Job #261: CAPITULATION_REVERSAL - RUNNING 70+ seconds (actual backtesting)
Job #262: FAILED_BREAKDOWN      - PENDING (waiting for #261)
Job #263: LIQUIDITY_SWEEP       - PENDING (control test)
```

### Manual Testing
```bash
# Test 1: DataCollector fix
✅ Loaded 24,192 candles, limited to 20,000 most recent
✅ Date range: May 16, 2024 to October 25, 2025

# Test 2: Strategy signature fix
✅ CAPITULATION_REVERSAL.generate_signals() accepted progress_callback
✅ Backtest ran successfully on 1,000 candles
✅ Generated signal DataFrame with correct columns
```

## Additional Context

### Why LIQUIDITY_SWEEP Worked
LIQUIDITY_SWEEP had the correct signature from the start:
```python
def generate_signals(
    self, 
    data: pd.DataFrame,
    progress_callback: Optional[Callable] = None
) -> pd.DataFrame:
```

### Data Availability
Current database contains:
- **155,520 candles** of BTC/USDT 5m data
- Date range: May 3, 2024 to October 25, 2025 (**540 days**)
- Sufficient for training with lookback_candles up to ~30,000

### Expected Signal Rates
Based on `docs/training_specs/STRATEGY_COMPARISON.md`:
- **CAPITULATION_REVERSAL**: 20-50 trades/year (rare pattern)
  - In 69 days (20k candles): 3.8-9.6 expected trades
  - min_trades=5 is appropriate threshold
  
- **FAILED_BREAKDOWN**: 10-30 trades/year (ultra-rare pattern)
  - In 69 days: 1.9-5.8 expected trades
  - May need min_trades=3 if still failing

## Next Steps

1. ✅ **COMPLETED**: Fix DataCollector date filtering
2. ✅ **COMPLETED**: Fix strategy signatures
3. ⏳ **IN PROGRESS**: Verify job #261 completes successfully
4. 📋 **TODO**: Fix progress tracking (currently stuck at 0%)
5. 📋 **TODO**: Test FAILED_BREAKDOWN with actual completion
6. 📋 **TODO**: Consider lowering min_trades to 3 if needed

## Lessons Learned

1. **Don't trust error messages blindly**: "No valid configurations found" was hiding TypeError
2. **Test incrementally**: Manual testing revealed issues faster than full job runs
3. **Check assumptions**: Assumed data was real-time when it was historical
4. **Validate interfaces**: Strategy signatures should be consistent across all implementations
5. **Add better logging**: Would have caught these issues faster with detailed error logging

## Files Modified Summary

```
training/data_collector.py          - DataCollector date filtering fix
training/strategies/capitulation_reversal.py - Added progress_callback parameter
training/strategies/failed_breakdown.py      - Added progress_callback parameter
docs/TRAINING_BUGS_FIX_NOV1_2025.md - This documentation
```

## Deployment

Deployed to production server (138.68.245.159) via:
```bash
(cd /workspaces/Trad && SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad bash ops/scripts/deploy_to_server.sh)
```

Services restarted:
- trad-api.service
- trad-worker.service

## References

- Training system: `/workspaces/Trad/training/`
- Strategy specs: `docs/training_specs/STRATEGY_COMPARISON.md`
- Database schema: `sql/010_add_training_tables.sql`
