"""
Training Jobs for RQ Worker

Defines training tasks that run in the worker process.
These are standalone functions that can be serialized and executed by RQ.
"""

import logging
import asyncio
import os
from typing import Dict, Any
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def get_db_url() -> str:
    """Get database URL from environment variables."""
    # Try DATABASE_URL first
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Try DB_* environment variables (trad.env format)
    db_host = os.getenv('DB_HOST')
    if db_host:
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME')
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fallback to localhost
    return "postgresql://traduser:TRAD123!@localhost:5432/trad"


async def _run_training_job_async(
    job_id: str,
    strategy: str,
    symbol: str,
    exchange: str,
    timeframe: str,
    regime: str,
    optimizer: str,
    lookback_days: int,
    n_iterations: int,
    run_validation: bool
) -> Dict[str, Any]:
    """
    Execute training job in worker process.
    
    This is an async function called by the sync wrapper.
    All database and I/O operations use await.
    """
    from training.progress_tracker import ProgressTracker
    from training.data_collector import DataCollector
    from training.optimizers.random_search import RandomSearchOptimizer
    from training.optimizers.bayesian import BayesianOptimizer
    from training.optimizers.grid_search import GridSearchOptimizer
    from training.strategies.liquidity_sweep import LiquiditySweepStrategy
    from training.configuration_writer import ConfigurationWriter
    from training.backtest_engine import BacktestEngine
    
    log.info(f"Starting training job {job_id}: {strategy} {symbol} on {exchange} ({timeframe})")
    
    db_url = get_db_url()
    
    try:
        # Initialize progress tracker
        progress = ProgressTracker(job_id=job_id, db_url=db_url)
        
        # Step 1: Data Preparation (0-25%)
        await progress.start('data_preparation', {
            'symbol': symbol,
            'exchange': exchange,
            'timeframe': timeframe,
            'lookback_days': lookback_days
        })
        
        collector = DataCollector(db_url=db_url)
        data = await collector.fetch_ohlcv(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            lookback_days=lookback_days
        )
        
        if data is None or len(data) < 100:
            raise ValueError(f"Insufficient data: {len(data) if data is not None else 0} candles")
        
        await progress.update(step_percentage=100.0)
        log.info(f"Data prepared: {len(data)} candles")
        
        # Step 2: Optimization (25-75%)
        await progress.start('optimization', {
            'optimizer': optimizer,
            'n_iterations': n_iterations
        })
        
        # Initialize backtest engine
        backtest_engine = BacktestEngine(initial_capital=10000.0)
        
        # Get parameter space
        temp_strategy = LiquiditySweepStrategy({})  # Temp instance to get parameter space
        parameter_space = temp_strategy.get_parameter_space()
        
        # Select optimizer (don't pass n_iterations to __init__)
        if optimizer == 'bayesian':
            opt = BayesianOptimizer()
        elif optimizer == 'random':
            opt = RandomSearchOptimizer()
        elif optimizer == 'grid':
            opt = GridSearchOptimizer()
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")
        
        # Define optimization callback
        def optimization_callback(iteration: int, score: float, params: Dict[str, Any]):
            pct = (iteration / n_iterations) * 100
            asyncio.create_task(progress.update(
                step_percentage=pct,
                iteration=iteration,
                scores={'current': score},
                params=params
            ))
        
        # Run optimization with all required parameters
        if optimizer == 'bayesian':
            # BayesianOptimizer uses n_calls instead of n_iterations
            result = opt.optimize(
                backtest_engine=backtest_engine,
                data=data,
                strategy_class=LiquiditySweepStrategy,
                parameter_space=parameter_space,
                n_calls=n_iterations,
                objective='sharpe_ratio',
                min_trades=10
            )
        else:
            # RandomSearchOptimizer and GridSearchOptimizer use n_iterations
            result = opt.optimize(
                backtest_engine=backtest_engine,
                data=data,
                strategy_class=LiquiditySweepStrategy,
                parameter_space=parameter_space,
                n_iterations=n_iterations,
                objective='sharpe_ratio',
                min_trades=10
            )
        
        best_params = result['best_parameters']
        best_score = result['best_score']
        best_metrics = result['best_metrics']
        
        await progress.update(step_percentage=100.0)
        log.info(f"Optimization complete: best_score={best_score:.4f}")
        
        # Step 3: Validation (75-95%) - optional (skip for now)
        await progress.start('validation', {'skipped': True})
        await progress.update(step_percentage=100.0)
        validation_result = None
        
        # Step 4: Save Configuration (95-100%)
        await progress.start('save_config', {
            'config_destination': 'trained_configurations'
        })
        
        # Run final backtest with best parameters
        engine = BacktestEngine()
        strategy_instance = LiquiditySweepStrategy(best_params)
        backtest_result = engine.run_backtest(data, strategy_instance)
        
        # Save configuration
        writer = ConfigurationWriter()
        config_id = await writer.save_configuration(
            strategy='LIQUIDITY_SWEEP',  # Pass strategy name as string
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            regime=regime,
            parameters=best_params,
            backtest_result=backtest_result,
            validation_result=validation_result,
            optimizer=optimizer
        )
        
        await progress.complete()
        
        log.info(f"Training job {job_id} completed successfully: {config_id}")
        
        return {
            'status': 'success',
            'config_id': config_id,
            'best_score': best_score,
            'best_params': best_params,
            'metrics': backtest_result.metrics
        }
        
    except Exception as e:
        log.error(f"Training job {job_id} failed: {e}", exc_info=True)
        
        # Update progress with error
        try:
            db_url = get_db_url()
            progress = ProgressTracker(job_id, db_url)
            await progress.error(str(e))
        except:
            pass
        
        return {
            'status': 'error',
            'error': str(e)
        }


def run_training_job(
    job_id: str,
    strategy: str,
    symbol: str,
    exchange: str,
    timeframe: str,
    regime: str,
    optimizer: str,
    lookback_days: int,
    n_iterations: int,
    run_validation: bool
) -> Dict[str, Any]:
    """
    Sync wrapper for the training job (called by RQ).
    Runs the async function in an event loop.
    """
    return asyncio.run(_run_training_job_async(
        job_id, strategy, symbol, exchange, timeframe, regime,
        optimizer, lookback_days, n_iterations, run_validation
    ))
