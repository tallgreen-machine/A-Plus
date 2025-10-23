# V2 Portfolio Management Architecture

**Date**: 2025-10-23  
**Purpose**: Portfolio management strategy using trained configurations (NO RL system)

---

## Executive Summary

The **V2 architecture** manages portfolios using **rule-based trained configurations** from the Strategy Studio, NOT reinforcement learning. This document clarifies the complete portfolio management strategy.

---

## Portfolio Management Without RL

### Core Concept

Each **trained configuration** acts as an independent signal generator. The portfolio manager:

1. **Monitors** all active configurations
2. **Executes** signals when conditions are met
3. **Manages** position sizing based on configuration confidence
4. **Tracks** performance per configuration

**No machine learning model** is needed for allocation decisions.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    V2 Portfolio Manager                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Active Configurations (from DB)              │  │
│  │  • Config 1: BTC/USDT Liquidity Sweep (MATURE)       │  │
│  │  • Config 2: ETH/USDT Capitulation (VALIDATION)      │  │
│  │  • Config 3: SOL/USDT Liquidity Sweep (MATURE)       │  │
│  │  • Config 4: BNB/USDT Failed Breakdown (DISCOVERY)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Signal Generation Loop                     │  │
│  │  For each active config:                             │  │
│  │    1. Fetch latest market data                       │  │
│  │    2. Run strategy logic with trained parameters     │  │
│  │    3. Generate signal (BUY/SELL/HOLD)                │  │
│  │    4. Calculate position size based on confidence    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Risk Management Layer                      │  │
│  │  • Check available capital                           │  │
│  │  • Apply position limits per asset                   │  │
│  │  • Apply lifecycle stage multipliers                 │  │
│  │  • Enforce circuit breakers                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Execution Engine                           │  │
│  │  • Submit orders to exchange                         │  │
│  │  • Track open positions                              │  │
│  │  • Monitor stop-loss / take-profit                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Position Sizing Strategy

### Lifecycle-Based Allocation

Each configuration has a **lifecycle stage** that determines risk allocation:

| Lifecycle Stage | Base Allocation | Max Per Position | Rationale |
|----------------|-----------------|------------------|-----------|
| **MATURE** | 5-10% | 10% | Proven performance, high confidence |
| **VALIDATION** | 2-5% | 5% | Promising but needs more proof |
| **DISCOVERY** | 0.5-2% | 2% | New discovery, experimental |
| **PAPER** | 0% | 0% | Paper trading only, no real capital |
| **DECAY** | 1-3% | 3% | Degrading performance, reduce exposure |

### Dynamic Position Sizing Formula

```python
def calculate_position_size(config, available_capital, current_signal):
    """
    Calculate position size based on configuration confidence
    """
    
    # Base allocation by lifecycle stage
    stage_multipliers = {
        'MATURE': 0.10,      # 10% of portfolio
        'VALIDATION': 0.05,  # 5% of portfolio
        'DISCOVERY': 0.02,   # 2% of portfolio
        'DECAY': 0.03,       # 3% of portfolio
        'PAPER': 0.00        # 0% (paper only)
    }
    
    base_allocation = stage_multipliers[config.lifecycle_stage]
    
    # Confidence adjustment (based on recent performance)
    sharpe_multiplier = min(config.validation.sharpe_ratio / 2.0, 1.5)
    win_rate_multiplier = config.performance.gross_win_rate / 100.0
    
    confidence_factor = (sharpe_multiplier * 0.6) + (win_rate_multiplier * 0.4)
    confidence_factor = max(0.5, min(confidence_factor, 1.5))  # Clamp 0.5-1.5x
    
    # Signal strength adjustment (from strategy logic)
    signal_strength = current_signal.confidence  # 0.0 - 1.0
    
    # Calculate final position size
    position_size = (
        available_capital * 
        base_allocation * 
        confidence_factor * 
        signal_strength
    )
    
    # Apply max position limit
    max_position = available_capital * stage_multipliers[config.lifecycle_stage]
    position_size = min(position_size, max_position)
    
    return position_size
```

---

## Multi-Asset Portfolio Balance

### Scenario: 4 Active Configurations

**Portfolio**: $100,000 USDT

| Config | Pair | Stage | Sharpe | Win Rate | Signal | Position Size |
|--------|------|-------|--------|----------|--------|---------------|
| Config 1 | BTC/USDT | MATURE | 2.1 | 68% | BUY (0.9) | $9,450 |
| Config 2 | ETH/USDT | VALIDATION | 1.4 | 62% | BUY (0.7) | $3,220 |
| Config 3 | SOL/USDT | MATURE | 1.8 | 65% | HOLD | $0 |
| Config 4 | BNB/USDT | DISCOVERY | 0.8 | 55% | BUY (0.6) | $660 |
| **Total** | | | | | | **$13,330** |

**Capital Allocation**:
- Active positions: $13,330 (13.3%)
- Available cash: $86,670 (86.7%)

**Risk Management**:
- No single position > 10% of portfolio ✅
- Total exposure < 50% of portfolio ✅
- MATURE configs get largest allocations ✅

---

## Portfolio Manager Implementation

### Core Class Structure

```python
# core/portfolio_manager.py

from typing import List, Dict, Optional
from dataclasses import dataclass
from decimal import Decimal
import time

from shared.db import get_db_conn
from training.strategies.liquidity_sweep import LiquiditySweepStrategy
from training.strategies.capitulation_reversal import CapitulationReversalStrategy
# ... other strategies

@dataclass
class Signal:
    """Trading signal from a strategy"""
    config_id: int
    pair: str
    direction: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 - 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: int


class PortfolioManager:
    """
    V2 Portfolio Manager
    
    Manages portfolio using rule-based trained configurations.
    NO reinforcement learning - uses configuration parameters directly.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db_conn = get_db_conn()
        
        # Load active configurations
        self.active_configs = self._load_active_configs()
        
        # Initialize strategy instances
        self.strategies = self._initialize_strategies()
        
        # Risk management
        self.max_portfolio_exposure = 0.50  # 50% max allocation
        self.max_position_per_asset = {
            'MATURE': 0.10,      # 10%
            'VALIDATION': 0.05,  # 5%
            'DISCOVERY': 0.02,   # 2%
            'DECAY': 0.03,       # 3%
            'PAPER': 0.00        # 0%
        }
    
    def _load_active_configs(self) -> List[Dict]:
        """Load active configurations from database"""
        query = """
            SELECT * FROM trained_configurations 
            WHERE is_active = TRUE 
              AND lifecycle_stage != 'PAPER'
            ORDER BY lifecycle_stage, validation.sharpe_ratio DESC
        """
        
        with self.db_conn.cursor() as cur:
            cur.execute(query)
            configs = cur.fetchall()
        
        return configs
    
    def _initialize_strategies(self) -> Dict[int, object]:
        """Instantiate strategy objects from configurations"""
        strategies = {}
        
        for config in self.active_configs:
            # Determine strategy class based on strategy_name
            if 'Liquidity Sweep' in config['strategy_name']:
                strategy = LiquiditySweepStrategy(config['parameters'])
            elif 'Capitulation' in config['strategy_name']:
                strategy = CapitulationReversalStrategy(config['parameters'])
            # ... other strategies
            
            strategies[config['id']] = strategy
        
        return strategies
    
    def run_trading_cycle(self):
        """
        Main trading loop - called every N minutes
        
        1. Check each active configuration for signals
        2. Calculate position sizes
        3. Execute trades
        """
        
        print(f"\n{'='*60}")
        print(f"Trading Cycle: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # Get current portfolio state
        portfolio = self._get_portfolio_state()
        available_capital = portfolio['available_capital']
        
        # Generate signals from all active configs
        signals = []
        for config in self.active_configs:
            signal = self._check_configuration_signal(config)
            if signal and signal.direction != 'HOLD':
                signals.append(signal)
        
        print(f"📊 Generated {len(signals)} signals\n")
        
        # Calculate position sizes with risk management
        sized_signals = []
        for signal in signals:
            position_size = self._calculate_position_size(
                signal, 
                available_capital, 
                portfolio
            )
            
            if position_size > 0:
                signal.position_size = position_size
                sized_signals.append(signal)
        
        # Execute signals
        for signal in sized_signals:
            self._execute_signal(signal, portfolio)
        
        # Check existing positions for exits
        self._check_exit_conditions(portfolio)
    
    def _check_configuration_signal(self, config: Dict) -> Optional[Signal]:
        """
        Run strategy logic for a configuration
        
        Returns Signal object or None
        """
        
        # Get strategy instance
        strategy = self.strategies[config['id']]
        
        # Fetch latest market data
        market_data = self._fetch_latest_data(
            config['pair'], 
            config['exchange'], 
            config['timeframe']
        )
        
        # Run strategy logic
        signal = strategy.check_signal(market_data)
        
        if signal:
            print(f"✅ Signal: {config['pair']} - {signal.direction} "
                  f"(confidence: {signal.confidence:.2f})")
        
        return signal
    
    def _calculate_position_size(
        self, 
        signal: Signal, 
        available_capital: float,
        portfolio: Dict
    ) -> float:
        """
        Calculate position size based on:
        1. Lifecycle stage
        2. Configuration confidence (Sharpe, win rate)
        3. Signal strength
        4. Risk limits
        """
        
        # Get configuration
        config = next(c for c in self.active_configs if c['id'] == signal.config_id)
        
        # Base allocation by lifecycle stage
        base_allocation = self.max_position_per_asset[config['lifecycle_stage']]
        
        # Confidence adjustment
        sharpe_multiplier = min(config['validation']['sharpe_ratio'] / 2.0, 1.5)
        win_rate_multiplier = config['performance']['gross_win_rate'] / 100.0
        
        confidence_factor = (sharpe_multiplier * 0.6) + (win_rate_multiplier * 0.4)
        confidence_factor = max(0.5, min(confidence_factor, 1.5))
        
        # Signal strength
        signal_strength = signal.confidence
        
        # Calculate position size
        position_size = (
            available_capital * 
            base_allocation * 
            confidence_factor * 
            signal_strength
        )
        
        # Apply maximum position limit
        max_position = available_capital * base_allocation
        position_size = min(position_size, max_position)
        
        # Check total portfolio exposure
        current_exposure = portfolio['total_exposure'] / portfolio['total_value']
        if current_exposure + (position_size / portfolio['total_value']) > self.max_portfolio_exposure:
            # Reduce position to stay under limit
            position_size = (self.max_portfolio_exposure - current_exposure) * portfolio['total_value']
        
        print(f"  💰 Position size: ${position_size:,.2f} "
              f"({100 * position_size / available_capital:.1f}% of capital)")
        
        return max(0, position_size)
    
    def _execute_signal(self, signal: Signal, portfolio: Dict):
        """
        Execute a trading signal
        
        1. Submit order to exchange
        2. Record in database
        3. Update portfolio state
        """
        
        print(f"\n🚀 EXECUTING: {signal.direction} {signal.pair}")
        print(f"   Entry: ${signal.entry_price:,.2f}")
        print(f"   Stop Loss: ${signal.stop_loss:,.2f}")
        print(f"   Take Profit: ${signal.take_profit:,.2f}")
        print(f"   Size: ${signal.position_size:,.2f}\n")
        
        # TODO: Submit order to exchange via CCXT
        # order = exchange.create_market_order(...)
        
        # Record trade in database
        self._record_trade(signal)
    
    def _check_exit_conditions(self, portfolio: Dict):
        """
        Check existing positions for exit signals
        
        1. Stop loss hit
        2. Take profit hit
        3. Strategy exit signal
        """
        
        for position in portfolio['open_positions']:
            # Get configuration
            config = next(c for c in self.active_configs if c['id'] == position['config_id'])
            
            # Get strategy instance
            strategy = self.strategies[config['id']]
            
            # Fetch latest data
            market_data = self._fetch_latest_data(
                position['pair'],
                position['exchange'],
                config['timeframe']
            )
            
            # Check exit conditions
            should_exit = strategy.check_exit(market_data, position)
            
            if should_exit:
                self._close_position(position)
    
    def _get_portfolio_state(self) -> Dict:
        """Get current portfolio state from database"""
        # Query portfolio table, active_trades table, etc.
        # Return dict with available_capital, total_value, open_positions
        pass
    
    def _fetch_latest_data(self, pair: str, exchange: str, timeframe: str):
        """Fetch latest market data for signal generation"""
        # Use DataCollector to get latest candles
        pass
    
    def _record_trade(self, signal: Signal):
        """Record executed trade in database"""
        # Insert into trades table
        pass
    
    def _close_position(self, position: Dict):
        """Close an open position"""
        # Submit sell order
        # Update database
        pass
```

---

## Main Trading Bot Entry Point

```python
# main.py (simplified)

import time
from core.portfolio_manager import PortfolioManager
from utils.logger import log

def main():
    """
    Main trading bot loop
    
    Uses V2 architecture: rule-based configurations (NO RL)
    """
    
    log.info("🚀 Starting TradePulse V2 Trading Bot")
    
    # Initialize portfolio manager
    user_id = "user_1"  # Or from config
    portfolio_manager = PortfolioManager(user_id)
    
    log.info(f"📊 Loaded {len(portfolio_manager.active_configs)} active configurations")
    
    # Main loop
    while True:
        try:
            # Run trading cycle
            portfolio_manager.run_trading_cycle()
            
            # Sleep until next cycle (e.g., 5 minutes)
            time.sleep(300)
            
        except KeyboardInterrupt:
            log.info("🛑 Shutting down trading bot")
            break
        except Exception as e:
            log.error(f"❌ Error in trading cycle: {e}")
            time.sleep(60)  # Wait 1 minute before retry

if __name__ == "__main__":
    main()
```

---

## Risk Management Rules

### Portfolio-Level Limits

```python
# Circuit breakers from CIRCUIT_BREAKER_GUIDE.md

RISK_LIMITS = {
    # Maximum total portfolio exposure
    'max_total_exposure': 0.50,  # 50% of capital
    
    # Maximum per lifecycle stage
    'max_per_stage': {
        'MATURE': 0.30,       # 30% total in MATURE configs
        'VALIDATION': 0.15,   # 15% total in VALIDATION
        'DISCOVERY': 0.05,    # 5% total in DISCOVERY
        'DECAY': 0.10,        # 10% total in DECAY
    },
    
    # Maximum per asset (across all configs)
    'max_per_asset': 0.20,  # 20% in any single asset
    
    # Minimum capital reserve
    'min_cash_reserve': 0.30,  # 30% always in cash
    
    # Daily loss limit
    'max_daily_loss': 0.02,  # 2% of portfolio per day
    
    # Maximum concurrent positions
    'max_positions': 10,
    
    # Minimum position size
    'min_position_size': 100.0,  # $100 minimum
}
```

### Position-Level Checks

```python
def validate_signal_execution(signal, portfolio, config):
    """
    Pre-execution risk checks
    
    Returns (can_execute: bool, reason: str)
    """
    
    # Check daily loss limit
    if portfolio['daily_pnl'] < -RISK_LIMITS['max_daily_loss'] * portfolio['total_value']:
        return False, "Daily loss limit reached"
    
    # Check total exposure
    total_exposure = portfolio['total_exposure'] / portfolio['total_value']
    if total_exposure >= RISK_LIMITS['max_total_exposure']:
        return False, f"Portfolio exposure limit reached ({total_exposure:.1%})"
    
    # Check per-asset limit
    asset_exposure = portfolio['exposures_by_asset'].get(signal.pair, 0)
    if asset_exposure >= RISK_LIMITS['max_per_asset']:
        return False, f"Asset exposure limit reached for {signal.pair}"
    
    # Check minimum position size
    if signal.position_size < RISK_LIMITS['min_position_size']:
        return False, f"Position size below minimum (${signal.position_size:.2f})"
    
    # Check configuration lifecycle
    if config['lifecycle_stage'] == 'PAPER':
        return False, "Configuration is in PAPER mode"
    
    # Check maximum positions
    if len(portfolio['open_positions']) >= RISK_LIMITS['max_positions']:
        return False, "Maximum concurrent positions reached"
    
    return True, "OK"
```

---

## Database Schema Integration

### Active Configurations Query

```sql
-- Get active configurations with performance metrics
SELECT 
    id,
    strategy_name,
    pair,
    exchange,
    timeframe,
    lifecycle_stage,
    parameters,
    performance,
    validation,
    regime
FROM trained_configurations
WHERE is_active = TRUE
  AND lifecycle_stage != 'PAPER'
ORDER BY 
    CASE lifecycle_stage
        WHEN 'MATURE' THEN 1
        WHEN 'VALIDATION' THEN 2
        WHEN 'DISCOVERY' THEN 3
        WHEN 'DECAY' THEN 4
    END,
    (validation->>'sharpe_ratio')::numeric DESC;
```

### Track Trade Execution

```sql
-- Record executed trade
INSERT INTO trades (
    user_id,
    config_id,
    symbol,
    direction,
    entry_price,
    quantity,
    stop_loss,
    take_profit,
    entry_timestamp,
    strategy_name,
    is_paper_trade
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, FALSE
);
```

---

## Example Trading Cycle Output

```
============================================================
Trading Cycle: 2025-10-23 14:35:00
============================================================

📊 Loaded 4 active configurations

✅ Signal: BTC/USDT - BUY (confidence: 0.87)
  💰 Position size: $8,700.00 (8.7% of capital)

✅ Signal: ETH/USDT - BUY (confidence: 0.72)
  💰 Position size: $3,600.00 (3.6% of capital)

✅ Signal: SOL/USDT - BUY (confidence: 0.65)
  💰 Position size: $1,300.00 (1.3% of capital)

📊 Generated 3 signals

🚀 EXECUTING: BUY BTC/USDT
   Entry: $67,234.50
   Stop Loss: $65,890.00
   Take Profit: $69,500.00
   Size: $8,700.00

🚀 EXECUTING: BUY ETH/USDT
   Entry: $3,456.78
   Stop Loss: $3,380.00
   Take Profit: $3,580.00
   Size: $3,600.00

🚀 EXECUTING: BUY SOL/USDT
   Entry: $145.67
   Stop Loss: $142.00
   Take Profit: $151.00
   Size: $1,300.00

📊 Portfolio State:
   Total Value: $100,000
   Active Positions: 3
   Total Exposure: $13,600 (13.6%)
   Available Capital: $86,400 (86.4%)
   Daily P&L: +$234.50 (+0.23%)

============================================================
```

---

## Summary

### V2 Portfolio Management (NO RL)

✅ **Signal Generation**: Each active configuration generates BUY/SELL/HOLD signals using trained parameters

✅ **Position Sizing**: Based on:
- Lifecycle stage (MATURE = larger, DISCOVERY = smaller)
- Configuration confidence (Sharpe ratio, win rate)
- Signal strength (0.0 - 1.0 from strategy logic)

✅ **Risk Management**: 
- Max 50% portfolio exposure
- Per-stage and per-asset limits
- Circuit breakers (daily loss, correlation spikes, etc.)

✅ **Execution**: 
- Submit orders via CCXT
- Track in `trades` and `active_trades` tables
- Monitor stop-loss / take-profit

### Key Difference from RL Approach

| Aspect | RL System (OLD) | V2 Configurations (NEW) |
|--------|-----------------|-------------------------|
| Decision Making | Neural network predicts weights | Rule-based strategy logic |
| Position Sizing | RL model output (-1 to +1 per asset) | Lifecycle stage + confidence formula |
| Training | PPO training (hours) | Parameter optimization (minutes) |
| Interpretability | Black box | Fully transparent parameters |
| Output | model.pkl file | JSON configuration |

---

## Next Steps

1. ✅ Build parameter optimization system (DataCollector, BacktestEngine, etc.)
2. ✅ Generate trained configurations in `trained_configurations` table
3. ✅ Build `PortfolioManager` class (this document)
4. ✅ Integrate with `main.py` trading bot
5. ✅ Deploy and monitor

**No RL system needed** - V2 is fully rule-based! 🚀
