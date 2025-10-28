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


class ProgressCallback:
    """
    Picklable progress callback that can be serialized and sent to worker processes.
    
    This class captures the job_id at initialization and can be safely pickled
    by joblib for use in parallel worker processes.
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.last_log_time = 0
        
    def __call__(self, iteration: int, total: int, score: float):
        """
        Store progress state and update database with iteration progress.
        
        This callback runs inside parallel worker processes, so it needs
        its own database connection.
        
        Args:
            iteration: Current iteration number
            total: Total iterations
            score: Current objective score
        """
        import time
        import psycopg2
        
        try:
            # Calculate percentage within THIS STEP (optimization is 0-100%)
            step_pct = (iteration / total) * 100
            
            # Throttle logging to every 1 second
            current_time = time.time()
            if current_time - self.last_log_time >= 1.0:
                log.info(f"🔔 Progress: iter {iteration}/{total} ({step_pct:.1f}%), score={score:.4f}")
                self.last_log_time = current_time
            
            # Update DB less frequently (every 5% or on iteration completion)
            needs_update = (iteration % max(1, total // 20) == 0) or iteration == total
            
            if needs_update:
                try:
                    # Build connection from environment variables
                    db_host = os.getenv('DB_HOST', 'localhost')
                    db_port = os.getenv('DB_PORT', '5432')
                    db_user = os.getenv('DB_USER', 'traduser')
                    db_pass = os.getenv('DB_PASSWORD', 'TRAD123!')
                    db_name = os.getenv('DB_NAME', 'trad')
                    
                    # Connect and update with timeout
                    conn = psycopg2.connect(
                        host=db_host,
                        port=db_port,
                        user=db_user,
                        password=db_pass,
                        dbname=db_name,
                        connect_timeout=5
                    )
                    cur = conn.cursor()
                    
                    # Convert numpy types to Python natives and handle infinity
                    score_value = float(score) if score is not None else None
                    if score_value is not None and (score_value == float('inf') or score_value == float('-inf')):
                        score_value = None  # Database can't store infinity
                    
                    cur.execute("""
                        UPDATE training_jobs
                        SET progress = %s,
                            current_episode = %s,
                            total_episodes = %s,
                            current_reward = %s,
                            current_loss = %s,
                            current_stage = 'Training'
                        WHERE id = %s
                    """, (
                        round(step_pct, 2),
                        iteration,
                        total,
                        score_value if score_value and score_value > 0 else None,
                        abs(score_value) if score_value and score_value < 0 else None,
                        int(self.job_id)
                    ))
                    
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    log.info(f"✅ DB updated: {step_pct:.1f}% (iter {iteration}/{total})")
                except Exception as e:
                    log.error(f"❌ DB update failed: {e}")
                    
        except Exception as e:
            log.error(f"❌ Callback error: {e}")


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
    lookback_candles: int,  # Changed from lookback_days to lookback_candles
    n_iterations: int,
    run_validation: bool,
    data_filter_config: Dict[str, Any] = None  # NEW: Data quality filtering config
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
        # Set job to 'running' immediately so frontend can start monitoring
        import asyncpg
        conn = await asyncpg.connect(db_url)
        await conn.execute(
            "UPDATE training_jobs SET status = 'running', started_at = NOW() WHERE id = $1",
            int(job_id)
        )
        await conn.close()
        log.info(f"Job {job_id} status set to 'running'")
        
        # Initialize progress tracker
        progress = ProgressTracker(job_id=job_id, db_url=db_url)
        
        # Step 1: Data Preparation (fast, don't show progress)
        log.info("🔧 Preparing data...")
        collector = DataCollector(db_url=db_url)
        data = await collector.fetch_ohlcv(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            lookback_candles=lookback_candles,  # Now using candles directly
            data_filter_config=data_filter_config  # NEW: Pass filter config
        )
        
        if data is None or len(data) < 100:
            raise ValueError(f"Insufficient data: {len(data) if data is not None else 0} candles")
        
        log.info(f"✅ Data prepared: {len(data)} candles")
        
        # Step 2: Optimization (0-100% of progress bar)
        log.info("🔧 Starting optimization step...")
        await progress.start('optimization', {
            'optimizer': optimizer,
            'n_iterations': n_iterations
        })
        log.info("✅ Progress tracker updated to optimization step")
        
        # Initialize backtest engine
        log.info("🔧 Initializing backtest engine...")
        backtest_engine = BacktestEngine(initial_capital=10000.0)
        log.info("✅ Backtest engine initialized")
        
        # Get parameter space
        log.info("🔧 Getting parameter space from strategy...")
        temp_strategy = LiquiditySweepStrategy({})  # Temp instance to get parameter space
        parameter_space = temp_strategy.get_parameter_space()
        log.info(f"✅ Parameter space obtained: {len(parameter_space)} parameters")
        
        # Select optimizer (don't pass n_iterations to __init__)
        log.info(f"🔧 Initializing {optimizer} optimizer...")
        if optimizer == 'bayesian':
            opt = BayesianOptimizer()
        elif optimizer == 'random':
            opt = RandomSearchOptimizer()
        elif optimizer == 'grid':
            opt = GridSearchOptimizer()
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")
        log.info(f"✅ Optimizer initialized: {opt.__class__.__name__}")
        
        # Shared state for progress tracking (no interpolation thread - relying on real callbacks)
        log.info("🔧 Setting up progress tracking...")
        import time
        
        progress_state = {
            'iteration': 0,
            'total': n_iterations,
            'score': 0.0,
            'last_update_pct': 0.0
        }
        
        # Create picklable progress callback for iteration-level updates
        optimization_progress_callback = ProgressCallback(job_id)
        log.info(f"✅ Progress callback created for job {job_id}")
        
        # Run optimization with all required parameters
        # Run in executor to avoid blocking the event loop
        log.info(f"🚀 Starting {optimizer} optimization with {n_iterations} iterations...")
        import concurrent.futures
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            log.info("✅ ThreadPoolExecutor created, submitting optimization task...")
            if optimizer == 'bayesian':
                # BayesianOptimizer with n_jobs for parallel initial points
                result = await loop.run_in_executor(
                    executor,
                    lambda: opt.optimize(
                        backtest_engine=backtest_engine,
                        data=data,
                        strategy_class=LiquiditySweepStrategy,
                        parameter_space=parameter_space,
                        n_calls=n_iterations,
                        objective='sharpe_ratio',
                        min_trades=10,
                        progress_callback=optimization_progress_callback,
                        n_jobs=-1  # Use all CPU cores
                    )
                )
            elif optimizer == 'random':
                # RandomSearchOptimizer with parallel execution enabled
                result = await loop.run_in_executor(
                    executor,
                    lambda: opt.optimize(
                        backtest_engine=backtest_engine,
                        data=data,
                        strategy_class=LiquiditySweepStrategy,
                        parameter_space=parameter_space,
                        n_iterations=n_iterations,
                        objective='sharpe_ratio',
                        min_trades=10,
                        progress_callback=optimization_progress_callback,
                        n_jobs=-1  # Use all CPU cores for parallel execution
                    )
                )
            else:
                # GridSearchOptimizer with parallel execution
                result = await loop.run_in_executor(
                    executor,
                    lambda: opt.optimize(
                        backtest_engine=backtest_engine,
                        data=data,
                        strategy_class=LiquiditySweepStrategy,
                        parameter_space=parameter_space,
                        objective='sharpe_ratio',
                        min_trades=10,
                        progress_callback=optimization_progress_callback,
                        n_jobs=-1  # Use all CPU cores
                    )
                )
        
        best_params = result['best_parameters']
        best_score = result['best_score']
        best_metrics = result['best_metrics']
        
        await progress.update(step_percentage=100.0)
        log.info(f"Optimization complete: best_score={best_score:.4f}")
        
        # Validation and save_config steps removed - optimization is now 0-100%
        validation_result = None
        
        # Run final backtest with best parameters
        engine = BacktestEngine()
        strategy_instance = LiquiditySweepStrategy(best_params)
        backtest_result = engine.run_backtest(data, strategy_instance)
        
        # Save configuration
        writer = ConfigurationWriter()
        config_id = await writer.save_configuration(
            strategy=strategy,  # Use the actual strategy name from job parameters
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            regime=regime,
            parameters=best_params,
            backtest_result=backtest_result,
            validation_result=validation_result,
            optimizer=optimizer,
            metadata={
                'job_id': int(job_id),
                'data_filter_config': data_filter_config  # NEW: Include filter settings in metadata
            }
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
    lookback_candles: int,  # Changed from lookback_days
    n_iterations: int,
    run_validation: bool,
    data_filter_config: Dict[str, Any] = None  # NEW: Data quality filtering config
) -> Dict[str, Any]:
    """
    Sync wrapper for the training job (called by RQ).
    Runs the async function in an event loop.
    """
    return asyncio.run(_run_training_job_async(
        job_id, strategy, symbol, exchange, timeframe, regime,
        optimizer, lookback_candles, n_iterations, run_validation, data_filter_config
    ))
