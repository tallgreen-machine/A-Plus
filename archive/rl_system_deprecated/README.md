# Deprecated RL System Archive

**Date Archived**: 2025-10-23  
**Reason**: Replaced by V2 rule-based parameter optimization system

---

## Archived Components

### 1. `policy/` Directory
**Purpose**: Reinforcement Learning training system using Stable-Baselines3 PPO

**Files Archived**:
- `train_strategy_aware.py` - PPO training script
- `trading_env.py` - Gymnasium environment for RL
- `pattern_library.py` - Pattern registry
- `reliability_engine.py` - Backtest result tracking
- `trader.py` - RL agent executor
- `callbacks.py` - Training callbacks
- `validate.py` - Model evaluation
- `run_trader.py` - Execution script

**Technology**: Stable-Baselines3, Gymnasium, TensorBoard

**Why Deprecated**: 
- Black box decision making (neural network)
- Long training times (hours)
- Difficult to interpret and debug
- Incompatible with V2 UI expectations

---

### 2. `ml/` Directory
**Purpose**: ML-based pattern recognition and trained asset management

**Files Archived**:
- `trained_assets_manager.py` (1784 lines) - Asset-specific model management
- `strategy_ml_engine.py` (304 lines) - Pattern ML training
- `real_training_runner.py` (248 lines) - Training orchestration
- `enhanced_strategy_library.py` - Enhanced strategy definitions
- `strategy_recognizer.py` - Pattern recognition
- `trained_asset_strategy_manager.py` - Strategy execution
- `trained_assets/*.pkl` - Trained model files
- `README.md` - ML system documentation

**Why Deprecated**:
- Pattern-based approach (not parameter-based)
- Stores models as .pkl files (not database configurations)
- Simple correlation-based optimization (not rigorous backtesting)
- Different architecture from V2 design

---

## Database Tables (Preserved)

These tables remain in the database for historical reference:

```sql
-- RL training results
pattern_training_results

-- Strategy training results
strategy_training_results

-- Backtest results from reliability engine
backtest_results
```

**Note**: These tables are not used by V2 system but preserved for data archaeology.

---

## API Endpoints (Deprecated)

The following endpoints in `api/training.py` were RL-specific:

- `/api/training/system-status` - Now updated for V2
- `/api/training/trained-assets` - RL model listing (removed)
- `/api/training/market-regimes` - RL regime detection (removed)
- `/api/training/start-multi-dimensional` - RL training job (removed)
- `/api/training/strategy-parameters/{symbol}/{exchange}/{strategy_id}` - RL params (removed)

**Action Required**: Clean up `api/training.py` to remove RL imports and endpoints.

---

## Migration Notes

### What Replaced This System

**V2 Parameter Optimization System**:
- Location: `training/` directory
- Purpose: Rule-based strategy parameter tuning
- Technology: Grid/Random/Bayesian search, scikit-optimize
- Storage: `trained_configurations` table (PostgreSQL)
- Output: JSON configuration files with transparent parameters

**Key Differences**:

| Aspect | RL System (Archived) | V2 System (Active) |
|--------|---------------------|-------------------|
| Approach | Neural network training | Parameter space search |
| Training | Hours (PPO episodes) | Minutes (backtest iterations) |
| Output | .pkl model files | Database configurations |
| Interpretability | Black box | Fully transparent |
| Decision | Portfolio weights | Entry/exit signals |
| UI Integration | None | Full V2 UI support |

---

### If You Need to Restore

**Warning**: Not recommended. V2 architecture is incompatible.

If absolutely necessary:
```bash
# Restore directories
cp -r archive/rl_system_deprecated/policy/ .
cp -r archive/rl_system_deprecated/ml/ .

# Reinstall dependencies
pip install stable-baselines3 gymnasium

# Database tables already exist (preserved)
```

---

## References

- **V2 Architecture**: `docs/V2_PORTFOLIO_MANAGEMENT.md`
- **Training Implementation**: `docs/TRAINING_IMPLEMENTATION_PLAN.md`
- **Gap Analysis**: `docs/EXISTING_TRAINING_INFRASTRUCTURE_ANALYSIS.md`
- **Data Strategy**: `docs/TRAINING_DATA_STRATEGY.md`

---

## Next Steps

1. ✅ Archive complete
2. ⏳ Build V2 training system (`training/` directory)
3. ⏳ Implement rule-based portfolio management
4. ⏳ Deploy and monitor

**V2 is the future** - RL system remains archived for historical reference only.
