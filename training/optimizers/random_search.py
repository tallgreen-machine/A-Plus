"""
RandomSearchOptimizer - Monte Carlo Parameter Sampling

Randomly samples parameter combinations from the search space.
Often finds good solutions much faster than grid search.

Supports parallel evaluation across multiple CPU cores for faster results.

Best for:
- Large parameter spaces
- When you want quick results
- Exploration before refined optimization
- Parallel execution (unlike Bayesian which is sequential)

Research shows random search often outperforms grid search with
fewer evaluations (Bergstra & Bengio, 2012).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Union, Callable, Optional
import logging
from tqdm import tqdm
from joblib import delayed

from ..backtest_engine import BacktestEngine, BacktestResult
from ..utils.cpu_config import get_cached_training_workers
from .progress_parallel import ProgressParallel

log = logging.getLogger(__name__)


class RandomSearchOptimizer:
    """
    Random search through parameter space.
    
    Example:
        optimizer = RandomSearchOptimizer(seed=42)
        
        result = optimizer.optimize(
            backtest_engine=engine,
            data=df,
            strategy_class=LiquiditySweepStrategy,
            parameter_space={
                'pierce_depth': (0.001, 0.005),      # Continuous range
                'volume_spike_threshold': (1.5, 5.0),  # Continuous range
                'reversal_candles': [1, 2, 3, 4, 5]    # Discrete choices
            },
            n_iterations=200,
            objective='sharpe_ratio'
        )
        
        # Tests 200 random combinations
    """
    
    def __init__(self, seed: int = None, verbose: bool = True):
        """
        Initialize RandomSearchOptimizer.
        
        Args:
            seed: Random seed for reproducibility
            verbose: Show progress bar during optimization
        """
        self.seed = seed
        self.verbose = verbose
        
        if seed is not None:
            np.random.seed(seed)
        
        log.info(f"RandomSearchOptimizer initialized (seed={seed})")
    
    def optimize(
        self,
        backtest_engine: BacktestEngine,
        data: pd.DataFrame,
        strategy_class: Any,
        parameter_space: Dict[str, Any],
        n_iterations: int = 100,
        objective: str = 'sharpe_ratio',
        min_trades: int = 10,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        n_jobs: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run random search optimization with optional parallel evaluation.
        
        Args:
            backtest_engine: BacktestEngine instance
            data: OHLCV DataFrame with indicators
            strategy_class: Strategy class to instantiate
            parameter_space: Dict of parameter names to ranges/choices
                Supported formats:
                - Continuous range: (min, max) tuple
                - Discrete choices: [val1, val2, val3] list
                - Integer range: range(min, max) or (min, max) with int values
                
                Example:
                {
                    'pierce_depth': (0.001, 0.005),           # Continuous
                    'volume_spike_threshold': (1.5, 5.0),     # Continuous
                    'reversal_candles': [1, 2, 3, 4, 5],      # Discrete
                    'max_holding_periods': (10, 100)          # Integer range
                }
            n_iterations: Number of random samples to test
            objective: Metric to maximize
            min_trades: Minimum trades required for valid configuration
            n_jobs: Number of parallel jobs (-1 = all cores, None = auto-detect with safety margin)
        
        Returns:
            Dict with best_parameters, best_score, best_metrics, all_results, search_stats
        """
        # Determine number of parallel jobs
        if n_jobs is None:
            n_jobs = get_cached_training_workers()  # Auto-detect with safety margin
        elif n_jobs == -1:
            n_jobs = get_cached_training_workers()  # Use all available (with margin)
        
        use_parallel = n_jobs > 1
        
        log.info(
            f"Starting Random Search: {n_iterations} iterations "
            f"{'in parallel' if use_parallel else 'sequentially'} "
            f"({n_jobs} worker{'s' if n_jobs > 1 else ''})"
        )
        
        # Validate parameter space
        self._validate_parameter_space(parameter_space)
        
        # Sample all configurations upfront for parallel execution
        all_params = []
        tested_configs = set()
        
        for _ in range(n_iterations):
            params = self._sample_parameters(parameter_space)
            params_hash = self._hash_params(params)
            
            if params_hash not in tested_configs:
                tested_configs.add(params_hash)
                all_params.append(params)
        
        log.info(f"Generated {len(all_params)} unique configurations")
        
        # Define evaluation function
        def evaluate_config(params_tuple):
            """Evaluate a single parameter configuration."""
            i, params = params_tuple
            try:
                strategy = strategy_class(params)
                
                backtest_result = backtest_engine.run_backtest(
                    data=data,
                    strategy_instance=strategy
                )
                
                if backtest_result.metrics['total_trades'] >= min_trades:
                    objective_value = backtest_result.metrics.get(objective, 0)
                    
                    # Fire progress callback immediately (for parallel execution)
                    if progress_callback:
                        progress_callback(i + 1, len(all_params), objective_value)
                    
                    return {
                        'parameters': params.copy(),
                        'metrics': backtest_result.metrics,
                        'objective_value': objective_value
                    }
                return None
                
            except Exception as e:
                log.debug(f"Backtest failed for params {params}: {e}")
                return None
        
        # Execute evaluations (parallel or sequential)
        if use_parallel:
            log.info(f"Running parallel evaluation with {n_jobs} workers...")
            results = ProgressParallel(
                n_jobs=n_jobs, 
                backend='loky', 
                verbose=1,  # Enable verbose to trigger print_progress callbacks
                progress_callback=progress_callback,
                total=len(all_params)
            )(
                delayed(evaluate_config)((i, params)) 
                for i, params in enumerate(all_params)
            )
            # Filter out None results
            results = [r for r in results if r is not None]
        else:
            log.info("Running sequential evaluation...")
            iterator = tqdm(enumerate(all_params), desc="Random Search", total=len(all_params)) if self.verbose else enumerate(all_params)
            results = []
            for i, params in iterator:
                result = evaluate_config((i, params))
                if result is not None:
                    results.append(result)
                    # Fire progress callback in sequential mode too
                    if progress_callback:
                        progress_callback(len(results), len(all_params), result['objective_value'])
        
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
            n_iterations
        )
        
        log.info(
            f"✅ Random Search complete: "
            f"Best {objective} = {best_result['objective_value']:.3f} "
            f"({len(results)}/{n_iterations} valid configs)"
        )
        
        return {
            'best_parameters': best_result['parameters'],
            'best_score': best_result['objective_value'],
            'best_metrics': best_result['metrics'],
            'all_results': all_results_df,
            'search_stats': search_stats,
            'optimizer': 'random_search',
            'total_evaluations': n_iterations,
            'valid_evaluations': len(results)
        }
    
    def _validate_parameter_space(self, parameter_space: Dict[str, Any]):
        """Validate parameter space format."""
        for param_name, param_config in parameter_space.items():
            if isinstance(param_config, (list, tuple)):
                if len(param_config) == 0:
                    raise ValueError(f"Parameter '{param_name}' has empty range/choices")
                
                # If tuple of 2 numbers, treat as range
                if (isinstance(param_config, tuple) and 
                    len(param_config) == 2 and
                    isinstance(param_config[0], (int, float)) and
                    isinstance(param_config[1], (int, float))):
                    if param_config[0] >= param_config[1]:
                        raise ValueError(
                            f"Parameter '{param_name}' range invalid: "
                            f"min ({param_config[0]}) >= max ({param_config[1]})"
                        )
            else:
                raise ValueError(
                    f"Parameter '{param_name}' must be tuple (range) or list (choices), "
                    f"got {type(param_config)}"
                )
    
    def _sample_parameters(self, parameter_space: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sample random parameter values from space.
        
        Returns:
            Dict of parameter values
        """
        params = {}
        
        for param_name, param_config in parameter_space.items():
            if isinstance(param_config, list):
                # Discrete choices - random choice
                params[param_name] = np.random.choice(param_config)
                
            elif isinstance(param_config, tuple) and len(param_config) == 2:
                min_val, max_val = param_config
                
                # Check if integer range
                if isinstance(min_val, int) and isinstance(max_val, int):
                    # Integer range - random integer
                    params[param_name] = np.random.randint(min_val, max_val + 1)
                else:
                    # Continuous range - random float
                    params[param_name] = np.random.uniform(min_val, max_val)
            
            else:
                raise ValueError(f"Unsupported parameter config for '{param_name}': {param_config}")
        
        return params
    
    def _hash_params(self, params: Dict[str, Any]) -> str:
        """Create hash string from parameters for duplicate detection."""
        # Sort by key for consistent hashing
        items = sorted(params.items())
        
        # Round floats to avoid precision issues
        items_str = []
        for k, v in items:
            if isinstance(v, float):
                items_str.append(f"{k}={v:.6f}")
            else:
                items_str.append(f"{k}={v}")
        
        return "|".join(items_str)
    
    def _calculate_search_stats(
        self,
        results_df: pd.DataFrame,
        objective: str,
        n_iterations: int
    ) -> Dict[str, Any]:
        """Calculate statistics about search process."""
        obj_col = 'objective_value'
        
        # Calculate convergence (best score over time)
        convergence = []
        best_so_far = float('-inf')
        for score in results_df[obj_col]:
            best_so_far = max(best_so_far, score)
            convergence.append(best_so_far)
        
        return {
            'total_iterations': n_iterations,
            'valid_configurations': len(results_df),
            'best_objective': results_df[obj_col].max(),
            'worst_objective': results_df[obj_col].min(),
            'mean_objective': results_df[obj_col].mean(),
            'median_objective': results_df[obj_col].median(),
            'std_objective': results_df[obj_col].std(),
            'top_10_pct_threshold': results_df[obj_col].quantile(0.9),
            'configurations_above_threshold': (
                results_df[obj_col] >= results_df[obj_col].quantile(0.9)
            ).sum(),
            'convergence_curve': convergence
        }
    
    def get_top_n_configs(
        self,
        optimization_result: Dict[str, Any],
        n: int = 10
    ) -> pd.DataFrame:
        """Get top N configurations from optimization result."""
        all_results = optimization_result['all_results']
        return all_results.nlargest(n, 'objective_value')
    
    def plot_convergence(self, optimization_result: Dict[str, Any]):
        """
        Plot convergence curve showing best objective over iterations.
        
        Requires matplotlib.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            log.warning("matplotlib not installed. Cannot plot convergence.")
            return
        
        convergence = optimization_result['search_stats']['convergence_curve']
        
        plt.figure(figsize=(10, 6))
        plt.plot(convergence, linewidth=2)
        plt.xlabel('Iteration')
        plt.ylabel('Best Objective Score')
        plt.title('Random Search Convergence')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
