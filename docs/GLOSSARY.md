# TradePulse IQ - Trading System Glossary

**Version**: 1.0  
**Last Updated**: October 22, 2025

This document defines the core terminology used throughout the TradePulse IQ trading system to ensure consistency and clarity across code, documentation, and team communication.

---

## 🏗️ System Architecture Terminology

### Core Trading Concepts (Hierarchical Order)

#### 1. **Strategy**
The highest-level trading approach or alpha-generation technique. A strategy defines the overall logic, rules, and conditions for identifying trading opportunities.

**Examples:**
- Liquidity Sweep V3
- HTF Sweep (Higher Timeframe Sweep)
- Volume Breakout
- Divergence Capitulation

**Key Characteristics:**
- Contains the core pattern recognition logic
- Defines entry/exit rules
- Specifies risk management approach
- Can be optimized through machine learning

**In Code:**
- Database table: `strategies`
- API endpoints: `/api/strategies/*`
- File naming: `htf_sweep.py`, `volume_breakout.py`

---

#### 2. **Configuration**
A specific trained instance of a strategy, optimized for particular market conditions. Each configuration represents a unique combination of context parameters that have been tested and validated.

**Definition Formula:**
```
Configuration = Strategy + Exchange + Pair + Timeframe + Regime + Optimized Parameters
```

**Example:**
```
Configuration ID: uuid-1234-5678
Strategy: Liquidity Sweep V3
Exchange: Binance
Pair: BTC/USDT
Timeframe: 1h
Regime: Bull Market
Status: MATURE
Optimized Parameters: {pierce_depth: 0.15%, rejection_candles: 3, ...}
```

**Key Characteristics:**
- Uniquely identified by UUID
- Has a lifecycle status (DISCOVERY, VALIDATION, MATURE, DECAY, PAPER)
- Contains optimized variable parameters
- Tracked with performance metrics
- Can be activated/deactivated for trading

**In Code:**
- Database table: `trained_configurations`
- API endpoints: `/api/training/configurations/*`
- JSON structure: See "Universal Discovery Template" below

---

#### 3. **Variable**
An optimization dimension within a strategy. Variables are the specific parameters that can be tuned through backtesting and machine learning to improve strategy performance.

**Examples (from Liquidity Sweep V3):**
- `pierce_depth` - How deep price penetrates a key level
- `rejection_candles` - Number of candles showing rejection
- `volume_spike_threshold` - Volume increase multiplier
- `reversal_candle_size` - Size of reversal candle in ATR
- `key_level_lookback` - Historical period for identifying levels
- `stop_distance` - Stop loss distance in ATR
- `target_multiple` - Risk/reward ratio
- `min_stop_density_score` - Liquidity density threshold
- `max_spread_tolerance` - Maximum acceptable spread

**Key Characteristics:**
- Each variable has a testable range
- Variables are strategy-specific
- Optimization creates best-fit parameter values
- Stored in `parameters_json` JSONB column

**In Code:**
- Defined in strategy classes
- Ranges defined in training configuration
- Values stored in `strategy_parameters` table and `trained_configurations.parameters_json`

---

#### 4. **Parameter**
The specific value(s) assigned to a variable. Parameters can be single values (for deployed configurations) or ranges (during optimization/testing).

**Contexts:**

**A. Testing/Optimization Phase:**
```python
# Variable with parameter range
pierce_depth: {
    "min": 0.05,    # Start of test range
    "max": 0.5,     # End of test range
    "step": 0.05    # Increment
}
```

**B. Deployed Configuration:**
```python
# Variable with optimal parameter value
pierce_depth: 0.15  # Discovered optimal value
```

**Key Characteristics:**
- Concrete values or ranges
- Result from optimization process
- Stored with configuration
- Can be adjusted based on regime changes

**In Code:**
- Stored in `parameters_json` JSONB field
- Accessed via configuration objects
- Used by strategy execution logic

---

## 🔄 Configuration Lifecycle

### Status Definitions

| Status | Description | Criteria | Position Size | Priority |
|--------|-------------|----------|---------------|----------|
| **DISCOVERY** | Newly found configuration, initial testing | sample < 30 | 0.25x | Low |
| **VALIDATION** | Under evaluation, building statistical confidence | sample 30-100, p_value < 0.05 | 0.5x | Medium |
| **MATURE** | Proven configuration, full deployment | sample > 100, sharpe > 1.5 | 1.0x | High |
| **DECAY** | Performance degrading, reduced allocation | degradation > -20% OR death signals | 0.25x | Low |
| **PAPER** | Non-trading, monitoring only | NET_PROFIT < 0 OR sharpe < 0.5 | 0x | None |

### Lifecycle Transitions

```
DISCOVERY → VALIDATION → MATURE → DECAY → PAPER
     ↓          ↓           ↓        ↓        ↓
   PAPER ←─────────────────────────────────←──┘
     ↓
 DISCOVERY (resurrection if conditions improve)
```

---

## 📊 Performance Metrics Terminology

### Core Metrics

- **NET_PROFIT**: Total profit after fees and slippage
- **Gross Win Rate (gross_WR)**: Percentage of winning trades before costs
- **Sharpe Ratio**: Risk-adjusted return metric
- **Calmar Ratio**: Return vs maximum drawdown
- **Sortino Ratio**: Downside risk-adjusted return
- **Fill Rate**: Percentage of orders successfully filled
- **Adverse Selection Score**: Measure of toxic order flow
- **Slippage**: Difference between expected and actual execution price

### Statistical Validation

- **p_value**: Statistical significance of results (< 0.05 = significant)
- **z_score**: Standard deviations from mean
- **Monte Carlo VaR**: Value at Risk from simulation
- **Stability Score**: Consistency of performance over time
- **Trade Clustering**: Measure of independence between trades

---

## 🎯 Market Context Terminology

### Regimes

- **Bull Market**: Upward trending, risk-on environment
- **Bear Market**: Downward trending, risk-off environment
- **Sideways/Ranging**: Consolidation, no clear trend
- **Volatile**: High variance, unstable conditions

### Timeframes

Standard timeframes used across the system:
- **1m**: 1-minute candles
- **5m**: 5-minute candles
- **15m**: 15-minute candles
- **1h**: 1-hour candles
- **4h**: 4-hour candles
- **1d**: Daily candles

---

## 🔧 Technical Implementation Terms

### Database

- **strategies**: Table storing strategy definitions
- **strategy_parameters**: Strategy-specific parameter configurations
- **strategy_performance**: Historical performance tracking
- **trained_configurations**: Optimized configuration instances
- **trades**: Individual trade records
- **active_trades**: Currently open positions

### API Structure

- `/api/strategies/*` - Strategy management and performance
- `/api/training/configurations/*` - Configuration CRUD and activation
- `/api/portfolio/*` - Portfolio and equity tracking
- `/api/trades/*` - Trade execution and history
- `/api/exchanges/*` - Exchange connection management
- `/api/analytics/*` - Market analysis and insights

### File Naming Conventions

✅ **Correct:**
- `htf_sweep.py` (strategy implementation)
- `strategy_performance.py` (performance tracking)
- `trained_configurations.sql` (database schema)

❌ **Incorrect (deprecated):**
- `htf_pattern.py`
- `pattern_performance.py`
- `trained_patterns.sql`

---

## 📝 Universal Discovery Template

When configurations are discovered through optimization, they follow this JSON structure:

```json
{
  "pair": "BTC/USDT",
  "strategy": "LIQUIDITY SWEEP V3",
  "configurations": [
    {
      "id": "uuid-generated",
      "status": "DISCOVERY|VALIDATION|MATURE|DECAY|PAPER",
      "metadata": {
        "model_version": "v3.1.0",
        "discovery_date": "2025-10-22T12:00:00Z",
        "engine_hash": "abc123def456",
        "runtime_env": "production"
      },
      "context": {
        "pair": "BTC/USDT",
        "exchange": "Binance",
        "timeframe": "1h"
      },
      "parameters": {
        "pierce_depth": 0.15,
        "rejection_candles": 3,
        "volume_spike_threshold": 2.5,
        "reversal_candle_size": 1.2,
        "key_level_lookback": 100,
        "stop_distance": 1.0,
        "target_multiple": 2.5,
        "min_stop_density_score": 0.7,
        "max_spread_tolerance": 5
      },
      "performance": {
        "gross_WR": 0.65,
        "avg_win": 150.0,
        "avg_loss": -75.0,
        "NET_PROFIT": 2500.0,
        "sample_size": 120
      },
      "statistical_validation": {
        "sharpe_ratio": 1.8,
        "p_value": 0.02,
        "stability_score": 0.85
      }
    }
  ]
}
```

---

## 🚫 Deprecated Terminology

The following terms are **NO LONGER USED** in the codebase:

| ❌ Deprecated | ✅ Use Instead |
|--------------|---------------|
| pattern | strategy |
| pattern_performance | strategy_performance |
| trained_patterns | trained_configurations |
| pattern_parameters | strategy_parameters |
| PatternStatus | StrategyStatus |

---

## 💡 Usage Examples

### Code Example: Loading a Configuration

```python
# Load a specific configuration
config = db.get_trained_configuration(config_id="uuid-1234")

# Access configuration properties
strategy_name = config["context"]["strategy"]  # "LIQUIDITY SWEEP V3"
exchange = config["context"]["exchange"]        # "Binance"
pair = config["context"]["pair"]               # "BTC/USDT"
timeframe = config["context"]["timeframe"]     # "1h"

# Access optimized parameters (variables with values)
pierce_depth = config["parameters"]["pierce_depth"]  # 0.15
rejection_candles = config["parameters"]["rejection_candles"]  # 3

# Check lifecycle status
if config["status"] == "MATURE":
    position_size = base_size * 1.0  # Full allocation
elif config["status"] == "VALIDATION":
    position_size = base_size * 0.5  # Half allocation
```

### API Example: Querying Configurations

```bash
# Get all configurations for a strategy
GET /api/training/configurations?strategy=LIQUIDITY_SWEEP_V3

# Get configurations for specific context
GET /api/training/configurations?exchange=Binance&pair=BTC/USDT&timeframe=1h

# Activate a configuration for trading
POST /api/training/configurations/activate
{
  "configuration_id": "uuid-1234"
}
```

---

## 🔄 Version History

- **v1.0** (2025-10-22): Initial glossary creation
  - Defined 4-tier hierarchy: Strategy → Configuration → Variable → Parameter
  - Documented lifecycle stages and transitions
  - Standardized terminology across codebase
  - Deprecated "pattern" terminology

---

## 📚 Related Documentation

- [README.md](./README.md) - System overview and architecture
- [SCHEMA_MANAGEMENT.md](./docs/SCHEMA_MANAGEMENT.md) - Database schema guide
- [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) - Production deployment
- [V2_MIGRATION.md](./docs/V2_MIGRATION.md) - V2 dashboard migration guide

---

**Questions or suggestions?** Update this glossary as the system evolves to maintain clarity and consistency.
