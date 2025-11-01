"""
Trading strategy implementations for training.

Each strategy implements signal detection logic and can be optimized
using the training system's parameter optimization algorithms.

Available strategies:
- LiquiditySweepStrategy: Key level pierce detection with volume confirmation
- CapitulationReversalStrategy: Panic selling/buying reversal detection
- FailedBreakdownStrategy: Wyckoff spring detection (failed breakdowns)
"""

from .liquidity_sweep import LiquiditySweepStrategy
from .capitulation_reversal import CapitulationReversalStrategy
from .failed_breakdown import FailedBreakdownStrategy

__all__ = [
    'LiquiditySweepStrategy',
    'CapitulationReversalStrategy',
    'FailedBreakdownStrategy'
]
