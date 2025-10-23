# V2 Training Schema Mapping

**Date**: October 23, 2025  
**Status**: ✅ Implemented

## Problem Statement

The V2 Training system was attempting to write to a `trained_configurations` table with a simple 16-column schema, but the production database had a comprehensive 70+ column schema designed for the production trading system with lifecycle management, regime classification, and advanced metrics.

## Solution: Schema Adaptation

Rather than dropping the existing comprehensive schema, we **adapted the V2 Training code to map its results to the existing production schema**.

---

## Existing Schema Purpose

The `trained_configurations` table supports a **production trading system with lifecycle management**:

### Key Features:
1. **Lifecycle Management**
   - Tracks configurations through stages: DISCOVERY → VALIDATION → MATURE → DECAY → PAPER
   - Each stage determines risk allocation and position sizing
   - MATURE configs get 10% max allocation, DISCOVERY gets 2%

2. **Regime Classification**
   - Stores market regime (bull, bear, sideways, volatile)
   - Enables regime-specific strategy selection
   - Future: Ensemble model predictions stored in JSONB

3. **Comprehensive Metrics** (70+ columns)
   - Performance: net_profit, gross_win_rate, avg_win, avg_loss, sample_size
   - Statistical: sharpe_ratio, calmar_ratio, sortino_ratio, p_value, z_score
   - Execution: fill_rate, slippage, time_to_fill, adverse_selection
   - Risk: kelly_fraction, var_95, cvar_95, max_position_size
   - Microstructure: book_depth, spread, maker_rebate, tick_impact
   - Health: performance_degradation, death_signals, resurrection_score

4. **Production Ready**
   - Activation flags (`is_active`)
   - Metadata tracking (model_version, discovery_date, engine_hash)
   - Timestamps (created_at, updated_at, activated_at, deactivated_at)

---

## V2 Training Output

Our training system produces:

```python
BacktestResult:
    - trades: List[Trade]
    - metrics: {
        'total_trades': int,
        'gross_win_rate': float,  # percentage
        'net_profit_pct': float,
        'sharpe_ratio': float,
        'avg_win_pct': float,
        'avg_loss_pct': float,
        'max_drawdown_pct': float,
        'calmar_ratio': float,
        'sortino_ratio': float,
        ...
    }
    - equity_curve: DataFrame
    - parameters: Dict[str, Any]

ValidationResult (optional):
    - stability_score: float
    - overfitting_detected: bool
    - aggregate_metrics: Dict
    - overfitting_reasons: List[str]
```

---

## Mapping Strategy

### Core Mapping (What We Have)

| V2 Training Output | Production Schema Column | Conversion |
|-------------------|--------------------------|------------|
| `strategy` | `strategy_name` | Direct |
| `symbol` (e.g., "BTC/USDT") | `pair` | Direct |
| `exchange` | `exchange` | Direct |
| `timeframe` | `timeframe` | Direct |
| `lifecycle_stage` (calculated) | `status` | Direct |
| `parameters` | `parameters_json` | JSON.dumps() |
| `metrics['gross_win_rate']` | `gross_win_rate` | /100 (% to decimal) |
| `metrics['avg_win_pct']` | `avg_win` | Direct |
| `metrics['avg_loss_pct']` | `avg_loss` | Direct |
| `metrics['net_profit_pct']` | `net_profit` | Direct |
| `metrics['total_trades']` | `sample_size` | Direct |
| `metrics['sharpe_ratio']` | `sharpe_ratio` | Direct |
| `metrics['calmar_ratio']` | `calmar_ratio` | Direct |
| `metrics['sortino_ratio']` | `sortino_ratio` | Direct |

### Default Values (What We Don't Have Yet)

| Production Column | Default Value | Future Enhancement |
|------------------|---------------|-------------------|
| `regime` | `'sideways'` | Implement regime detection |
| `is_active` | `false` | Manual activation via UI |
| `fill_rate` | `NULL` | Requires live trading data |
| `slippage_vs_mid_bps` | `NULL` | Requires order book data |
| `regime_classification` | `NULL` | Implement ensemble models |
| `kelly_fraction` | `NULL` | Implement Kelly criterion |
| `var_95`, `cvar_95` | `NULL` | Implement VaR calculation |
| `death_signals` | `NULL` | Implement pattern decay detection |

### Lifecycle Stage Assignment

Automatically determined during training:

```python
def _determine_lifecycle_stage(metrics, validation_result):
    """
    PAPER: net_profit < 0 OR sharpe < 0.5 OR overfitting detected
    DISCOVERY: total_trades < 30 (untested)
    MATURE: total_trades >= 100 AND sharpe >= 1.5 AND validated
    VALIDATION: Passed validation, not yet mature
    """
```

---

## Code Changes

### 1. Configuration Writer (`training/configuration_writer.py`)

**Before**: Attempted to insert 16 columns with custom schema
```python
INSERT INTO trained_configurations (
    config_id, strategy, symbol, exchange, timeframe,
    lifecycle_stage, confidence_score, parameters, metrics,
    config_json, created_at, updated_at, ...
)
```

**After**: Maps to existing 70+ column schema
```python
INSERT INTO trained_configurations (
    strategy_name, exchange, pair, timeframe, regime,
    status, is_active, parameters_json,
    gross_win_rate, avg_win, avg_loss, net_profit, sample_size,
    sharpe_ratio, calmar_ratio, sortino_ratio,
    created_at, updated_at
)
```

### 2. Systemd Service (`ops/systemd/dashboard.service`)

**Added process cleanup settings** to prevent orphaned background tasks:

```ini
# Process cleanup settings
KillMode=mixed         # Kill main process + children
KillSignal=SIGTERM     # Graceful shutdown first
TimeoutStopSec=30s     # Wait 30s before SIGKILL
SendSIGKILL=yes        # Force kill if needed
RestartSec=5s          # Wait 5s between restarts
```

**Why this matters**: Training runs as FastAPI BackgroundTasks. When the service crashes/restarts, these become orphaned processes that hold port 8000.

---

## Testing & Verification

### 1. Start a Training Job

```bash
curl -X POST http://138.68.245.159:8000/api/v2/training/start \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "LIQUIDITY_SWEEP",
    "symbol": "BTC/USDT",
    "exchange": "binanceus",
    "timeframe": "5m",
    "optimizer": "bayesian",
    "lookback_days": 30,
    "n_iterations": 20,
    "run_validation": true
  }'
```

### 2. Monitor Progress

```bash
JOB_ID="<from above>"
curl http://138.68.245.159:8000/api/v2/training/jobs/$JOB_ID/progress
```

### 3. Check Database

```sql
SELECT 
    id, 
    strategy_name, 
    pair, 
    timeframe,
    status,  -- lifecycle stage
    sharpe_ratio,
    net_profit,
    sample_size,
    created_at
FROM trained_configurations
ORDER BY created_at DESC
LIMIT 5;
```

### 4. Verify No Orphaned Processes

```bash
ssh root@138.68.245.159 "ps aux | grep uvicorn | grep -v grep"
# Should show only 1 process
```

---

## Future Enhancements

### Phase 1: Enhanced Metrics (Easy)
- [ ] Calculate VaR/CVaR from equity curve
- [ ] Implement Kelly criterion for position sizing
- [ ] Extract execution metrics from backtests (fees paid, slippage estimated)

### Phase 2: Regime Detection (Medium)
- [ ] Implement market regime classifier (bull/bear/sideways/volatile)
- [ ] Train ensemble model for regime probability
- [ ] Store regime classification in JSONB field

### Phase 3: Live Trading Integration (Hard)
- [ ] Track actual fill rates from live orders
- [ ] Measure real slippage vs mid-price
- [ ] Monitor adverse selection (post-trade drift)
- [ ] Implement pattern decay detection (death signals)

### Phase 4: Portfolio Optimization (Hard)
- [ ] Correlation-adjusted position sizing
- [ ] Multi-asset portfolio balancing
- [ ] Dynamic regime-based allocation

---

## Schema Reference

Full schema available in: `sql/migrations/004_create_trained_configurations.sql`

Key constraints:
- `UNIQUE (strategy_name, exchange, pair, timeframe, regime)` - Prevents duplicate configs
- `CHECK (status IN ('DISCOVERY', 'VALIDATION', 'MATURE', 'DECAY', 'PAPER'))` - Valid lifecycle stages
- `CHECK (regime IN ('bull', 'bear', 'sideways', 'volatile'))` - Valid regimes
- `CHECK (timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d'))` - Valid timeframes

---

## Troubleshooting

### Issue: "column config_id does not exist"
**Cause**: Code trying to use old schema  
**Fix**: ✅ Resolved - Code now maps to existing schema

### Issue: "Object of type int64 is not JSON serializable"
**Cause**: Numpy types in parameters/metrics  
**Fix**: ✅ Resolved - Added `convert_numpy_types()` helper

### Issue: Orphaned uvicorn processes holding port 8000
**Cause**: Systemd not killing background tasks on restart  
**Fix**: ✅ Resolved - Added `KillMode=mixed` and proper cleanup settings

### Issue: Training stuck at 95% (Saving Configuration)
**Cause**: Database schema mismatch or serialization errors  
**Fix**: ✅ Resolved - Proper schema mapping + numpy type conversion

---

## Related Documentation

- [V2 Portfolio Management](./V2_PORTFOLIO_MANAGEMENT.md) - How configs are used for position sizing
- [Training Progress API](./training_progress_api.md) - Progress tracking implementation
- [Existing Infrastructure Analysis](./EXISTING_TRAINING_INFRASTRUCTURE_ANALYSIS.md) - Historical context
- [Circuit Breaker Guide](./CIRCUIT_BREAKER_GUIDE.md) - Risk management using trained configs

---

**Last Updated**: October 23, 2025  
**Status**: Production Ready ✅
