# Data Backfill Plan - Achieving 10-20k Candles Per Timeframe

**Date:** October 26, 2025  
**Current Status:** 8.66M records total  
**Target:** 10k minimum, 20k ideal per timeframe/symbol/exchange combo

## Current State Analysis

### What We Have (BinanceUS - Primary Training Exchange)

| Symbol | 1m | 5m | 15m | 1h | 4h | 1d | Status |
|--------|----|----|-----|----|----|-----|---------|
| **BTC/USDT** | 777k ✅ | 155k ✅ | 51k ✅ | 13k ✅ | 3.2k ❌ | 540 ❌ | **GOOD** |
| **ETH/USDT** | 777k ✅ | 155k ✅ | 51k ✅ | 13k ✅ | 3.2k ❌ | 540 ❌ | **GOOD** |
| **SOL/USDT** | 777k ✅ | 155k ✅ | 51k ✅ | 13k ✅ | 3.2k ❌ | 540 ❌ | **GOOD** |
| **BNB/USDT** | 327k ⚠️ | 103k ✅ | 34k ✅ | 8.6k ❌ | 2.1k ❌ | 360 ❌ | **GAPS** |
| ADA/USDT | 1k ❌ | 1k ❌ | 1k ❌ | 1k ❌ | 360 ❌ | 100 ❌ | **BAD** |
| AVAX/USDT | 1k ❌ | 1k ❌ | 1k ❌ | 1k ❌ | 360 ❌ | 100 ❌ | **BAD** |
| DOT/USDT | 1k ❌ | 1k ❌ | 1k ❌ | 1k ❌ | 360 ❌ | 100 ❌ | **BAD** |
| MATIC/USDT | 1k ❌ | 1k ❌ | 269 ❌ | 0 ❌ | 0 ❌ | 0 ❌ | **CRITICAL** |

### Target vs Reality Check

**10k Candle Target by Timeframe:**
- **1m (1 minute)**: 10k candles = ~7 days 🎯 EASY
- **5m (5 minute)**: 10k candles = ~35 days 🎯 EASY
- **15m (15 minute)**: 10k candles = ~104 days (3.5 months) 🎯 MODERATE
- **1h (hourly)**: 10k candles = ~417 days (14 months) ⚠️ HARD
- **4h (4 hour)**: 10k candles = ~1,667 days (4.6 YEARS) ❌ UNREALISTIC
- **1d (daily)**: 10k candles = ~27 YEARS ❌ IMPOSSIBLE

**20k Candle Target by Timeframe:**
- **1m**: 20k candles = ~14 days 🎯 EASY
- **5m**: 20k candles = ~69 days (2.3 months) 🎯 EASY
- **15m**: 20k candles = ~208 days (7 months) 🎯 MODERATE
- **1h**: 20k candles = ~833 days (2.3 years) ⚠️ VERY HARD
- **4h**: 20k candles = ~3,333 days (9+ YEARS) ❌ UNREALISTIC
- **1d**: 20k candles = ~55 YEARS ❌ IMPOSSIBLE

## Revised Realistic Goals

### Tier 1: Achievable Targets (Based on Data Availability)

| Timeframe | Realistic Target | Days Needed | Why |
|-----------|------------------|-------------|-----|
| **1m** | 500k - 1M | 347-694 days | Maximum depth, training granularity |
| **5m** | 100k - 200k | 347-694 days | Good balance of detail and history |
| **15m** | 30k - 50k | 312-521 days | Best for swing trading strategies |
| **1h** | 8k - 16k | 333-667 days | Good for position analysis |
| **4h** | 2k - 4k | 333-667 days | Long-term trend detection |
| **1d** | 500 - 1000 | 500-1000 days | Market regime identification |

### Tier 2: Our Current Status vs Goals

| Symbol | Timeframe | Current | Target | Gap | Priority |
|--------|-----------|---------|--------|-----|----------|
| BTC/ETH/SOL | 1m | 777k | 500k | ✅ EXCEEDED | Maintain |
| BTC/ETH/SOL | 5m | 155k | 100k | ✅ EXCEEDED | Maintain |
| BTC/ETH/SOL | 15m | 51k | 30k | ✅ EXCEEDED | Maintain |
| BTC/ETH/SOL | 1h | 13k | 10k | ✅ EXCEEDED | Maintain |
| BTC/ETH/SOL | 4h | 3.2k | 3k | ✅ EXCEEDED | Maintain |
| BTC/ETH/SOL | 1d | 540 | 500 | ✅ EXCEEDED | Maintain |
| **BNB/USDT** | **1m** | **327k** | **500k** | **-173k** | **🔴 HIGH** |
| **BNB/USDT** | **1h** | **8.6k** | **10k** | **-1.4k** | **🔴 HIGH** |
| **BNB/USDT** | **4h** | **2.1k** | **3k** | **-900** | **🔴 HIGH** |
| **ADA/AVAX/DOT** | **ALL** | **1k** | **varies** | **CRITICAL** | **🔴 CRITICAL** |
| **MATIC** | **ALL** | **<1k** | **varies** | **CRITICAL** | **🔴 CRITICAL** |

## Recommended Actions

### ✅ RECOMMENDATION 1: Keep 1d Timeframe in UI
**Reason:** We have 540 days of daily data for BTC/ETH/SOL - that's plenty!
- 540 days = ~18 months of market cycles
- Enough to train regime detection algorithms
- Captures bull/bear/sideways transitions
- **Action:** Keep 1d option, it's fine!

### 🎯 RECOMMENDATION 2: Adjust Backfill Script for Realistic Goals

**Modify `massive_historical_backfill.py` with these changes:**

1. **Update target months based on timeframe:**
   ```python
   # Instead of fixed 18 months, use optimal per timeframe:
   optimal_months = {
       '1m': 18,   # ~777k candles
       '5m': 18,   # ~155k candles  
       '15m': 18,  # ~52k candles
       '1h': 24,   # ~17k candles (need 2 years for 10k+)
       '4h': 24,   # ~4.3k candles (need 2 years for 3k+)
       '1d': 36    # ~1095 candles (need 3 years for 1k)
   }
   ```

2. **Focus backfill on priority gaps:**
   - **Priority 1:** BNB/USDT - fill gaps to match BTC/ETH/SOL
   - **Priority 2:** ADA/AVAX/DOT - get to 18 months like BTC/ETH/SOL
   - **Priority 3:** MATIC - emergency backfill (almost no data)

3. **Skip timeframes that are already good:**
   - Don't re-fetch BTC/ETH/SOL on timeframes we already exceed targets
   - Only fill gaps and new symbols

### 📋 RECOMMENDATION 3: Create Targeted Backfill Script

Instead of running the full `massive_historical_backfill.py` again (which would take 6-12 hours), create a **targeted gap-filler**:

**File:** `data/targeted_backfill.py`

```python
# Focused backfill for specific gaps:
BACKFILL_TARGETS = {
    'binanceus': {
        'BNB/USDT': {
            '1m': {'months': 24, 'priority': 'HIGH'},  # Fill gaps to 500k+
            '1h': {'months': 24, 'priority': 'HIGH'},  # Get to 10k+
            '4h': {'months': 24, 'priority': 'HIGH'},  # Get to 3k+
        },
        'ADA/USDT': {
            'ALL': {'months': 18, 'priority': 'CRITICAL'}
        },
        'AVAX/USDT': {
            'ALL': {'months': 18, 'priority': 'CRITICAL'}
        },
        'DOT/USDT': {
            'ALL': {'months': 18, 'priority': 'CRITICAL'}
        },
        'MATIC/USDT': {
            'ALL': {'months': 24, 'priority': 'CRITICAL'}
        }
    }
}
```

### 🔧 RECOMMENDATION 4: Script Modifications

**File to modify:** `/workspaces/Trad/data/massive_historical_backfill.py`

**Changes needed:**
1. ✅ Add `--symbols` flag to target specific symbols
2. ✅ Add `--timeframes` flag to target specific timeframes  
3. ✅ Add `--exchange` flag to focus on one exchange (binanceus)
4. ✅ Add `--fill-gaps-only` flag to skip what we already have
5. ✅ Increase months_back for 1h/4h/1d to get more data

Example usage:
```bash
# Fill BNB gaps only
python3 data/massive_historical_backfill.py \
  --exchange binanceus \
  --symbols BNB/USDT \
  --months 24 \
  --fill-gaps-only

# Fill all altcoins
python3 data/massive_historical_backfill.py \
  --exchange binanceus \
  --symbols ADA/USDT,AVAX/USDT,DOT/USDT,MATIC/USDT \
  --months 18 \
  --auto-confirm
```

## Execution Plan

### Phase 1: Emergency Fix (2-3 hours)
```bash
# 1. Fix MATIC (almost no data)
python3 data/massive_historical_backfill.py \
  --exchange binanceus \
  --symbols MATIC/USDT \
  --months 24 \
  --auto-confirm

# 2. Fix ADA/AVAX/DOT (only 1k candles each)
python3 data/massive_historical_backfill.py \
  --exchange binanceus \
  --symbols ADA/USDT,AVAX/USDT,DOT/USDT \
  --months 18 \
  --auto-confirm
```

### Phase 2: Fill BNB Gaps (3-4 hours)
```bash
# Fill BNB to match BTC/ETH/SOL quality
python3 data/massive_historical_backfill.py \
  --exchange binanceus \
  --symbols BNB/USDT \
  --months 24 \
  --auto-confirm
```

### Phase 3: Extend 1h/4h/1d Globally (optional, 4-6 hours)
```bash
# Get more 1h/4h/1d data for ALL symbols
python3 data/massive_historical_backfill.py \
  --exchange binanceus \
  --timeframes 1h,4h,1d \
  --months 36 \
  --auto-confirm
```

## Expected Outcomes

### After Phase 1+2 (Target: 5-7 hours)
| Symbol | 1m | 5m | 15m | 1h | 4h | 1d | Status |
|--------|----|----|-----|----|----|-----|---------|
| BTC/USDT | 777k ✅ | 155k ✅ | 51k ✅ | 13k ✅ | 3.2k ✅ | 540 ✅ | **EXCELLENT** |
| ETH/USDT | 777k ✅ | 155k ✅ | 51k ✅ | 13k ✅ | 3.2k ✅ | 540 ✅ | **EXCELLENT** |
| SOL/USDT | 777k ✅ | 155k ✅ | 51k ✅ | 13k ✅ | 3.2k ✅ | 540 ✅ | **EXCELLENT** |
| BNB/USDT | 500k+ ✅ | 120k+ ✅ | 40k+ ✅ | 12k+ ✅ | 3k+ ✅ | 720 ✅ | **EXCELLENT** |
| ADA/USDT | 500k+ ✅ | 100k+ ✅ | 30k+ ✅ | 10k+ ✅ | 3k+ ✅ | 540 ✅ | **EXCELLENT** |
| AVAX/USDT | 500k+ ✅ | 100k+ ✅ | 30k+ ✅ | 10k+ ✅ | 3k+ ✅ | 540 ✅ | **EXCELLENT** |
| DOT/USDT | 500k+ ✅ | 100k+ ✅ | 30k+ ✅ | 10k+ ✅ | 3k+ ✅ | 540 ✅ | **EXCELLENT** |
| MATIC/USDT | 400k+ ✅ | 80k+ ✅ | 25k+ ✅ | 10k+ ✅ | 3k+ ✅ | 720 ✅ | **GOOD** |

### Total Records After Backfill
- **Current:** 8.66M records
- **After Phase 1+2:** ~12-14M records (est. +3-5M)
- **Storage:** ~3-4 GB total

## Summary

✅ **Keep 1d timeframe** - we have enough daily data  
🎯 **10k candle goal is unrealistic for 4h/1d** - adjust expectations  
🔧 **Modify existing script** - add flags for targeted backfill  
🚀 **Focus on gaps** - BNB, ADA, AVAX, DOT, MATIC need attention  
⏱️ **Estimated time:** 5-7 hours for critical gaps  
💾 **Storage impact:** +3-5M records (~40-60% increase)

The script already works well - we just need to:
1. Run it with specific targets (not everything)
2. Increase months for 1h/4h/1d timeframes (18→24-36 months)
3. Skip what we already have (BTC/ETH/SOL are perfect)
