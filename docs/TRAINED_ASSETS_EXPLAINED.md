# Trained Assets Detail Modal - Field Explanations

## Overview
This document explains every field shown in the Trained Configuration Details modal that appears when you click on a trained asset in the Trained Assets tab.

---

## Header Section

### Strategy Name
**Example:** `LIQUIDITY_SWEEP`

**What it means:** The name of the trading strategy being used. Currently, your system has one main strategy:
- **LIQUIDITY_SWEEP**: Detects "stop hunts" where price briefly pierces a key support/resistance level (triggering other traders' stop losses), then reverses direction. The strategy enters on the reversal.

### Exchange & Timeframe
**Example:** `binanceus • 5m`

**What it means:**
- **Exchange**: Which cryptocurrency exchange this configuration was trained on (`binanceus`, `cryptocom`, `coinbase`, `bitstamp`)
- **Timeframe**: The candlestick period (e.g., `1m` = 1 minute, `5m` = 5 minutes, `15m` = 15 minutes)

### Lifecycle Stage Badge
**Values:** DISCOVERY | VALIDATION | MATURE | DECAY | PAPER

**What it means:** The stage in the strategy's lifecycle:
- **DISCOVERY** (Purple): New configuration, recently discovered
- **VALIDATION** (Sky Blue): Being validated with more data
- **MATURE** (Green): Proven and reliable, performing well over time
- **DECAY** (Yellow): Performance degrading, needs review or retirement
- **PAPER** (Gray): Paper trading only (simulated, not live)

**Note:** Currently all your configurations show `PAPER` status, meaning they're not activated for live trading yet.

---

## Performance Snapshot

### Net Profit
**Example:** `-50.32%` (red) or `+15.45%` (green)

**What it means:** The total profit/loss percentage after all costs (fees + slippage). This is **the bottom line** - the actual money made or lost.

- **Formula**: `(total_gains - total_losses - fees - slippage) / initial_capital × 100`
- **Negative = Losing money** (shown in red)
- **Positive = Making money** (shown in green)

**Your data shows:** `-50.32%` and `-14.30%` → The strategy is **losing money heavily** with these parameters.

### Gross Win Rate
**Example:** `0.15%` or `0.20%`

**What it means:** The percentage of trades that were winners (before costs).

- **Formula**: `winning_trades / total_trades × 100`
- **Example**: If you took 100 trades and 55 won, win rate = 55%

**Your data shows:** `0.15%` (0.0015) → **Only ~1 out of 667 trades wins!** This is **extremely low**.

**Normal range:** Good strategies typically have 40-65% win rates.

### Sharpe Ratio
**Example:** `-11.23` or `2.50`

**What it means:** Risk-adjusted return metric. Measures how much return you get per unit of risk taken.

- **Formula**: `(average_return - risk_free_rate) / volatility_of_returns`
- **Interpretation:**
  - **< 0**: Losing money (your case: -11.23)
  - **0 to 1**: Poor risk-adjusted returns
  - **1 to 2**: Acceptable
  - **2 to 3**: Good
  - **> 3**: Excellent

**Your data:** `-11.23` → Strategy is losing money with high volatility (very bad).

### Sample Size
**Example:** `80 trades` or `45 trades`

**What it means:** How many trades occurred during the backtest period.

- **Importance:** More trades = more statistical confidence
- **Minimum recommended:** 30+ trades for basic confidence, 100+ for strong confidence
- **Your data:** 80 and 45 trades → Sample sizes are reasonable for initial testing

---

## Strategy Parameters

These are the **tunable knobs** that the ML optimizer adjusts to find the best settings.

### pierce_depth
**Example:** `0.0041` (0.41%)

**What it means:** How far price must pierce through a support/resistance level to trigger a "liquidity sweep" detection.

- **Lower values** (e.g., 0.001 = 0.1%): More sensitive, catches smaller sweeps, more signals
- **Higher values** (e.g., 0.01 = 1%): Less sensitive, only catches bigger sweeps, fewer signals

### reversal_candles  
**Example:** `3` or `5`

**What it means:** How many candles must show reversal pattern after the sweep before entering the trade.

- **Lower** (e.g., 1-2): Enter quickly, catch reversals early, but more false signals
- **Higher** (e.g., 4-5): Wait for stronger confirmation, miss some moves but fewer false entries

### atr_multiplier_sl
**Example:** `1.52` (1.52× ATR)

**What it means:** Stop-loss distance based on ATR (Average True Range, a volatility measure).

- **ATR** measures typical price movement per candle
- **1.5× ATR** = Stop loss 1.5× the average candle size away from entry
- **Lower** (e.g., 1.0): Tighter stops, preserve capital but get stopped out more
- **Higher** (e.g., 2.5): Wider stops, give trade room to breathe but risk more per trade

### min_level_touches
**Example:** `4` or `5`

**What it means:** How many times price must touch a support/resistance level before it's considered "key" and valid for trading.

- **Lower** (e.g., 2-3): More levels qualify, more trading opportunities
- **Higher** (e.g., 5-6): Only strong, well-tested levels, fewer but higher quality setups

### risk_reward_ratio
**Example:** `3.60` (3.6:1)

**What it means:** The target profit relative to the risk (stop-loss distance).

- **Example**: If stop-loss is $10 away, target profit is 3.6 × $10 = $36 away
- **Lower** (e.g., 1.5:1): Easier to hit targets, higher win rate but smaller wins
- **Higher** (e.g., 4:1): Harder to hit targets, lower win rate but bigger wins when you do

### key_level_lookback
**Example:** `100` or `200` candles

**What it means:** How far back in history to look when identifying support/resistance levels.

- **Shorter** (e.g., 50): Only recent levels, adapts quickly to new conditions
- **Longer** (e.g., 200): Includes older levels, more stable but slower to adapt

### max_holding_periods
**Example:** `20` candles

**What it means:** Maximum time to hold a position before forcing an exit (even if neither stop-loss nor take-profit hit).

- **Purpose**: Prevents capital from being tied up in stagnant trades
- **5m timeframe + 20 periods = 100 minutes max hold time**

### volume_spike_threshold
**Example:** `3.38` (3.38× average volume)

**What it means:** Volume must be this many times higher than average to confirm a liquidity sweep.

- **Lower** (e.g., 1.5): Accept moderate volume, more signals
- **Higher** (e.g., 4.0): Require very high volume, fewer but stronger signals

### min_distance_from_level
**Example:** `0.0028` (0.28%)

**What it means:** Minimum distance between support/resistance levels for both to be considered valid.

- **Purpose**: Prevents clustering of too many levels close together
- **Lower**: Allow levels closer together
- **Higher**: Require more spacing between levels

---

## Statistical Validation

These metrics assess whether the strategy's performance is **statistically significant** or just random luck.

### sharpe_ratio
See above in Performance Snapshot.

### calmar_ratio
**Example:** `-0.98`

**What it means:** Return relative to worst drawdown.

- **Formula**: `annualized_return / max_drawdown`
- **Interpretation:**
  - **< 0**: Losing strategy (your case)
  - **1.0**: Return equals worst drawdown
  - **2.0+**: Good, returns exceed worst losses
  - **3.0+**: Excellent

**Your data:** `-0.98` → Negative returns with drawdowns (bad).

### p_value
**Example:** `0.05` or `null`

**What it means:** Statistical significance test. Probability that results are due to random chance.

- **< 0.05**: Statistically significant (< 5% chance of luck)
- **> 0.05**: Could be random luck, not significant
- **null**: Not calculated yet

**Your data:** Shows `None` → This validation test wasn't run.

### z_score
**Example:** `2.5` or `null`

**What it means:** How many standard deviations away from random performance.

- **> 1.96**: Significant at 95% confidence
- **> 2.58**: Significant at 99% confidence
- **< 0**: Worse than random

**Your data:** Shows `None` → Not calculated.

### stability_score
**Example:** `0.75` or `null`

**What it means:** Measures consistency of performance across different market conditions and time periods.

- **0.0 to 0.3**: Very unstable
- **0.3 to 0.6**: Moderate stability
- **0.6 to 0.8**: Stable
- **0.8 to 1.0**: Very stable

**Your data:** Shows `None` → Not calculated.

---

## Market Regime Probabilities

**Example:** `Trending: 45% | Ranging: 30% | Volatile: 25%`

**What it means:** The trained configuration's analysis of what percentage of time the market was in each regime during training.

### trending
**Definition:** Market moving clearly in one direction (up or down) with sustained momentum.
- **Strategy impact:** Trend-following strategies work well, mean-reversion strategies struggle

### ranging
**Definition:** Market moving sideways, bouncing between support and resistance without clear direction.
- **Strategy impact:** Mean-reversion strategies work well, trend-following struggles

### volatile
**Definition:** Market with large, erratic price swings and high uncertainty.
- **Strategy impact:** Risk management critical, strategies need wider stops

**Purpose:** Helps understand in what market conditions this configuration was trained. If it only saw "ranging" markets, it may fail when trends emerge.

**Your data:** Currently shows this section in the modal but regime_json is `null` in the database, so it won't display properly.

---

## What You're Currently Seeing

Based on your actual database data, here's what your trained configurations show:

```
Configuration 1: LIQUIDITY_SWEEP on binanceus SOL/USDT 5m
├─ Net Profit: -50.32% ❌ (LOSING)
├─ Win Rate: 0.15% ❌ (TERRIBLE - only 1 in 667 trades wins!)
├─ Sample Size: 80 trades ✓ (adequate for testing)
├─ Sharpe Ratio: -11.23 ❌ (losing with high volatility)
├─ Calmar Ratio: -0.98 ❌ (poor risk-adjusted return)
└─ Sortino Ratio: -31.67 ❌ (very poor downside risk)

Configuration 2: LIQUIDITY_SWEEP on binanceus SOL/USDT 1m
├─ Net Profit: -14.30% ❌ (LOSING)
├─ Win Rate: 0.20% ❌ (TERRIBLE - only 1 in 500 trades wins!)
├─ Sample Size: 45 trades ✓ (adequate for testing)
├─ Sharpe Ratio: -11.37 ❌ (losing with high volatility)
├─ Calmar Ratio: -1.00 ❌ (poor risk-adjusted return)
└─ Sortino Ratio: -41.21 ❌ (very poor downside risk)
```

**⚠️ CRITICAL ISSUE DETECTED:** Both configurations have **catastrophically low win rates** (0.15% and 0.20%). This means:
- Out of 80 trades, maybe 0-1 won
- Out of 45 trades, maybe 0-1 won
- The strategy is essentially losing on every single trade

This is **NOT normal** and indicates a serious problem in the training/backtesting system.

---

## Next Steps

See the companion document **`TRAINING_SYSTEM_ISSUES.md`** for detailed analysis of what's wrong and how to fix it.
