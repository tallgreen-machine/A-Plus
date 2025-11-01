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
    
    Uses Redis to track cumulative progress across parallel episodes.
    Each episode contributes proportionally to overall progress.
    
    This class captures the job_id at initialization and can be safely pickled
    by joblib for use in parallel worker processes.
    """
    
    def __init__(self, job_id: str, total_episodes: int):
        self.job_id = job_id
        self.total_episodes = total_episodes
        self.last_log_time = 0
        self.last_db_update_pct = -1  # Track last percentage to avoid excessive DB updates
        
    def __call__(self, episode_index: int, intra_progress: float, stage: str = 'signal_generation'):
        """
        Update progress for a specific episode.
        
        This callback runs inside parallel worker processes and updates Redis
        to track cumulative progress across all parallel episodes.
        
        Args:
            episode_index: The episode number (0-indexed)
            intra_progress: Progress within this episode (0.0 to 1.0)
            stage: Current stage (for logging, e.g., 'signal_generation')
        """
        import time
        import redis
        import psycopg2
        
        try:
            # Connect to Redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            # Update this episode's progress in Redis
            episode_key = f"training_job:{self.job_id}:episode:{episode_index}"
            
            if intra_progress >= 1.0:
                # Episode complete - only increment if not already counted
                # This makes completion idempotent (safe to call multiple times)
                if r.exists(episode_key):
                    r.delete(episode_key)
                    r.incr(f"training_job:{self.job_id}:completed_count")
            else:
                # Update in-progress
                # Convert to plain Python float to avoid numpy string representation
                r.set(episode_key, float(intra_progress))
            
            # Calculate total progress from Redis
            completed_count = int(r.get(f"training_job:{self.job_id}:completed_count") or 0)
            
            # Sum up all partial progress from in-flight episodes
            partial_sum = 0.0
            episode_keys = r.keys(f"training_job:{self.job_id}:episode:*")
            for key in episode_keys:
                partial_sum += float(r.get(key) or 0.0)
            
            # Total progress = completed episodes + partial progress from in-flight
            total_progress_pct = ((completed_count + partial_sum) / self.total_episodes) * 100
            
            # Throttle logging to every 1 second
            current_time = time.time()
            if current_time - self.last_log_time >= 1.0:
                log.info(f"🔔 Progress: {completed_count}/{self.total_episodes} complete, "
                        f"{len(episode_keys)} in-flight, {total_progress_pct:.1f}% total")
                self.last_log_time = current_time
            
            # Update database if progress changed by at least 0.5%
            if abs(total_progress_pct - self.last_db_update_pct) >= 0.5:
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
                    
                    # Update database with aggregated progress
                    cur.execute("""
                        UPDATE training_jobs
                        SET progress = %s,
                            current_episode = %s,
                            total_episodes = %s,
                            current_stage = 'Training'
                        WHERE job_id = %s
                    """, (
                        round(total_progress_pct, 2),
                        completed_count,  # Show only completed episodes
                        self.total_episodes,
                        self.job_id
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    self.last_db_update_pct = total_progress_pct
                    
                except Exception as e:
                    log.debug(f"DB update failed: {e}")
            
        except Exception as e:
            log.error(f"Progress callback failed: {e}", exc_info=True)


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
    data_filter_config: Dict[str, Any] = None,  # Data quality filtering config
    seed: int = 42  # NEW: Seed for reproducible parameter optimization
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
    from training.strategies.capitulation_reversal import CapitulationReversalStrategy
    from training.strategies.failed_breakdown import FailedBreakdownStrategy
    from training.configuration_writer import ConfigurationWriter
    from training.backtest_engine import BacktestEngine
    
    log.info(f"Starting training job {job_id}: {strategy} {symbol} on {exchange} ({timeframe})")
    
    # Map strategy names to classes
    STRATEGY_MAP = {
        'LIQUIDITY_SWEEP': LiquiditySweepStrategy,
        'CAPITULATION_REVERSAL': CapitulationReversalStrategy,
        'FAILED_BREAKDOWN': FailedBreakdownStrategy,
    }
    
    # Get strategy class from name
    strategy_class = STRATEGY_MAP.get(strategy)
    if strategy_class is None:
        raise ValueError(
            f"Unknown strategy '{strategy}'. "
            f"Available strategies: {', '.join(STRATEGY_MAP.keys())}"
        )
    
    log.info(f"Using strategy class: {strategy_class.__name__}")
    
    db_url = get_db_url()
    
    try:
        # Set job to 'running' immediately so frontend can start monitoring
        import asyncpg
        conn = await asyncpg.connect(db_url)
        
        # Get the integer database ID for this job (needed for trained_configurations.job_id)
        training_job_int_id = await conn.fetchval(
            "SELECT id FROM training_jobs WHERE job_id = $1", job_id
        )
        
        await conn.execute(
            "UPDATE training_jobs SET status = 'running', started_at = NOW() WHERE job_id = $1",
            job_id
        )
        await conn.close()
        log.info(f"Job {job_id} (ID #{training_job_int_id}) status set to 'running'")
        
        # Initialize progress tracker with both UUID and integer IDs
        progress = ProgressTracker(job_id=job_id, db_url=db_url, job_id_int=training_job_int_id)
        
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
        log.info(f"🔧 Getting parameter space from strategy: {strategy_class.__name__}...")
        temp_strategy = strategy_class({})  # Temp instance to get parameter space
        parameter_space = temp_strategy.get_parameter_space()
        log.info(f"✅ Parameter space obtained: {len(parameter_space)} parameters")
        
        # Select optimizer with seed for reproducibility
        log.info(f"🔧 Initializing {optimizer} optimizer with seed={seed}...")
        if optimizer == 'bayesian':
            opt = BayesianOptimizer(random_state=seed)  # ✅ WITH SEED
        elif optimizer == 'random':
            opt = RandomSearchOptimizer(seed=seed)  # ✅ WITH SEED
        elif optimizer == 'grid':
            opt = GridSearchOptimizer()  # No seed needed - deterministic by nature
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")
        log.info(f"✅ Optimizer initialized: {opt.__class__.__name__} (seed={seed} for reproducibility)")
        
        # Shared state for progress tracking (no interpolation thread - relying on real callbacks)
        log.info("🔧 Setting up progress tracking...")
        import redis
        
        # Initialize Redis progress tracking
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.set(f"training_job:{job_id}:completed_count", 0)
        r.set(f"training_job:{job_id}:total", n_iterations)
        
        # Create picklable progress callback with cumulative tracking
        optimization_progress_callback = ProgressCallback(job_id, n_iterations)
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
                        strategy_class=strategy_class,
                        parameter_space=parameter_space,
                        n_calls=n_iterations,
                        objective='sharpe_ratio',
                        min_trades=5,  # Lowered from 10 for rare pattern strategies
                        # Reason: 20k candles = 69 days. Rare strategies (20-50/year) = 3.8-9.6 trades
                        # in 69 days. min_trades=5 allows these to pass validation.
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
                        strategy_class=strategy_class,
                        parameter_space=parameter_space,
                        n_iterations=n_iterations,
                        objective='sharpe_ratio',
                        min_trades=5,  # Lowered from 10 for rare pattern strategies
                        # Reason: 20k candles = 69 days. Rare strategies (20-50/year) = 3.8-9.6 trades
                        # in 69 days. min_trades=5 allows these to pass validation.
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
                        strategy_class=strategy_class,
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
        strategy_instance = strategy_class(best_params)
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
                'job_id': job_id,  # UUID for logging
                'job_id_int': training_job_int_id,  # INTEGER for database display
                'data_filter_config': data_filter_config  # NEW: Include filter settings in metadata
            }
        )
        
        # Update training_jobs with the saved configuration ID
        import asyncpg
        conn = await asyncpg.connect(db_url)
        await conn.execute(
            "UPDATE training_jobs SET config_id = $1 WHERE job_id = $2",
            config_id,
            job_id
        )
        await conn.close()
        log.info(f"Linked training job {job_id} to configuration {config_id}")
        
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
            # Get integer ID for error logging
            import asyncpg
            conn = await asyncpg.connect(db_url)
            training_job_int_id = await conn.fetchval(
                "SELECT id FROM training_jobs WHERE job_id = $1", job_id
            )
            await conn.close()
            
            progress = ProgressTracker(job_id, db_url, job_id_int=training_job_int_id)
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
    data_filter_config: Dict[str, Any] = None,  # Data quality filtering config
    seed: int = 42  # NEW: Seed for reproducible parameter optimization
) -> Dict[str, Any]:
    """
    Sync wrapper for the training job (called by RQ).
    Runs the async function in an event loop.
    """
    return asyncio.run(_run_training_job_async(
        job_id, strategy, symbol, exchange, timeframe, regime,
        optimizer, lookback_candles, n_iterations, run_validation, data_filter_config, seed
    ))
