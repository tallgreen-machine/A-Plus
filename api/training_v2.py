"""
V2 Training API Router

Provides REST endpoints for the V2 training system:
- POST /api/v2/training/start - Start training job
- GET /api/v2/training/jobs - List training jobs
- GET /api/v2/training/jobs/{job_id} - Get job status
- GET /api/v2/training/jobs/{job_id}/results - Get job results
- DELETE /api/v2/training/jobs/{job_id} - Cancel job

Integrates with training/ components for ML-powered parameter optimization.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio
import uuid
import logging
import traceback

from training.data_collector import DataCollector
from training.backtest_engine import BacktestEngine
from training.strategies.liquidity_sweep import LiquiditySweepStrategy
from training.optimizers.grid_search import GridSearchOptimizer
from training.optimizers.random_search import RandomSearchOptimizer
from training.optimizers.bayesian import BayesianOptimizer, is_bayesian_available
from training.validator import WalkForwardValidator
from training.configuration_writer import ConfigurationWriter

# Database imports
import asyncpg
import os
from configparser import ConfigParser

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/training", tags=["Training V2"])

# ===== Request/Response Models =====

class StartTrainingRequest(BaseModel):
    """Request body for starting a training job."""
    strategy: str = Field(..., description="Strategy name (e.g., LIQUIDITY_SWEEP)")
    symbol: str = Field(..., description="Trading pair (e.g., BTC/USDT)")
    exchange: str = Field(..., description="Exchange name (e.g., binance)")
    timeframe: str = Field(..., description="Timeframe (e.g., 5m, 1h)")
    optimizer: str = Field(
        default="bayesian",
        description="Optimizer: grid, random, or bayesian"
    )
    lookback_days: int = Field(default=90, description="Days of historical data")
    n_iterations: Optional[int] = Field(
        default=200,
        description="Iterations for random/bayesian optimizer"
    )
    run_validation: bool = Field(
        default=True,
        description="Run walk-forward validation"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "strategy": "LIQUIDITY_SWEEP",
                "symbol": "BTC/USDT",
                "exchange": "binance",
                "timeframe": "5m",
                "optimizer": "bayesian",
                "lookback_days": 90,
                "n_iterations": 200,
                "run_validation": True
            }
        }


class TrainingJobResponse(BaseModel):
    """Response for training job."""
    job_id: str
    status: str
    strategy: str
    symbol: str
    exchange: str
    timeframe: str
    optimizer: str
    progress_pct: float
    current_iteration: Optional[int]
    total_iterations: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_message: Optional[str]


class TrainingResultsResponse(BaseModel):
    """Response for training job results."""
    job_id: str
    status: str
    config_id: Optional[str]
    best_score: Optional[float]
    best_parameters: Optional[Dict[str, Any]]
    best_metrics: Optional[Dict[str, Any]]
    validation_summary: Optional[Dict[str, Any]]


# ===== Database Helper =====

def get_db_url() -> str:
    """Get database URL from config."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    config = ConfigParser()
    config.read('config.ini')
    
    if 'database' in config:
        db_config = config['database']
        return (
            f"postgresql://{db_config.get('user', 'traduser')}:"
            f"{db_config.get('password', '')}@"
            f"{db_config.get('host', 'localhost')}:"
            f"{db_config.get('port', '5432')}/"
            f"{db_config.get('database', 'traddb')}"
        )
    
    return "postgresql://traduser:tradpass@localhost:5432/traddb"


# ===== Background Training Task =====

async def run_training_task(
    job_id: str,
    request: StartTrainingRequest
):
    """
    Run training job in background.
    
    Updates database with progress and results.
    """
    db_url = get_db_url()
    
    try:
        # Update status to RUNNING
        conn = await asyncpg.connect(db_url)
        await conn.execute(
            """
            UPDATE training_jobs 
            SET status = 'RUNNING', started_at = $1, progress_pct = 0
            WHERE job_id = $2
            """,
            datetime.now(timezone.utc),
            job_id
        )
        await conn.close()
        
        log.info(f"Training job {job_id} started: {request.strategy} {request.symbol}")
        
        # ===== Step 1: Data Collection =====
        log.info(f"[{job_id}] Step 1/5: Collecting data...")
        collector = DataCollector(db_url=db_url)
        data = await collector.fetch_ohlcv(
            symbol=request.symbol,
            exchange=request.exchange,
            timeframe=request.timeframe,
            lookback_days=request.lookback_days
        )
        
        # Update progress
        conn = await asyncpg.connect(db_url)
        await conn.execute(
            "UPDATE training_jobs SET progress_pct = 20 WHERE job_id = $1",
            job_id
        )
        await conn.close()
        
        # ===== Step 2: Get Parameter Space =====
        log.info(f"[{job_id}] Step 2/5: Defining parameter space...")
        
        # Map strategy name to class
        strategy_map = {
            'LIQUIDITY_SWEEP': LiquiditySweepStrategy
        }
        
        strategy_class = strategy_map.get(request.strategy)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {request.strategy}")
        
        temp_strategy = strategy_class({})
        parameter_space = temp_strategy.get_parameter_space()
        
        # ===== Step 3: Optimization =====
        log.info(f"[{job_id}] Step 3/5: Running {request.optimizer} optimization...")
        
        engine = BacktestEngine(
            initial_capital=10000,
            fee_rate=0.001,
            slippage_rate=0.0005
        )
        
        # Select optimizer
        if request.optimizer == 'grid':
            optimizer = GridSearchOptimizer(verbose=False)
            opt_result = optimizer.optimize(
                backtest_engine=engine,
                data=data,
                strategy_class=strategy_class,
                parameter_space=parameter_space,
                objective='sharpe_ratio',
                min_trades=10
            )
        elif request.optimizer == 'random':
            optimizer = RandomSearchOptimizer(seed=42, verbose=False)
            opt_result = optimizer.optimize(
                backtest_engine=engine,
                data=data,
                strategy_class=strategy_class,
                parameter_space=parameter_space,
                n_iterations=request.n_iterations,
                objective='sharpe_ratio',
                min_trades=10
            )
        elif request.optimizer == 'bayesian':
            if not is_bayesian_available():
                raise ValueError("Bayesian optimizer not available. Install scikit-optimize.")
            optimizer = BayesianOptimizer(random_state=42, verbose=False)
            opt_result = optimizer.optimize(
                backtest_engine=engine,
                data=data,
                strategy_class=strategy_class,
                parameter_space=parameter_space,
                n_calls=request.n_iterations,
                n_initial_points=max(10, request.n_iterations // 10),
                objective='sharpe_ratio',
                min_trades=10
            )
        else:
            raise ValueError(f"Unknown optimizer: {request.optimizer}")
        
        # Update progress
        conn = await asyncpg.connect(db_url)
        await conn.execute(
            "UPDATE training_jobs SET progress_pct = 60 WHERE job_id = $1",
            job_id
        )
        await conn.close()
        
        # ===== Step 4: Validation (Optional) =====
        validation_result = None
        
        if request.run_validation:
            log.info(f"[{job_id}] Step 4/5: Walk-forward validation...")
            
            validator = WalkForwardValidator(
                train_window_days=60,
                test_window_days=30,
                gap_days=7
            )
            
            validation_result = validator.validate(
                config=opt_result['best_parameters'],
                data=data,
                strategy_class=strategy_class,
                backtest_engine=engine
            )
        
        # Update progress
        conn = await asyncpg.connect(db_url)
        await conn.execute(
            "UPDATE training_jobs SET progress_pct = 80 WHERE job_id = $1",
            job_id
        )
        await conn.close()
        
        # ===== Step 5: Save Configuration =====
        log.info(f"[{job_id}] Step 5/5: Saving configuration...")
        
        # Re-run backtest with best params for full metrics
        final_strategy = strategy_class(opt_result['best_parameters'])
        final_result = engine.run_backtest(data=data, strategy_instance=final_strategy)
        
        writer = ConfigurationWriter(db_url=db_url)
        config_id = await writer.save_configuration(
            strategy=request.strategy,
            symbol=request.symbol,
            exchange=request.exchange,
            timeframe=request.timeframe,
            parameters=opt_result['best_parameters'],
            backtest_result=final_result,
            validation_result=validation_result,
            optimizer=request.optimizer,
            metadata={
                'job_id': job_id,
                'lookback_days': request.lookback_days,
                'n_iterations': request.n_iterations
            }
        )
        
        # ===== Update Job Status: COMPLETED =====
        completed_at = datetime.now(timezone.utc)
        
        conn = await asyncpg.connect(db_url)
        
        # Get started_at to calculate duration
        row = await conn.fetchrow(
            "SELECT started_at FROM training_jobs WHERE job_id = $1",
            job_id
        )
        
        duration_seconds = None
        if row and row['started_at']:
            duration_seconds = int((completed_at - row['started_at']).total_seconds())
        
        await conn.execute(
            """
            UPDATE training_jobs 
            SET 
                status = 'COMPLETED',
                progress_pct = 100,
                completed_at = $1,
                duration_seconds = $2,
                best_config_id = $3,
                best_score = $4,
                best_parameters = $5,
                best_metrics = $6
            WHERE job_id = $7
            """,
            completed_at,
            duration_seconds,
            config_id,
            opt_result['best_score'],
            opt_result['best_parameters'],
            opt_result['best_metrics'],
            job_id
        )
        
        await conn.close()
        
        log.info(
            f"✅ Training job {job_id} completed: "
            f"config_id={config_id}, "
            f"best_score={opt_result['best_score']:.3f}, "
            f"duration={duration_seconds}s"
        )
        
    except Exception as e:
        log.error(f"Training job {job_id} failed: {e}", exc_info=True)
        
        # Update status to FAILED
        try:
            conn = await asyncpg.connect(db_url)
            await conn.execute(
                """
                UPDATE training_jobs 
                SET 
                    status = 'FAILED',
                    completed_at = $1,
                    error_message = $2,
                    error_trace = $3
                WHERE job_id = $4
                """,
                datetime.now(timezone.utc),
                str(e),
                traceback.format_exc(),
                job_id
            )
            await conn.close()
        except Exception as db_error:
            log.error(f"Failed to update job status: {db_error}")


# ===== API Endpoints =====

@router.post("/start", response_model=TrainingJobResponse)
async def start_training(
    request: StartTrainingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new training job.
    
    The job runs asynchronously in the background. Use the returned job_id
    to poll for status and results.
    
    Example:
        ```
        POST /api/v2/training/start
        {
            "strategy": "LIQUIDITY_SWEEP",
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "timeframe": "5m",
            "optimizer": "bayesian",
            "lookback_days": 90,
            "n_iterations": 200,
            "run_validation": true
        }
        ```
    
    Returns:
        TrainingJobResponse with job_id and initial status
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Insert job record
        db_url = get_db_url()
        conn = await asyncpg.connect(db_url)
        
        await conn.execute(
            """
            INSERT INTO training_jobs (
                job_id,
                strategy,
                symbol,
                exchange,
                timeframe,
                optimizer,
                lookback_days,
                n_iterations,
                parameter_space,
                status,
                created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'PENDING', $10)
            """,
            job_id,
            request.strategy,
            request.symbol,
            request.exchange,
            request.timeframe,
            request.optimizer,
            request.lookback_days,
            request.n_iterations,
            {},  # parameter_space (filled by training task)
            datetime.now(timezone.utc)
        )
        
        await conn.close()
        
        # Start background task
        background_tasks.add_task(run_training_task, job_id, request)
        
        log.info(f"Training job {job_id} queued: {request.strategy} {request.symbol}")
        
        return TrainingJobResponse(
            job_id=job_id,
            status="PENDING",
            strategy=request.strategy,
            symbol=request.symbol,
            exchange=request.exchange,
            timeframe=request.timeframe,
            optimizer=request.optimizer,
            progress_pct=0,
            current_iteration=None,
            total_iterations=request.n_iterations,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            duration_seconds=None,
            error_message=None
        )
        
    except Exception as e:
        log.error(f"Failed to start training job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=List[TrainingJobResponse])
async def list_training_jobs(
    status: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = 50
):
    """
    List training jobs with optional filters.
    
    Query Parameters:
        - status: Filter by status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
        - strategy: Filter by strategy name
        - limit: Maximum number of jobs to return (default: 50)
    
    Returns:
        List of TrainingJobResponse
    """
    try:
        db_url = get_db_url()
        conn = await asyncpg.connect(db_url)
        
        # Build query
        query = "SELECT * FROM training_jobs WHERE 1=1"
        params = []
        param_idx = 1
        
        if status:
            query += f" AND status = ${param_idx}"
            params.append(status)
            param_idx += 1
        
        if strategy:
            query += f" AND strategy = ${param_idx}"
            params.append(strategy)
            param_idx += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${param_idx}"
        params.append(limit)
        
        rows = await conn.fetch(query, *params)
        await conn.close()
        
        jobs = []
        for row in rows:
            jobs.append(TrainingJobResponse(
                job_id=row['job_id'],
                status=row['status'],
                strategy=row['strategy'],
                symbol=row['symbol'],
                exchange=row['exchange'],
                timeframe=row['timeframe'],
                optimizer=row['optimizer'],
                progress_pct=float(row['progress_pct'] or 0),
                current_iteration=row['current_iteration'],
                total_iterations=row['total_iterations'],
                created_at=row['created_at'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                duration_seconds=row['duration_seconds'],
                error_message=row['error_message']
            ))
        
        return jobs
        
    except Exception as e:
        log.error(f"Failed to list jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(job_id: str):
    """
    Get training job status.
    
    Returns:
        TrainingJobResponse with current job status and progress
    """
    try:
        db_url = get_db_url()
        conn = await asyncpg.connect(db_url)
        
        row = await conn.fetchrow(
            "SELECT * FROM training_jobs WHERE job_id = $1",
            job_id
        )
        
        await conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return TrainingJobResponse(
            job_id=row['job_id'],
            status=row['status'],
            strategy=row['strategy'],
            symbol=row['symbol'],
            exchange=row['exchange'],
            timeframe=row['timeframe'],
            optimizer=row['optimizer'],
            progress_pct=float(row['progress_pct'] or 0),
            current_iteration=row['current_iteration'],
            total_iterations=row['total_iterations'],
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            duration_seconds=row['duration_seconds'],
            error_message=row['error_message']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to get job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/results", response_model=TrainingResultsResponse)
async def get_training_results(job_id: str):
    """
    Get training job results.
    
    Only available after job is COMPLETED.
    
    Returns:
        TrainingResultsResponse with best configuration and metrics
    """
    try:
        db_url = get_db_url()
        conn = await asyncpg.connect(db_url)
        
        row = await conn.fetchrow(
            "SELECT * FROM training_jobs WHERE job_id = $1",
            job_id
        )
        
        await conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if row['status'] != 'COMPLETED':
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} not completed (status: {row['status']})"
            )
        
        return TrainingResultsResponse(
            job_id=row['job_id'],
            status=row['status'],
            config_id=row['best_config_id'],
            best_score=float(row['best_score']) if row['best_score'] else None,
            best_parameters=row['best_parameters'],
            best_metrics=row['best_metrics'],
            validation_summary=None  # TODO: Add validation summary if needed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to get results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def cancel_training_job(job_id: str):
    """
    Cancel a training job.
    
    Only works for PENDING or RUNNING jobs.
    
    Returns:
        Success message
    """
    try:
        db_url = get_db_url()
        conn = await asyncpg.connect(db_url)
        
        row = await conn.fetchrow(
            "SELECT status FROM training_jobs WHERE job_id = $1",
            job_id
        )
        
        if not row:
            await conn.close()
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if row['status'] not in ['PENDING', 'RUNNING']:
            await conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status {row['status']}"
            )
        
        # Update status to CANCELLED
        await conn.execute(
            """
            UPDATE training_jobs 
            SET status = 'CANCELLED', completed_at = $1
            WHERE job_id = $2
            """,
            datetime.now(timezone.utc),
            job_id
        )
        
        await conn.close()
        
        log.info(f"Training job {job_id} cancelled")
        
        return {"message": f"Job {job_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to cancel job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
