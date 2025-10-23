# Circuit Breaker Configuration

Default values for risk management across all trading strategies.

---

## Default Values

```python
CIRCUIT_BREAKERS = {
    # Portfolio Protection
    "max_daily_loss": 0.02,                    # 2% maximum loss per day
    
    # Diversification Protection  
    "max_correlation_spike": 0.8,              # 80% max correlation between configs
    
    # Market Anomaly Detection
    "unusual_market_threshold": 3.0,           # 3-sigma volatility spike
    
    # Execution Quality
    "latency_threshold_ms": 500,               # 500ms max execution latency
    "max_adverse_selection": 0.6,              # 60% adverse selection limit
    
    # Streak Protection
    "consecutive_losses_limit": 5,             # Pause after 5 consecutive losses
    
    # Regime Stability
    "regime_break_threshold": 0.3,             # <30% regime confidence triggers pause
}
```

---

## Usage in Code

### Configuration Level
Each `trained_configuration` will have its own circuit breaker settings (can override defaults):

```sql
-- In trained_configurations table
UPDATE trained_configurations
SET circuit_breakers = '{
  "max_daily_loss": 0.02,
  "max_correlation_spike": 0.8,
  "unusual_market_threshold": 3.0,
  "latency_threshold_ms": 500,
  "consecutive_losses_limit": 5,
  "max_adverse_selection": 0.6,
  "regime_break_threshold": 0.3
}'::jsonb
WHERE id = 'config_uuid';
```

### Runtime Monitoring
Trading engine checks circuit breakers on each trade:

```python
class TradingEngine:
    def check_circuit_breakers(self, config: TrainedConfiguration) -> bool:
        """Returns True if circuit breaker triggered"""
        
        # Check daily loss
        if self.calculate_daily_pnl() < -config.circuit_breakers['max_daily_loss']:
            self.trigger_circuit_breaker(config, 'MAX_DAILY_LOSS')
            return True
        
        # Check correlation
        if self.calculate_correlation(config) > config.circuit_breakers['max_correlation_spike']:
            self.trigger_circuit_breaker(config, 'CORRELATION_SPIKE')
            return True
        
        # Check market volatility
        if self.calculate_volatility_zscore() > config.circuit_breakers['unusual_market_threshold']:
            self.trigger_circuit_breaker(config, 'UNUSUAL_MARKET')
            return True
        
        # Check latency
        if self.last_execution_latency_ms > config.circuit_breakers['latency_threshold_ms']:
            self.trigger_circuit_breaker(config, 'HIGH_LATENCY')
            return True
        
        # Check consecutive losses
        if self.count_consecutive_losses(config) >= config.circuit_breakers['consecutive_losses_limit']:
            self.trigger_circuit_breaker(config, 'LOSS_STREAK')
            return True
        
        # Check adverse selection
        if config.execution_metrics['adverse_selection_score'] > config.circuit_breakers['max_adverse_selection']:
            self.trigger_circuit_breaker(config, 'ADVERSE_SELECTION')
            return True
        
        # Check regime confidence
        regime_probs = config.regime_classification['final_regime_probability']
        max_confidence = max(regime_probs.values())
        if max_confidence < config.circuit_breakers['regime_break_threshold']:
            self.trigger_circuit_breaker(config, 'REGIME_BREAK')
            return True
        
        return False
```

---

## Detailed Explanations

### 1. Max Daily Loss (2%)
**Purpose**: Prevent catastrophic drawdowns  
**Trigger**: If portfolio loses >2% in a single day  
**Action**: Pause ALL trading until next day  
**Rationale**: 2% daily loss = ~40% annual loss if it happened every day (it won't, but still dangerous)

**Example**:
- Portfolio value: $100,000
- Max daily loss: $2,000
- If PnL reaches -$2,000, stop trading for the day
- Resume next day at midnight UTC

---

### 2. Max Correlation Spike (0.8)
**Purpose**: Maintain portfolio diversification  
**Trigger**: If active configurations become >80% correlated  
**Action**: Deactivate newest configurations until correlation drops  
**Rationale**: High correlation = concentrated risk (all configs fail together)

**Example**:
- Configuration A and B normally have 0.4 correlation (healthy)
- Suddenly correlation jumps to 0.85 (both losing together)
- System detects correlation spike
- Deactivates Configuration B (newer/less proven)
- Keeps Configuration A (older/more proven)

**Calculation**:
```python
def calculate_correlation(configs: List[TrainedConfiguration]) -> float:
    """Calculate rolling 30-day returns correlation"""
    returns_matrix = []
    for config in configs:
        daily_returns = get_daily_returns(config, days=30)
        returns_matrix.append(daily_returns)
    
    correlation_matrix = np.corrcoef(returns_matrix)
    max_correlation = np.max(correlation_matrix[np.triu_indices_from(correlation_matrix, k=1)])
    return max_correlation
```

---

### 3. Unusual Market Threshold (3.0 sigma)
**Purpose**: Detect black swan events or market anomalies  
**Trigger**: Volatility >3 standard deviations from normal  
**Action**: Pause trading until volatility normalizes  
**Rationale**: Extreme volatility often means strategies won't work as expected

**Example**:
- Normal BTC daily volatility: 2% (1 sigma)
- 3-sigma event: 6% daily move
- If BTC moves 7% in a day, circuit breaker triggers
- Historical examples: COVID crash, FTX collapse, etc.

**Calculation**:
```python
def calculate_volatility_zscore(pair: str, window: int = 30) -> float:
    """Calculate Z-score of current volatility vs historical"""
    returns = get_daily_returns(pair, days=window)
    current_volatility = returns.std()
    
    historical_volatility = get_daily_returns(pair, days=365).std()
    historical_mean_vol = get_rolling_volatility(pair, days=365, window=30).mean()
    historical_std_vol = get_rolling_volatility(pair, days=365, window=30).std()
    
    z_score = (current_volatility - historical_mean_vol) / historical_std_vol
    return z_score
```

---

### 4. Latency Threshold (500ms)
**Purpose**: Ensure timely execution  
**Trigger**: If order execution takes >500ms  
**Action**: Log warning, potentially pause if persistent  
**Rationale**: High latency = missed entries, worse fills, adverse selection

**Example**:
- LIQUIDITY SWEEP signal detected at price $50,000
- Order sent to exchange
- Execution takes 600ms (circuit breaker triggered)
- Price now $50,050 (missed the sweep reversal)
- Result: Worse entry or no entry

**Measurement**:
```python
start_time = time.time()
order = exchange.create_order(...)
execution_time_ms = (time.time() - start_time) * 1000

if execution_time_ms > 500:
    logger.warning(f"High latency: {execution_time_ms}ms")
```

---

### 5. Max Adverse Selection (0.6)
**Purpose**: Detect edge degradation or front-running  
**Trigger**: If 60%+ of trades move against you immediately  
**Action**: Move configuration to DECAY status  
**Rationale**: High adverse selection means you're being exploited

**Example**:
- Configuration enters at $50,000
- 1 minute later, price is at $49,950 (moved against you)
- This happens on 7 out of 10 trades (70% adverse selection)
- Circuit breaker triggers - configuration moved to DECAY

**What is Adverse Selection?**
The phenomenon where your orders consistently get filled at bad prices because market makers/HFTs know you're coming.

**Calculation**:
```python
def calculate_adverse_selection_score(trades: List[Trade]) -> float:
    """Calculate % of trades that moved against entry immediately"""
    adverse_count = 0
    
    for trade in trades:
        # Check price movement 1 minute after entry
        price_1m_later = get_price_at(trade.entry_time + timedelta(minutes=1))
        
        if trade.direction == 'LONG':
            # For long, adverse = price went down
            if price_1m_later < trade.entry_price:
                adverse_count += 1
        else:
            # For short, adverse = price went up
            if price_1m_later > trade.entry_price:
                adverse_count += 1
    
    return adverse_count / len(trades)
```

---

### 6. Consecutive Losses Limit (5)
**Purpose**: Stop runaway losses when strategy breaks  
**Trigger**: 5 consecutive losing trades  
**Action**: Pause configuration, send alert  
**Rationale**: 5 losses in a row is statistically unlikely (3% if 50% win rate)

**Example**:
- Configuration normally has 55% win rate
- Suddenly: Loss, Loss, Loss, Loss, Loss
- Probability of 5 losses at 55% WR: 0.45^5 = 1.8%
- This suggests strategy is broken or market changed
- Circuit breaker pauses trading

**Statistical Justification**:
```python
# Probability of N consecutive losses at win_rate W
def prob_n_losses(win_rate: float, n: int) -> float:
    loss_rate = 1 - win_rate
    return loss_rate ** n

# Examples:
prob_n_losses(0.50, 5) = 0.03125  # 3.1% chance
prob_n_losses(0.55, 5) = 0.0185   # 1.8% chance
prob_n_losses(0.60, 5) = 0.0102   # 1.0% chance
```

---

### 7. Regime Break Threshold (0.3)
**Purpose**: Detect market regime changes  
**Trigger**: Regime classifier confidence <30%  
**Action**: Reduce position size 50% or pause  
**Rationale**: Strategies are regime-dependent; low confidence = uncertainty

**Example**:
- Configuration trained for "Ranging" regime
- Ensemble classifier output:
  ```python
  {
    "trending": 0.28,
    "ranging": 0.32,
    "volatile": 0.40
  }
  ```
- Max confidence is 0.40 (volatile), but none are >0.50
- Circuit breaker triggers - market is in transition
- Reduce position size or pause until regime stabilizes

**When to Trigger**:
- **All regime probabilities <0.5**: Market is transitioning
- **Max probability <0.3**: Complete uncertainty
- **Rapid regime switching**: Probabilities changing daily

---

## UI Representation

### Dashboard Circuit Breaker Panel
```
┌─ Circuit Breakers ────────────────────────────────────────┐
│ Status: ✅ All Systems Normal                              │
│                                                            │
│ Daily Loss:           -0.8% / 2.0% max    ▓▓▓▓░░░░░░ 40%  │
│ Correlation:           0.45 / 0.80 max    ▓▓▓▓▓░░░░░ 56%  │
│ Market Volatility:     1.2σ / 3.0σ max    ▓▓░░░░░░░░ 40%  │
│ Execution Latency:   280ms / 500ms max    ▓▓▓▓▓░░░░░ 56%  │
│ Adverse Selection:    0.35 / 0.60 max     ▓▓▓▓▓░░░░░ 58%  │
│ Consecutive Losses:      2 / 5 max        ▓▓░░░░░░░░ 40%  │
│ Regime Confidence:    0.75 / 0.30 min     ✅ Healthy      │
└────────────────────────────────────────────────────────────┘
```

### Alert When Triggered
```
┌─ ⚠️ CIRCUIT BREAKER TRIGGERED ─────────────────────────────┐
│                                                             │
│ Configuration: LIQUIDITY_SWEEP_BTC-USDT_BINANCE_5m         │
│ Breaker:       MAX_DAILY_LOSS                              │
│ Threshold:     2.0%                                         │
│ Current:       -2.3%                                        │
│                                                             │
│ Action Taken:  ALL TRADING PAUSED                          │
│ Resume:        Tomorrow 00:00 UTC                           │
│                                                             │
│ [View Details] [Override (requires 2FA)] [Acknowledge]     │
└─────────────────────────────────────────────────────────────┘
```

---

## Adjustability

All circuit breakers should be adjustable per configuration or globally:

### Global Defaults
```python
# config/circuit_breakers.py
GLOBAL_CIRCUIT_BREAKERS = {
    "max_daily_loss": float(os.getenv("CIRCUIT_BREAKER_DAILY_LOSS", 0.02)),
    "max_correlation_spike": float(os.getenv("CIRCUIT_BREAKER_CORRELATION", 0.8)),
    # ... etc
}
```

### Configuration-Specific Overrides
```sql
-- Allow more aggressive settings for MATURE configs
UPDATE trained_configurations
SET circuit_breakers = jsonb_set(
    circuit_breakers,
    '{max_daily_loss}',
    '0.03'::jsonb  -- 3% for proven configs
)
WHERE lifecycle_stage = 'MATURE' AND sharpe_ratio > 2.0;
```

### UI for Adjustment
```
┌─ Configuration Settings > Circuit Breakers ────────────────┐
│                                                             │
│ ○ Use Global Defaults                                      │
│ ◉ Custom Settings (Advanced)                               │
│                                                             │
│ Max Daily Loss:         [2.0] % [Reset to Default]         │
│ Max Correlation:        [0.8]   [Reset to Default]         │
│ Unusual Market:         [3.0] σ [Reset to Default]         │
│ Latency Threshold:      [500] ms [Reset to Default]        │
│ Consecutive Losses:     [5] trades [Reset to Default]      │
│ Max Adverse Selection:  [0.6] [Reset to Default]           │
│ Regime Break:           [0.3] [Reset to Default]           │
│                                                             │
│ [Cancel] [Save Changes]                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Circuit Breakers

### Unit Tests
```python
def test_max_daily_loss_trigger():
    engine = TradingEngine()
    engine.daily_pnl = -0.025  # -2.5%
    
    assert engine.check_circuit_breakers(config) == True
    assert engine.last_breaker_triggered == 'MAX_DAILY_LOSS'

def test_consecutive_losses_trigger():
    trades = [
        Trade(pnl=-100),
        Trade(pnl=-50),
        Trade(pnl=-75),
        Trade(pnl=-200),
        Trade(pnl=-30),
    ]
    
    assert count_consecutive_losses(trades) == 5
    assert should_trigger_breaker(trades, 'consecutive_losses_limit', 5) == True
```

---

**Summary**: These circuit breaker defaults are conservative but reasonable for live trading. They can be adjusted based on:
1. Configuration maturity (MATURE configs get more leeway)
2. Market conditions (bull market vs bear market)
3. Strategy type (high-frequency vs swing trading)
4. User risk tolerance (conservative vs aggressive)
