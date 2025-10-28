"""
BayesianOptimizer - ML-Powered Intelligent Search

Uses Gaussian Process regression to build a probabilistic model of the
objective function and intelligently explores parameter space.

This IS machine learning! The GP model learns which parameter regions
are promising and focuses search there.

Best for:
- Expensive objective functions (backtesting)
- When you want optimal results with minimal evaluations
- Continuous and mixed parameter spaces

Typically finds near-optimal solutions in 50-200 evaluations vs.
thousands required by grid search.

Note: Bayesian optimization is inherently SEQUENTIAL - each iteration depends
on previous results to decide where to search next. For parallel execution,
use RandomSearchOptimizer instead.

Requires: scikit-optimize (pip install scikit-optimize)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Union, Callable, Optional
import logging
from tqdm import tqdm

try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer, Categorical
    from skopt.utils import use_named_args
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False
    log = logging.getLogger(__name__)
    log.warning(
        "scikit-optimize not installed. BayesianOptimizer unavailable. "
        "Install with: pip install scikit-optimize"
    )

from ..backtest_engine import BacktestEngine, BacktestResult

log = logging.getLogger(__name__)


class BayesianOptimizer:
    """
    Bayesian optimization using Gaussian Process.
    
    This is ML-powered parameter optimization! Uses a probabilistic model
    to intelligently search parameter space.
    
    Example:
        optimizer = BayesianOptimizer()
        
        result = optimizer.optimize(
            backtest_engine=engine,
            data=df,
            strategy_class=LiquiditySweepStrategy,
            parameter_space={
                'pierce_depth': (0.001, 0.005),           # Continuous
                'volume_spike_threshold': (1.5, 5.0),     # Continuous
                'reversal_candles': [1, 2, 3, 4, 5],      # Discrete
                'max_holding_periods': (10, 100)          # Integer
            },
            n_calls=200,              # Only 200 evaluations
            n_initial_points=20,      # Random exploration first
            objective='sharpe_ratio'
        )
        
        # ML model learns optimal regions, finds best config in 200 tests
        # vs. 5 × 5 × 5 × 91 = 11,375 for grid search!
    """
    
    def __init__(self, random_state: int = 42, verbose: bool = True):
        """
        Initialize BayesianOptimizer.
        
        Args:
            random_state: Random seed for reproducibility
            verbose: Show progress during optimization
        
        Raises:
            ImportError: If scikit-optimize not installed
        """
        if not SKOPT_AVAILABLE:
            raise ImportError(
                "BayesianOptimizer requires scikit-optimize. "
                "Install with: pip install scikit-optimize"
            )
        
        self.random_state = random_state
        self.verbose = verbose
        
        log.info(f"BayesianOptimizer initialized (ML-powered)")
    
    def optimize(
        self,
        backtest_engine: BacktestEngine,
        data: pd.DataFrame,
        strategy_class: Any,
        parameter_space: Dict[str, Any],
        n_calls: int = 100,
        n_initial_points: int = 10,
        objective: str = 'sharpe_ratio',
        min_trades: int = 10,
        acq_func: str = 'gp_hedge',
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        n_jobs: int = 1
    ) -> Dict[str, Any]:
        """
        Run Bayesian optimization using Gaussian Process.
        
        Args:
            backtest_engine: BacktestEngine instance
            data: OHLCV DataFrame with indicators
            strategy_class: Strategy class to instantiate
            parameter_space: Dict of parameter names to ranges/choices
                Supported formats:
                - Continuous range: (min, max) tuple with floats
                - Integer range: (min, max) tuple with ints
                - Discrete choices: [val1, val2, ...] list
                
                Example:
                {
                    'pierce_depth': (0.001, 0.005),           # Continuous
                    'volume_spike_threshold': (1.5, 5.0),     # Continuous
                    'reversal_candles': [1, 2, 3, 4, 5],      # Categorical
                    'max_holding_periods': (10, 100)          # Integer range
                }
            
            n_calls: Total number of evaluations (including initial)
            n_initial_points: Random exploration before GP modeling
            objective: Metric to maximize
            min_trades: Minimum trades required for valid configuration
            acq_func: Acquisition function
                - 'gp_hedge': Automatically selects best acquisition (recommended)
                - 'EI': Expected Improvement
                - 'LCB': Lower Confidence Bound
                - 'PI': Probability of Improvement
            progress_callback: Optional callback(iteration, total, score) for progress updates
        
        Returns:
            Dict with:
                - best_parameters: Optimal parameter combination
                - best_score: Best objective value
                - best_metrics: Full metrics for best config
                - all_results: DataFrame of all tested combinations
                - search_stats: Statistics about search process
                - convergence_trace: Objective values over iterations
                - gp_model: Trained Gaussian Process model (for analysis)
        """
        log.info(
            f"Starting Bayesian Optimization: {n_calls} evaluations "
            f"({n_initial_points} random exploration + {n_calls - n_initial_points} GP-guided)"
        )
        
        # Convert parameter space to skopt format
        dimensions, param_names = self._build_skopt_space(parameter_space)
        
        log.info(
            f"Parameter space: {len(param_names)} dimensions "
            f"({', '.join(param_names)})"
        )
        
        # Track all results
        all_evaluations = []
        iteration_counter = [0]  # Mutable for closure
        
        # Define objective function for skopt
        @use_named_args(dimensions=dimensions)
        def objective_function(**params):
            """
            Objective function for Bayesian optimization.
            
            Returns NEGATIVE objective (skopt minimizes, we want to maximize).
            """
            iteration_counter[0] += 1
            
            if self.verbose:
                print(f"\rIteration {iteration_counter[0]}/{n_calls}", end='')
            
            try:
                # Create strategy instance
                strategy = strategy_class(params)
                
                # Run backtest
                backtest_result = backtest_engine.run_backtest(
                    data=data,
                    strategy_instance=strategy
                )
                
                # Check minimum trades
                if backtest_result.metrics['total_trades'] < min_trades:
                    # Penalize configurations with too few trades
                    objective_value = -999
                else:
                    objective_value = backtest_result.metrics.get(objective, 0)
                
                # Record evaluation
                all_evaluations.append({
                    'iteration': iteration_counter[0],
                    'parameters': params.copy(),
                    'metrics': backtest_result.metrics,
                    'objective_value': objective_value
                })
                
                # Call progress callback (iteration complete)
                if progress_callback:
                    progress_callback(iteration_counter[0], n_calls, objective_value)
                
                # Return negative (skopt minimizes)
                return -objective_value
                
            except Exception as e:
                log.debug(f"Backtest failed for params {params}: {e}")
                # Return large penalty
                return 999
        
        # Run Gaussian Process optimization
        result = gp_minimize(
            func=objective_function,
            dimensions=dimensions,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            acq_func=acq_func,
            random_state=self.random_state,
            n_jobs=n_jobs,  # Parallelize initial random points and some internal operations
            verbose=False  # We handle progress ourselves
        )
        
        if self.verbose:
            print()  # New line after progress
        
        # Extract best configuration
        best_params_list = result.x
        best_params = dict(zip(param_names, best_params_list))
        best_score = -result.fun  # Negate back to positive
        
        # Find best evaluation in our records
        valid_evals = [e for e in all_evaluations if e['objective_value'] > -999]
        if valid_evals:
            best_eval = max(valid_evals, key=lambda x: x['objective_value'])
        else:
            raise ValueError(
                f"No valid configurations found (min_trades={min_trades}). "
                f"Try lowering min_trades or expanding parameter space."
            )
        
        # Create results DataFrame
        all_results_df = pd.DataFrame([
            {
                'iteration': e['iteration'],
                **e['parameters'],
                **{f"metric_{k}": v for k, v in e['metrics'].items()},
                'objective_value': e['objective_value']
            }
            for e in valid_evals
        ])
        
        # Calculate search statistics
        search_stats = self._calculate_search_stats(
            all_results_df,
            objective,
            n_calls,
            n_initial_points
        )
        
        # Extract convergence trace
        convergence_trace = [-y for y in result.func_vals]  # Negate back
        
        log.info(
            f"✅ Bayesian Optimization complete: "
            f"Best {objective} = {best_score:.3f} "
            f"({len(valid_evals)}/{n_calls} valid configs)"
        )
        
        return {
            'best_parameters': best_eval['parameters'],
            'best_score': best_eval['objective_value'],
            'best_metrics': best_eval['metrics'],
            'all_results': all_results_df,
            'search_stats': search_stats,
            'convergence_trace': convergence_trace,
            'optimizer': 'bayesian',
            'total_evaluations': n_calls,
            'valid_evaluations': len(valid_evals),
            'gp_model': result.models[-1] if result.models else None,
            'acquisition_function': acq_func
        }
    
    def _build_skopt_space(
        self,
        parameter_space: Dict[str, Any]
    ) -> Tuple[List, List[str]]:
        """
        Convert parameter space to skopt dimensions.
        
        Returns:
            (dimensions, param_names)
        """
        dimensions = []
        param_names = []
        
        for param_name, param_config in parameter_space.items():
            param_names.append(param_name)
            
            if isinstance(param_config, list):
                # Discrete choices -> Categorical
                dimensions.append(
                    Categorical(param_config, name=param_name)
                )
            
            elif isinstance(param_config, tuple) and len(param_config) == 2:
                min_val, max_val = param_config
                
                if isinstance(min_val, int) and isinstance(max_val, int):
                    # Integer range -> Integer
                    dimensions.append(
                        Integer(min_val, max_val, name=param_name)
                    )
                else:
                    # Continuous range -> Real
                    dimensions.append(
                        Real(min_val, max_val, name=param_name)
                    )
            
            else:
                raise ValueError(
                    f"Unsupported parameter config for '{param_name}': {param_config}"
                )
        
        return dimensions, param_names
    
    def _calculate_search_stats(
        self,
        results_df: pd.DataFrame,
        objective: str,
        n_calls: int,
        n_initial_points: int
    ) -> Dict[str, Any]:
        """Calculate statistics about Bayesian search process."""
        obj_col = 'objective_value'
        
        # Separate exploration and exploitation phases
        exploration_results = results_df[results_df['iteration'] <= n_initial_points]
        exploitation_results = results_df[results_df['iteration'] > n_initial_points]
        
        stats = {
            'total_evaluations': n_calls,
            'valid_configurations': len(results_df),
            'n_initial_points': n_initial_points,
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
        
        # Exploration phase stats
        if not exploration_results.empty:
            stats['exploration_best'] = exploration_results[obj_col].max()
            stats['exploration_mean'] = exploration_results[obj_col].mean()
        
        # Exploitation phase stats
        if not exploitation_results.empty:
            stats['exploitation_best'] = exploitation_results[obj_col].max()
            stats['exploitation_mean'] = exploitation_results[obj_col].mean()
            stats['improvement_from_exploration'] = (
                exploitation_results[obj_col].max() - exploration_results[obj_col].max()
                if not exploration_results.empty else 0
            )
        
        return stats
    
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
        
        convergence = optimization_result['convergence_trace']
        n_initial = optimization_result['search_stats']['n_initial_points']
        
        # Calculate best-so-far curve
        best_so_far = []
        current_best = float('-inf')
        for score in convergence:
            current_best = max(current_best, score)
            best_so_far.append(current_best)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Plot 1: All evaluations
        ax1.scatter(
            range(1, n_initial + 1),
            convergence[:n_initial],
            alpha=0.6,
            c='blue',
            label='Exploration (random)'
        )
        ax1.scatter(
            range(n_initial + 1, len(convergence) + 1),
            convergence[n_initial:],
            alpha=0.6,
            c='green',
            label='Exploitation (GP-guided)'
        )
        ax1.set_xlabel('Iteration')
        ax1.set_ylabel('Objective Value')
        ax1.set_title('Bayesian Optimization: All Evaluations')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Best-so-far curve
        ax2.plot(best_so_far, linewidth=2, color='red')
        ax2.axvline(x=n_initial, linestyle='--', color='gray', label='End of exploration')
        ax2.set_xlabel('Iteration')
        ax2.set_ylabel('Best Objective So Far')
        ax2.set_title('Convergence Curve')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_parameter_importance(
        self,
        optimization_result: Dict[str, Any],
        parameter_space: Dict[str, Any]
    ):
        """
        Plot parameter importance based on GP model.
        
        Requires matplotlib.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            log.warning("matplotlib not installed. Cannot plot importance.")
            return
        
        all_results = optimization_result['all_results']
        param_names = list(parameter_space.keys())
        
        # Calculate correlations with objective
        importance = {}
        for param in param_names:
            if param in all_results.columns:
                corr = abs(all_results[param].corr(all_results['objective_value']))
                importance[param] = corr
        
        # Sort by importance
        sorted_params = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        params, scores = zip(*sorted_params)
        
        # Plot
        plt.figure(figsize=(10, 6))
        plt.barh(params, scores)
        plt.xlabel('Importance (Correlation with Objective)')
        plt.title('Parameter Importance Analysis')
        plt.grid(True, alpha=0.3, axis='x')
        plt.tight_layout()
        plt.show()


# Convenience check function
def is_bayesian_available() -> bool:
    """Check if Bayesian optimization is available."""
    return SKOPT_AVAILABLE
