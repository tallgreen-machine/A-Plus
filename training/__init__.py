"""
V2 Training System - Rule-Based Parameter Optimization

This training system finds optimal parameters for trading strategies using
intelligent search algorithms (Grid, Random, Bayesian Optimization).

Components:
- data_collector: Database-first OHLCV data fetching
- backtest_engine: Trade simulation and metrics calculation
- optimizers/: GridSearch, RandomSearch, BayesianOptimizer
- strategies/: Strategy implementations (LiquiditySweep, etc.)
- validator: Walk-forward validation
- configuration_writer: V3 JSON generation and DB persistence

NO neural networks - fully transparent, rule-based parameter optimization.
"""

__version__ = "1.0.0"
