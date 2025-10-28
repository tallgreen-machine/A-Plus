"""
GridSearchOptimizer - Exhaustive Parameter Search

Tests every combination of parameters in the search space.
Guaranteed to find the global optimum within the grid, but can be slow
for large parameter spaces.

Best for:
- Small parameter spaces (< 1000 combinations)
- When you need guaranteed global optimum
- Initial exploration to understand parameter sensitivity
"""

import itertools
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Callable
import logging
from tqdm import tqdm
from joblib import delayed

from ..backtest_engine import BacktestEngine, BacktestResult
from .progress_parallel import ProgressParallel

log = logging.getLogger(__name__)

class GridSearchOptimizer:
    """
    Exhaustive grid search through parameter space.
    
    Example:
        optimizer = GridSearchOptimizer()
        
        result = optimizer.optimize(
            backtest_engine=engine,
            data=df,
            strategy_class=LiquiditySweepStrategy,
            parameter_space={
                'pierce_depth': [0.001, 0.002, 0.003],
                'volume_spike_threshold': [2.0, 2.5, 3.0],
                'reversal_candles': [1, 2, 3]
            },
            objective='sharpe_ratio'
        )
        
        # 3 × 3 × 3 = 27 combinations tested
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize GridSearchOptimizer.
        
        Args:
            verbose: Show progress bar during optimization
        """
        self.verbose = verbose
        log.info("GridSearchOptimizer initialized")
    
    def optimize(
        self,
        backtest_engine: BacktestEngine,
        data: pd.DataFrame,
        strategy_class: Any,
        parameter_space: Dict[str, Any],
        objective: str = 'sharpe_ratio',
        min_trades: int = 10,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        n_jobs: int = 1
    ) -> Dict[str, Any]:
        """
        Run grid search optimization.
        
        Args:
            backtest_engine: BacktestEngine instance
            data: OHLCV DataFrame with indicators
            strategy_class: Strategy class to instantiate
            parameter_space: Dict of parameter names to value lists
                Example:
                {
                    'pierce_depth': [0.001, 0.002, 0.003],  # 3 values
                    'volume_spike_threshold': [2.0, 3.0],   # 2 values
                    'reversal_candles': [1, 2, 3]           # 3 values
                }
                Total combinations: 3 × 2 × 3 = 18
            objective: Metric to maximize ('sharpe_ratio', 'net_profit_pct', etc.)
            min_trades: Minimum trades required for valid configuration
        
        Returns:
            Dict with:
                - best_parameters: Optimal parameter combination
                - best_score: Best objective value
                - best_metrics: Full metrics for best config
                - all_results: DataFrame of all tested combinations
                - search_stats: Statistics about search process
        """
        log.info("Starting Grid Search optimization...")
        
        # Convert parameter space to grid
        param_grid = self._build_parameter_grid(parameter_space)
        total_combinations = len(param_grid)
        
        log.info(
            f"Grid size: {total_combinations} combinations "
            f"({', '.join(f'{k}={len(v)}' for k, v in parameter_space.items())})"
        )
        
        if total_combinations > 10000:
            log.warning(
                f"Large grid ({total_combinations} combinations). "
                f"Consider using RandomSearch or Bayesian optimization."
            )
        
        # Determine parallelization
        use_parallel = n_jobs != 1
        
        log.info(
            f"Testing configurations {'in parallel' if use_parallel else 'sequentially'} "
            f"({n_jobs if n_jobs > 0 else 'all'} workers)"
        )
        
        # Define evaluation function
        def evaluate_params(params_tuple):
            i, params = params_tuple
            try:
                strategy = strategy_class(params)
                backtest_result = backtest_engine.run_backtest(
                    data=data,
                    strategy_instance=strategy
                )
                
                objective_value = backtest_result.metrics.get(objective, 0)
                
                if backtest_result.metrics['total_trades'] >= min_trades:
                    # Fire progress callback immediately (for parallel execution)
                    if progress_callback:
                        progress_callback(i + 1, total_combinations, objective_value)
                    
                    return {
                        'parameters': params.copy(),
                        'metrics': backtest_result.metrics,
                        'objective_value': objective_value
                    }
                return None
                
            except Exception as e:
                log.debug(f"Backtest failed for params {params}: {e}")
                return None
        
        # Run evaluations (parallel or sequential)
        if use_parallel:
            # Parallel execution with progress tracking
            results_raw = ProgressParallel(
                n_jobs=n_jobs,
                verbose=1,  # Enable verbose to trigger print_progress callbacks
                progress_callback=progress_callback,
                total=total_combinations
            )(
                delayed(evaluate_params)((i, params))
                for i, params in enumerate(param_grid)
            )
            results = [r for r in results_raw if r is not None]
        else:
            # Sequential execution with progress bar
            results = []
            iterator = tqdm(enumerate(param_grid), total=total_combinations, desc="Grid Search") if self.verbose else enumerate(param_grid)
            for i, params in iterator:
                result = evaluate_params((i, params))
                if result is not None:
                    results.append(result)
                    # Fire progress callback in sequential mode
                    if progress_callback:
                        progress_callback(len(results), total_combinations, result['objective_value'])
            
            for params_tuple in iterator:
                result = evaluate_params(params_tuple)
                if result is not None:
                    results.append(result)
        
        if not results:
            raise ValueError(
                f"No valid configurations found (min_trades={min_trades}). "
                f"Try lowering min_trades or expanding parameter space."
            )
        
        # Find best configuration
        best_result = max(results, key=lambda x: x['objective_value'])
        
        # Create results DataFrame
        all_results_df = pd.DataFrame([
            {
                **r['parameters'],
                **{f"metric_{k}": v for k, v in r['metrics'].items()},
                'objective_value': r['objective_value']
            }
            for r in results
        ])
        
        # Calculate search statistics
        search_stats = self._calculate_search_stats(
            all_results_df,
            objective,
            total_combinations
        )
        
        log.info(
            f"✅ Grid Search complete: "
            f"Best {objective} = {best_result['objective_value']:.3f} "
            f"({len(results)}/{total_combinations} valid configs)"
        )
        
        return {
            'best_parameters': best_result['parameters'],
            'best_score': best_result['objective_value'],
            'best_metrics': best_result['metrics'],
            'all_results': all_results_df,
            'search_stats': search_stats,
            'optimizer': 'grid_search',
            'total_evaluations': total_combinations,
            'valid_evaluations': len(results)
        }
    
    def _build_parameter_grid(
        self,
        parameter_space: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Convert parameter space to list of all combinations.
        
        Args:
            parameter_space: Dict of parameter names to value lists
        
        Returns:
            List of parameter dictionaries (one per combination)
        """
        # Ensure all values are lists
        param_lists = {}
        for param_name, param_values in parameter_space.items():
            if isinstance(param_values, (list, tuple)):
                param_lists[param_name] = param_values
            elif isinstance(param_values, range):
                param_lists[param_name] = list(param_values)
            else:
                # Single value - wrap in list
                param_lists[param_name] = [param_values]
        
        # Generate all combinations
        param_names = list(param_lists.keys())
        param_value_lists = [param_lists[name] for name in param_names]
        
        grid = []
        for combination in itertools.product(*param_value_lists):
            grid.append(dict(zip(param_names, combination)))
        
        return grid
    
    def _calculate_search_stats(
        self,
        results_df: pd.DataFrame,
        objective: str,
        total_combinations: int
    ) -> Dict[str, Any]:
        """Calculate statistics about search process."""
        obj_col = 'objective_value'
        
        return {
            'total_combinations_tested': total_combinations,
            'valid_configurations': len(results_df),
            'best_objective': results_df[obj_col].max(),
            'worst_objective': results_df[obj_col].min(),
            'mean_objective': results_df[obj_col].mean(),
            'median_objective': results_df[obj_col].median(),
            'std_objective': results_df[obj_col].std(),
            'top_10_pct_threshold': results_df[obj_col].quantile(0.9),
            'configurations_above_threshold': (
                results_df[obj_col] >= results_df[obj_col].quantile(0.9)
            ).sum()
        }
    
    def get_top_n_configs(
        self,
        optimization_result: Dict[str, Any],
        n: int = 10
    ) -> pd.DataFrame:
        """
        Get top N configurations from optimization result.
        
        Args:
            optimization_result: Result dict from optimize()
            n: Number of top configs to return
        
        Returns:
            DataFrame with top N configs sorted by objective
        """
        all_results = optimization_result['all_results']
        return all_results.nlargest(n, 'objective_value')
    
    def analyze_parameter_importance(
        self,
        optimization_result: Dict[str, Any],
        parameter_space: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Analyze which parameters have most impact on objective.
        
        Uses correlation between parameter values and objective.
        
        Args:
            optimization_result: Result dict from optimize()
            parameter_space: Original parameter space
        
        Returns:
            Dict of parameter names to importance scores (0-1)
        """
        all_results = optimization_result['all_results']
        param_names = list(parameter_space.keys())
        
        importance = {}
        
        for param in param_names:
            if param in all_results.columns:
                # Calculate correlation with objective
                corr = abs(all_results[param].corr(all_results['objective_value']))
                importance[param] = corr
        
        # Normalize to 0-1
        max_importance = max(importance.values()) if importance else 1
        if max_importance > 0:
            importance = {k: v / max_importance for k, v in importance.items()}
        
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
