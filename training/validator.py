"""
WalkForwardValidator - Prevent Overfitting with Time-Series Validation

Validates strategy parameters using walk-forward analysis:
- Split data into train/test windows with gap (no lookahead bias)
- Train on historical data, test on unseen future data
- Roll windows forward through time
- Detect overfitting by comparing train vs test metrics

This is the gold standard for time-series validation, preventing the
common mistake of training and testing on the same period.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from .backtest_engine import BacktestEngine, BacktestResult

log = logging.getLogger(__name__)


@dataclass
class ValidationWindow:
    """Single validation window."""
    window_id: int
    train_start_idx: int
    train_end_idx: int
    gap_start_idx: int
    gap_end_idx: int
    test_start_idx: int
    test_end_idx: int
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]


@dataclass
class ValidationResult:
    """Complete walk-forward validation results."""
    windows: List[ValidationWindow]
    aggregate_metrics: Dict[str, float]
    overfitting_detected: bool
    overfitting_reasons: List[str]
    stability_score: float


class WalkForwardValidator:
    """
    Walk-forward validation for strategy parameter optimization.
    
    Prevents overfitting by:
    1. Training on historical window
    2. Testing on future unseen window
    3. Gap between train/test (no lookahead)
    4. Rolling windows through entire dataset
    5. Comparing train vs test performance
    
    Example:
        validator = WalkForwardValidator(
            train_window_days=60,   # Train on 60 days
            test_window_days=30,    # Test on next 30 days
            gap_days=7              # 7-day gap (no lookahead)
        )
        
        result = validator.validate(
            config={'pierce_depth': 0.002, ...},
            data=df,
            strategy_class=LiquiditySweepStrategy,
            backtest_engine=engine
        )
        
        if result.overfitting_detected:
            print(f"Overfitting! Reasons: {result.overfitting_reasons}")
        else:
            print(f"Validated! Test Sharpe: {result.aggregate_metrics['test_sharpe_ratio']}")
    """
    
    def __init__(
        self,
        train_window_days: int = 60,
        test_window_days: int = 30,
        gap_days: int = 7,
        min_windows: int = 2,
        overfitting_threshold_sharpe: float = 0.7,
        overfitting_threshold_winrate: float = 0.8,
        min_stability_score: float = 0.6
    ):
        """
        Initialize WalkForwardValidator.
        
        Args:
            train_window_days: Days of data for training window
            test_window_days: Days of data for test window
            gap_days: Days between train and test (prevent lookahead)
            min_windows: Minimum validation windows required
            overfitting_threshold_sharpe: If test_sharpe < threshold × train_sharpe, flag overfit
            overfitting_threshold_winrate: If test_winrate < threshold × train_winrate, flag overfit
            min_stability_score: Minimum stability score to pass validation
        """
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.gap_days = gap_days
        self.min_windows = min_windows
        self.overfitting_threshold_sharpe = overfitting_threshold_sharpe
        self.overfitting_threshold_winrate = overfitting_threshold_winrate
        self.min_stability_score = min_stability_score
        
        log.info(
            f"WalkForwardValidator initialized: "
            f"train={train_window_days}d, test={test_window_days}d, gap={gap_days}d"
        )
    
    def validate(
        self,
        config: Dict[str, Any],
        data: pd.DataFrame,
        strategy_class: Any,
        backtest_engine: BacktestEngine
    ) -> ValidationResult:
        """
        Run walk-forward validation on strategy configuration.
        
        Args:
            config: Strategy parameters to validate
            data: Full OHLCV DataFrame with indicators
            strategy_class: Strategy class to instantiate
            backtest_engine: BacktestEngine instance
        
        Returns:
            ValidationResult with windows, metrics, overfitting detection
        """
        log.info(f"Starting walk-forward validation: {len(data)} candles")
        
        # Calculate window indices
        windows = self._create_windows(data)
        
        if len(windows) < self.min_windows:
            raise ValueError(
                f"Insufficient data for validation. "
                f"Need {self.min_windows} windows, can only create {len(windows)}. "
                f"Required data: ~{(self.train_window_days + self.test_window_days + self.gap_days) * self.min_windows} days"
            )
        
        log.info(f"Created {len(windows)} validation windows")
        
        # Run validation on each window
        validated_windows = []
        
        for window_info in windows:
            validated_window = self._validate_window(
                window_info=window_info,
                config=config,
                data=data,
                strategy_class=strategy_class,
                backtest_engine=backtest_engine
            )
            validated_windows.append(validated_window)
        
        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(validated_windows)
        
        # Detect overfitting
        overfitting_detected, overfitting_reasons = self._detect_overfitting(
            validated_windows,
            aggregate_metrics
        )
        
        # Calculate stability score
        stability_score = self._calculate_stability_score(validated_windows)
        
        log.info(
            f"✅ Validation complete: "
            f"{len(validated_windows)} windows, "
            f"Test Sharpe {aggregate_metrics.get('test_sharpe_ratio', 0):.2f}, "
            f"Stability {stability_score:.2f}, "
            f"Overfit: {overfitting_detected}"
        )
        
        return ValidationResult(
            windows=validated_windows,
            aggregate_metrics=aggregate_metrics,
            overfitting_detected=overfitting_detected,
            overfitting_reasons=overfitting_reasons,
            stability_score=stability_score
        )
    
    def _create_windows(
        self,
        data: pd.DataFrame
    ) -> List[Dict[str, int]]:
        """
        Create train/test window indices.
        
        Example with train=60d, test=30d, gap=7d:
        
        Window 1: [Train: 0-60] [Gap: 60-67] [Test: 67-97]
        Window 2: [Train: 30-90] [Gap: 90-97] [Test: 97-127]
        Window 3: [Train: 60-120] [Gap: 120-127] [Test: 127-157]
        ...
        
        Returns:
            List of window info dicts
        """
        # Estimate candles per day (assuming data sorted by timestamp)
        timestamps = data['timestamp'].values
        time_diffs = np.diff(timestamps)
        avg_candle_interval_ms = np.median(time_diffs)
        candles_per_day = int((24 * 60 * 60 * 1000) / avg_candle_interval_ms)
        
        # Convert days to candles
        train_window_candles = self.train_window_days * candles_per_day
        test_window_candles = self.test_window_days * candles_per_day
        gap_candles = self.gap_days * candles_per_day
        
        total_window_size = train_window_candles + gap_candles + test_window_candles
        
        # Create windows with 50% overlap
        step_size = train_window_candles // 2
        
        windows = []
        window_id = 1
        start_idx = 0
        
        while start_idx + total_window_size <= len(data):
            train_start = start_idx
            train_end = start_idx + train_window_candles
            
            gap_start = train_end
            gap_end = gap_start + gap_candles
            
            test_start = gap_end
            test_end = test_start + test_window_candles
            
            windows.append({
                'window_id': window_id,
                'train_start_idx': train_start,
                'train_end_idx': train_end,
                'gap_start_idx': gap_start,
                'gap_end_idx': gap_end,
                'test_start_idx': test_start,
                'test_end_idx': test_end
            })
            
            window_id += 1
            start_idx += step_size
        
        return windows
    
    def _validate_window(
        self,
        window_info: Dict[str, int],
        config: Dict[str, Any],
        data: pd.DataFrame,
        strategy_class: Any,
        backtest_engine: BacktestEngine
    ) -> ValidationWindow:
        """
        Validate configuration on a single train/test window.
        
        Returns:
            ValidationWindow with train and test metrics
        """
        window_id = window_info['window_id']
        
        # Extract train and test data
        train_data = data.iloc[
            window_info['train_start_idx']:window_info['train_end_idx']
        ].copy()
        
        test_data = data.iloc[
            window_info['test_start_idx']:window_info['test_end_idx']
        ].copy()
        
        log.debug(
            f"Window {window_id}: "
            f"Train {len(train_data)} candles, "
            f"Test {len(test_data)} candles"
        )
        
        # Create strategy instance
        strategy = strategy_class(config)
        
        # Run backtest on train data
        train_result = backtest_engine.run_backtest(
            data=train_data,
            strategy_instance=strategy
        )
        
        # Run backtest on test data (same parameters)
        test_result = backtest_engine.run_backtest(
            data=test_data,
            strategy_instance=strategy
        )
        
        return ValidationWindow(
            window_id=window_id,
            train_start_idx=window_info['train_start_idx'],
            train_end_idx=window_info['train_end_idx'],
            gap_start_idx=window_info['gap_start_idx'],
            gap_end_idx=window_info['gap_end_idx'],
            test_start_idx=window_info['test_start_idx'],
            test_end_idx=window_info['test_end_idx'],
            train_metrics=train_result.metrics,
            test_metrics=test_result.metrics
        )
    
    def _calculate_aggregate_metrics(
        self,
        windows: List[ValidationWindow]
    ) -> Dict[str, float]:
        """
        Calculate aggregate metrics across all windows.
        
        Returns:
            Dict with train/test averages for key metrics
        """
        train_sharpes = []
        test_sharpes = []
        train_winrates = []
        test_winrates = []
        train_profits = []
        test_profits = []
        
        for window in windows:
            train_sharpes.append(window.train_metrics.get('sharpe_ratio', 0))
            test_sharpes.append(window.test_metrics.get('sharpe_ratio', 0))
            train_winrates.append(window.train_metrics.get('gross_win_rate', 0))
            test_winrates.append(window.test_metrics.get('gross_win_rate', 0))
            train_profits.append(window.train_metrics.get('net_profit_pct', 0))
            test_profits.append(window.test_metrics.get('net_profit_pct', 0))
        
        return {
            'train_sharpe_ratio': np.mean(train_sharpes),
            'test_sharpe_ratio': np.mean(test_sharpes),
            'train_sharpe_std': np.std(test_sharpes),
            'test_sharpe_std': np.std(test_sharpes),
            'train_win_rate': np.mean(train_winrates),
            'test_win_rate': np.mean(test_winrates),
            'train_net_profit_pct': np.mean(train_profits),
            'test_net_profit_pct': np.mean(test_profits),
            'total_windows': len(windows),
            'profitable_windows_train': sum(1 for p in train_profits if p > 0),
            'profitable_windows_test': sum(1 for p in test_profits if p > 0)
        }
    
    def _detect_overfitting(
        self,
        windows: List[ValidationWindow],
        aggregate_metrics: Dict[str, float]
    ) -> Tuple[bool, List[str]]:
        """
        Detect overfitting by comparing train vs test performance.
        
        Returns:
            (overfitting_detected: bool, reasons: List[str])
        """
        reasons = []
        
        train_sharpe = aggregate_metrics['train_sharpe_ratio']
        test_sharpe = aggregate_metrics['test_sharpe_ratio']
        train_winrate = aggregate_metrics['train_win_rate']
        test_winrate = aggregate_metrics['test_win_rate']
        
        # Check 1: Test Sharpe significantly lower than train
        if test_sharpe < self.overfitting_threshold_sharpe * train_sharpe:
            reasons.append(
                f"Test Sharpe ({test_sharpe:.2f}) < "
                f"{self.overfitting_threshold_sharpe}× Train Sharpe ({train_sharpe:.2f})"
            )
        
        # Check 2: Test win rate significantly lower than train
        if test_winrate < self.overfitting_threshold_winrate * train_winrate:
            reasons.append(
                f"Test Win Rate ({test_winrate:.2%}) < "
                f"{self.overfitting_threshold_winrate}× Train Win Rate ({train_winrate:.2%})"
            )
        
        # Check 3: Negative test performance
        if test_sharpe < 0:
            reasons.append(f"Negative test Sharpe ratio ({test_sharpe:.2f})")
        
        # Check 4: Inconsistent performance across windows
        test_sharpes = [w.test_metrics.get('sharpe_ratio', 0) for w in windows]
        sharpe_std = np.std(test_sharpes)
        if sharpe_std > 1.5:
            reasons.append(
                f"High test Sharpe variability (std={sharpe_std:.2f}, suggests instability)"
            )
        
        # Check 5: Majority of windows unprofitable in test
        profitable_windows_test = aggregate_metrics['profitable_windows_test']
        total_windows = aggregate_metrics['total_windows']
        if profitable_windows_test < total_windows / 2:
            reasons.append(
                f"Only {profitable_windows_test}/{total_windows} test windows profitable"
            )
        
        return len(reasons) > 0, reasons
    
    def _calculate_stability_score(
        self,
        windows: List[ValidationWindow]
    ) -> float:
        """
        Calculate stability score (0-1) based on consistency across windows.
        
        Higher score = more consistent performance across windows
        """
        test_sharpes = [w.test_metrics.get('sharpe_ratio', 0) for w in windows]
        test_winrates = [w.test_metrics.get('gross_win_rate', 0) for w in windows]
        test_profits = [w.test_metrics.get('net_profit_pct', 0) for w in windows]
        
        # Component 1: Sharpe consistency (lower std = higher score)
        sharpe_mean = np.mean(test_sharpes)
        sharpe_std = np.std(test_sharpes)
        sharpe_consistency = 1 / (1 + sharpe_std) if sharpe_mean > 0 else 0
        
        # Component 2: Win rate consistency
        winrate_std = np.std(test_winrates)
        winrate_consistency = 1 / (1 + winrate_std * 10)  # Scale up std impact
        
        # Component 3: Profitable window ratio
        profitable_ratio = sum(1 for p in test_profits if p > 0) / len(test_profits)
        
        # Combined score (weighted average)
        stability_score = (
            0.4 * sharpe_consistency +
            0.3 * winrate_consistency +
            0.3 * profitable_ratio
        )
        
        return stability_score
    
    def get_validation_summary(
        self,
        result: ValidationResult
    ) -> str:
        """
        Get human-readable validation summary.
        
        Returns:
            Formatted string with validation results
        """
        metrics = result.aggregate_metrics
        
        summary = []
        summary.append("=" * 60)
        summary.append("WALK-FORWARD VALIDATION SUMMARY")
        summary.append("=" * 60)
        
        summary.append(f"\nValidation Windows: {metrics['total_windows']}")
        summary.append(f"Configuration: {len(result.windows)} windows validated")
        
        summary.append("\n--- TRAIN PERFORMANCE ---")
        summary.append(f"Sharpe Ratio: {metrics['train_sharpe_ratio']:.2f}")
        summary.append(f"Win Rate: {metrics['train_win_rate']:.2%}")
        summary.append(f"Net Profit: {metrics['train_net_profit_pct']:.2f}%")
        summary.append(f"Profitable Windows: {metrics['profitable_windows_train']}/{metrics['total_windows']}")
        
        summary.append("\n--- TEST PERFORMANCE (Out-of-Sample) ---")
        summary.append(f"Sharpe Ratio: {metrics['test_sharpe_ratio']:.2f} (±{metrics['test_sharpe_std']:.2f})")
        summary.append(f"Win Rate: {metrics['test_win_rate']:.2%}")
        summary.append(f"Net Profit: {metrics['test_net_profit_pct']:.2f}%")
        summary.append(f"Profitable Windows: {metrics['profitable_windows_test']}/{metrics['total_windows']}")
        
        summary.append("\n--- VALIDATION RESULT ---")
        summary.append(f"Stability Score: {result.stability_score:.2f}")
        summary.append(f"Overfitting Detected: {'YES ⚠️' if result.overfitting_detected else 'NO ✓'}")
        
        if result.overfitting_detected:
            summary.append("\nOverfitting Reasons:")
            for reason in result.overfitting_reasons:
                summary.append(f"  - {reason}")
        
        # Recommendation
        summary.append("\n--- RECOMMENDATION ---")
        if result.overfitting_detected:
            summary.append("❌ REJECT: Configuration shows overfitting")
            summary.append("   Suggested actions:")
            summary.append("   - Simplify strategy (reduce parameters)")
            summary.append("   - Expand parameter search space")
            summary.append("   - Collect more training data")
        elif result.stability_score < self.min_stability_score:
            summary.append("⚠️  CAUTION: Low stability score")
            summary.append(f"   Stability {result.stability_score:.2f} < minimum {self.min_stability_score:.2f}")
            summary.append("   Consider collecting more data or adjusting parameters")
        else:
            summary.append("✅ ACCEPT: Configuration passes validation")
            summary.append("   Ready for production deployment")
        
        summary.append("=" * 60)
        
        return "\n".join(summary)
    
    def plot_validation_windows(
        self,
        result: ValidationResult,
        metric: str = 'sharpe_ratio'
    ):
        """
        Plot train vs test metrics across windows.
        
        Requires matplotlib.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            log.warning("matplotlib not installed. Cannot plot validation.")
            return
        
        windows = result.windows
        window_ids = [w.window_id for w in windows]
        train_values = [w.train_metrics.get(metric, 0) for w in windows]
        test_values = [w.test_metrics.get(metric, 0) for w in windows]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot 1: Train vs Test comparison
        x = np.arange(len(window_ids))
        width = 0.35
        
        ax1.bar(x - width/2, train_values, width, label='Train', alpha=0.8)
        ax1.bar(x + width/2, test_values, width, label='Test', alpha=0.8)
        ax1.set_xlabel('Window')
        ax1.set_ylabel(metric.replace('_', ' ').title())
        ax1.set_title(f'Walk-Forward Validation: {metric}')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'W{id}' for id in window_ids])
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        
        # Plot 2: Degradation (test/train ratio)
        degradation = [
            (test / train if train != 0 else 0) 
            for train, test in zip(train_values, test_values)
        ]
        
        ax2.plot(window_ids, degradation, marker='o', linewidth=2)
        ax2.axhline(y=1.0, color='g', linestyle='--', label='No degradation', alpha=0.7)
        ax2.axhline(
            y=self.overfitting_threshold_sharpe,
            color='r',
            linestyle='--',
            label=f'Overfitting threshold ({self.overfitting_threshold_sharpe})',
            alpha=0.7
        )
        ax2.set_xlabel('Window')
        ax2.set_ylabel('Test/Train Ratio')
        ax2.set_title('Performance Degradation (Test/Train)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
