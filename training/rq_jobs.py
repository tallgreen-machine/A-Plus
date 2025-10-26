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
    lookback_candles: int,  # Changed from lookback_days to lookback_candles
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
        
        # Step 1: Data Preparation (0-25%)
        await progress.start('data_preparation', {
            'symbol': symbol,
            'exchange': exchange,
            'timeframe': timeframe,
            'lookback_candles': lookback_candles
        })
        
        collector = DataCollector(db_url=db_url)
        data = await collector.fetch_ohlcv(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            lookback_candles=lookback_candles  # Now using candles directly
        )
        
        if data is None or len(data) < 100:
            raise ValueError(f"Insufficient data: {len(data) if data is not None else 0} candles")
        
        await progress.update(step_percentage=100.0)  # Indicators calculated
        log.info(f"✅ Data prepared: {len(data)} candles")
        
        # Step 2: Optimization (25-75%)
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
        
        # Shared state for progress tracking
        log.info("🔧 Setting up progress tracking...")
        import time
        import threading
        
        progress_state = {
            'iteration': 0,
            'total': n_iterations,
            'score': 0.0,
            'last_update_pct': 0.0,
            'running': True,
            'last_iteration_time': time.time(),
            'avg_iteration_duration': 5.0  # Initial estimate
        }
        
        # Background thread that interpolates progress between iterations
        def progress_interpolation_thread():
            """Update progress smoothly between iterations"""
            import psycopg2
            import os
            
            while progress_state['running']:
                try:
                    current_iteration = progress_state['iteration']
                    total = progress_state['total']
                    
                    if current_iteration == 0 or current_iteration >= total:
                        time.sleep(0.5)
                        continue
                    
                    # Calculate time since last iteration
                    elapsed = time.time() - progress_state['last_iteration_time']
                    avg_duration = progress_state['avg_iteration_duration']
                    
                    # Estimate progress within current iteration (0-1)
                    if avg_duration > 0:
                        sub_iteration_progress = min(elapsed / avg_duration, 0.99)
                    else:
                        sub_iteration_progress = 0.5
                    
                    # Calculate interpolated iteration count
                    interpolated_iteration = current_iteration + sub_iteration_progress
                    step_pct = (interpolated_iteration / total) * 100
                    
                    # Calculate overall percentage
                    previous_weight = 0.25  # data_preparation step
                    current_contribution = 0.50 * (step_pct / 100.0)  # optimization step is 50% of total
                    overall_pct = (previous_weight + current_contribution) * 100
                    
                    # Only update if changed by at least 0.1%
                    if abs(overall_pct - progress_state['last_update_pct']) >= 0.1:
                        progress_state['last_update_pct'] = overall_pct
                        
                        # Update database
                        db_host = os.getenv('DB_HOST', 'localhost')
                        db_port = os.getenv('DB_PORT', '5432')
                        db_user = os.getenv('DB_USER', 'traduser')
                        db_pass = os.getenv('DB_PASSWORD', 'TRAD123!')
                        db_name = os.getenv('DB_NAME', 'trad')
                        
                        conn = psycopg2.connect(
                            host=db_host, port=db_port, user=db_user,
                            password=db_pass, dbname=db_name
                        )
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE training_jobs
                            SET progress = %s,
                                current_episode = %s,
                                total_episodes = %s,
                                current_stage = 'Training'
                            WHERE id = %s
                        """, (
                            round(overall_pct, 2),  # Changed to 2 decimal places
                            int(interpolated_iteration),
                            total,
                            int(job_id)
                        ))
                        conn.commit()
                        cur.close()
                        conn.close()
                        
                        log.info(f"🔄 Interpolated progress: {overall_pct:.2f}% (iter {interpolated_iteration:.1f}/{total})")  # Changed to 2 decimal places
                
                except Exception as e:
                    log.error(f"❌ Interpolation error: {e}")
                
                # Update every 500ms
                time.sleep(0.5)
        
        # Start interpolation thread
        interpolation_thread = threading.Thread(target=progress_interpolation_thread, daemon=True)
        interpolation_thread.start()
        log.info("✅ Progress interpolation thread started")
        
        # Define progress callback for fine-grained updates
        def optimization_progress_callback(iteration: int, total: int, score: float, current_candle: int = 0, total_candles: int = 0):
            """
            Store progress state and update database with iteration + candle progress.
            
            Args:
                iteration: Current iteration number
                total: Total iterations
                score: Current objective score
                current_candle: Current candle being processed (0 if iteration complete)
                total_candles: Total candles in dataset
            """
            try:
                # Update timing for interpolation
                current_time = time.time()
                if progress_state['iteration'] > 0:
                    duration = current_time - progress_state['last_iteration_time']
                    # Exponential moving average
                    progress_state['avg_iteration_duration'] = (
                        0.7 * progress_state['avg_iteration_duration'] + 0.3 * duration
                    )
                
                progress_state['iteration'] = iteration
                progress_state['total'] = total
                progress_state['score'] = score
                progress_state['last_iteration_time'] = current_time
                
                # Calculate percentage within THIS STEP (optimization is 25-75%, so 50% of total)
                step_pct = (iteration / total) * 100
                
                # Add sub-iteration progress from candles
                if total_candles > 0 and current_candle > 0:
                    candle_pct = (current_candle / total_candles)
                    # This candle progress represents progress WITHIN the current iteration
                    # So we add a fraction of the per-iteration percentage
                    per_iteration_pct = 100.0 / total
                    step_pct = ((iteration - 1) / total) * 100 + (candle_pct * per_iteration_pct)
                
                # Log with candle info if available
                if total_candles > 0 and current_candle > 0:
                    log.info(f"🔔 Callback: iter {iteration}/{total} ({step_pct:.2f}%), candle {current_candle}/{total_candles}, score={score:.4f}")
                else:
                    log.info(f"🔔 Callback: iter {iteration}/{total} ({step_pct:.2f}%), score={score:.4f}")
                
                # Update DB every 0.1% for fine-grained progress
                if abs(step_pct - progress_state['last_update_pct']) >= 0.1 or iteration == total:
                    progress_state['last_update_pct'] = step_pct
                    
                    log.info(f"💾 Updating DB: step_pct={step_pct:.2f}%")
                    
                    # Use synchronous psycopg2 instead of asyncpg since we're in a thread
                    import psycopg2
                    import os
                    
                    try:
                        # Calculate overall percentage (with 2 decimal places)
                        previous_weight = 0.25  # data_preparation step
                        current_contribution = 0.50 * (step_pct / 100.0)  # optimization step is 50% of total
                        overall_pct = (previous_weight + current_contribution) * 100
                        
                        # Build connection from environment variables
                        db_host = os.getenv('DB_HOST', 'localhost')
                        db_port = os.getenv('DB_PORT', '5432')
                        db_user = os.getenv('DB_USER', 'traduser')
                        db_pass = os.getenv('DB_PASSWORD', 'TRAD123!')
                        db_name = os.getenv('DB_NAME', 'trad')
                        
                        # Connect and update
                        conn = psycopg2.connect(
                            host=db_host,
                            port=db_port,
                            user=db_user,
                            password=db_pass,
                            dbname=db_name
                        )
                        cur = conn.cursor()
                        
                        cur.execute("""
                            UPDATE training_jobs
                            SET progress = %s,
                                current_episode = %s,
                                total_episodes = %s,
                                current_candle = %s,
                                total_candles = %s,
                                current_reward = %s,
                                current_loss = %s,
                                current_stage = 'Training'
                            WHERE id = %s
                        """, (
                            round(overall_pct, 2),  # Changed to 2 decimal places
                            iteration,
                            total,
                            current_candle if current_candle > 0 else None,
                            total_candles if total_candles > 0 else None,
                            score if score > 0 else None,
                            abs(score) if score < 0 else None,
                            int(job_id)
                        ))
                        
                        conn.commit()
                        cur.close()
                        conn.close()
                        
                        log.info(f"✅ DB updated: {overall_pct:.2f}%")  # Changed to 2 decimal places
                    except Exception as e:
                        log.error(f"❌ Failed to update DB: {e}")
                    
            except Exception as e:
                log.error(f"❌ Error in callback: {e}", exc_info=True)
        
        log.info("✅ Progress callback defined")
        
        # Run optimization with all required parameters
        # Run in executor to avoid blocking the event loop
        log.info(f"🚀 Starting {optimizer} optimization with {n_iterations} iterations...")
        import concurrent.futures
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            log.info("✅ ThreadPoolExecutor created, submitting optimization task...")
            if optimizer == 'bayesian':
                # BayesianOptimizer uses n_calls instead of n_iterations
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
                        progress_callback=optimization_progress_callback
                    )
                )
            elif optimizer == 'random':
                # RandomSearchOptimizer uses n_iterations
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
                        progress_callback=optimization_progress_callback
                    )
                )
            else:
                # GridSearchOptimizer doesn't use n_iterations (tests all combinations)
                result = await loop.run_in_executor(
                    executor,
                    lambda: opt.optimize(
                        backtest_engine=backtest_engine,
                        data=data,
                        strategy_class=LiquiditySweepStrategy,
                        parameter_space=parameter_space,
                        objective='sharpe_ratio',
                        min_trades=10,
                        progress_callback=optimization_progress_callback
                    )
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
    lookback_candles: int,  # Changed from lookback_days
    n_iterations: int,
    run_validation: bool
) -> Dict[str, Any]:
    """
    Sync wrapper for the training job (called by RQ).
    Runs the async function in an event loop.
    """
    return asyncio.run(_run_training_job_async(
        job_id, strategy, symbol, exchange, timeframe, regime,
        optimizer, lookback_candles, n_iterations, run_validation
    ))
