#!/usr/bin/env python3
"""
End-to-End Training Pipeline Test

Tests the complete V2 training system:
1. DataCollector - Fetch OHLCV data
2. LiquiditySweepStrategy - Generate signals
3. BacktestEngine - Simulate trades
4. BayesianOptimizer - Find optimal parameters
5. WalkForwardValidator - Validate configuration
6. ConfigurationWriter - Save to database

This demonstrates the full workflow from data collection to 
production-ready configuration.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from training.data_collector import DataCollector
from training.backtest_engine import BacktestEngine
from training.strategies.liquidity_sweep import LiquiditySweepStrategy
from training.optimizers.bayesian import BayesianOptimizer, is_bayesian_available
from training.optimizers.random_search import RandomSearchOptimizer
from training.validator import WalkForwardValidator
from training.configuration_writer import ConfigurationWriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


async def test_end_to_end():
    """
    Run complete training pipeline test.
    
    Target: Train LIQUIDITY SWEEP for BTC/USDT on Binance 5m
    Expected time: < 5 minutes
    """
    print("=" * 80)
    print("V2 TRAINING SYSTEM - END-TO-END TEST")
    print("=" * 80)
    print()
    
    # Configuration
    SYMBOL = 'BTC/USDT'
    EXCHANGE = 'binance'
    TIMEFRAME = '5m'
    LOOKBACK_DAYS = 90
    N_CALLS = 50  # Small number for quick test (use 200 for production)
    
    print(f"Target: {SYMBOL} on {EXCHANGE} {TIMEFRAME}")
    print(f"Lookback: {LOOKBACK_DAYS} days")
    print(f"Optimizer: {'Bayesian (ML)' if is_bayesian_available() else 'Random Search'}")
    print(f"Evaluations: {N_CALLS}")
    print()
    
    try:
        # ===== STEP 1: Data Collection =====
        print("Step 1: Collecting data...")
        print("-" * 80)
        
        collector = DataCollector()
        data = await collector.fetch_ohlcv(
            symbol=SYMBOL,
            exchange=EXCHANGE,
            timeframe=TIMEFRAME,
            lookback_days=LOOKBACK_DAYS
        )
        
        print(f"✅ Data collected: {len(data)} candles")
        print(f"   Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
        print(f"   Columns: {list(data.columns)}")
        print()
        
        # ===== STEP 2: Parameter Space Definition =====
        print("Step 2: Defining parameter space...")
        print("-" * 80)
        
        strategy_instance = LiquiditySweepStrategy({})
        parameter_space = strategy_instance.get_parameter_space()
        
        print(f"✅ Parameter space defined:")
        for param, space in parameter_space.items():
            print(f"   - {param}: {space}")
        print()
        
        # ===== STEP 3: Optimization =====
        print("Step 3: Running optimization...")
        print("-" * 80)
        
        engine = BacktestEngine(
            initial_capital=10000,
            fee_rate=0.001,
            slippage_rate=0.0005
        )
        
        # Use Bayesian if available, otherwise Random
        if is_bayesian_available():
            optimizer = BayesianOptimizer(random_state=42, verbose=True)
            opt_result = optimizer.optimize(
                backtest_engine=engine,
                data=data,
                strategy_class=LiquiditySweepStrategy,
                parameter_space=parameter_space,
                n_calls=N_CALLS,
                n_initial_points=10,
                objective='sharpe_ratio',
                min_trades=10
            )
        else:
            log.warning("Bayesian optimizer not available, using Random Search")
            optimizer = RandomSearchOptimizer(seed=42, verbose=True)
            opt_result = opt_result = optimizer.optimize(
                backtest_engine=engine,
                data=data,
                strategy_class=LiquiditySweepStrategy,
                parameter_space=parameter_space,
                n_iterations=N_CALLS,
                objective='sharpe_ratio',
                min_trades=10
            )
        
        print()
        print(f"✅ Optimization complete:")
        print(f"   Best Sharpe: {opt_result['best_score']:.3f}")
        print(f"   Valid configs: {opt_result['valid_evaluations']}/{opt_result['total_evaluations']}")
        print(f"   Best parameters:")
        for param, value in opt_result['best_parameters'].items():
            print(f"      - {param}: {value}")
        print()
        
        # ===== STEP 4: Walk-Forward Validation =====
        print("Step 4: Walk-forward validation...")
        print("-" * 80)
        
        validator = WalkForwardValidator(
            train_window_days=60,
            test_window_days=30,
            gap_days=7
        )
        
        validation_result = validator.validate(
            config=opt_result['best_parameters'],
            data=data,
            strategy_class=LiquiditySweepStrategy,
            backtest_engine=engine
        )
        
        print()
        print(validator.get_validation_summary(validation_result))
        print()
        
        # ===== STEP 5: Save Configuration =====
        print("Step 5: Saving configuration to database...")
        print("-" * 80)
        
        # Re-run backtest with best params for full metrics
        final_strategy = LiquiditySweepStrategy(opt_result['best_parameters'])
        final_result = engine.run_backtest(data=data, strategy_instance=final_strategy)
        
        writer = ConfigurationWriter()
        config_id = await writer.save_configuration(
            strategy='LIQUIDITY_SWEEP',
            symbol=SYMBOL,
            exchange=EXCHANGE,
            timeframe=TIMEFRAME,
            parameters=opt_result['best_parameters'],
            backtest_result=final_result,
            validation_result=validation_result,
            optimizer=opt_result['optimizer'],
            metadata={
                'test_run': True,
                'n_evaluations': N_CALLS
            }
        )
        
        print(f"✅ Configuration saved: {config_id}")
        print()
        
        # ===== FINAL SUMMARY =====
        print("=" * 80)
        print("TEST COMPLETE - SUMMARY")
        print("=" * 80)
        print()
        print(f"Configuration ID: {config_id}")
        print(f"Lifecycle Stage: {validation_result.aggregate_metrics.get('test_sharpe_ratio', 0) >= 1.5 and 'MATURE' or 'VALIDATION'}")
        print()
        print("Metrics:")
        print(f"  - Sharpe Ratio: {opt_result['best_metrics']['sharpe_ratio']:.2f}")
        print(f"  - Net Profit: {opt_result['best_metrics']['net_profit_pct']:.2f}%")
        print(f"  - Win Rate: {opt_result['best_metrics']['gross_win_rate']:.2%}")
        print(f"  - Total Trades: {opt_result['best_metrics']['total_trades']}")
        print(f"  - Max Drawdown: {opt_result['best_metrics']['max_drawdown_pct']:.2f}%")
        print()
        print("Validation:")
        print(f"  - Test Sharpe: {validation_result.aggregate_metrics['test_sharpe_ratio']:.2f}")
        print(f"  - Stability Score: {validation_result.stability_score:.2f}")
        print(f"  - Overfitting: {'YES ⚠️' if validation_result.overfitting_detected else 'NO ✅'}")
        print()
        
        if validation_result.overfitting_detected:
            print("⚠️  WARNING: Overfitting detected!")
            print("   Configuration moved to PAPER stage")
            print("   Reasons:")
            for reason in validation_result.overfitting_reasons:
                print(f"     - {reason}")
        else:
            print("✅ SUCCESS: Configuration ready for production!")
            print("   Check V2 dashboard to see the new configuration")
        
        print()
        print("=" * 80)
        
        return {
            'success': True,
            'config_id': config_id,
            'metrics': opt_result['best_metrics'],
            'validation': validation_result
        }
        
    except Exception as e:
        log.error(f"Test failed: {e}", exc_info=True)
        print()
        print("=" * 80)
        print("TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Run test."""
    result = asyncio.run(test_end_to_end())
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
