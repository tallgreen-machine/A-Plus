"""
Trading strategy implementations for training.

Each strategy implements signal detection logic and can be optimized
using the training system's parameter optimization algorithms.

Available strategies:
- LiquiditySweepStrategy: Key level pierce detection with volume confirmation
- (More strategies will be added: CapitulationReversal, FailedBreakdown, SupplyShock)
"""

from .liquidity_sweep import LiquiditySweepStrategy

__all__ = [
    'LiquiditySweepStrategy'
]
