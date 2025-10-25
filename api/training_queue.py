"""
Training Queue API
Manages persistent training job queue with database-backed state
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import asyncpg
import os
from redis import Redis
from rq import Queue
from rq.job import Job
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

router = APIRouter(prefix="/api/training", tags=["Training Queue"])
log = logging.getLogger(__name__)

# ===== Database Configuration =====

def get_db_url() -> str:
    """Get database URL from environment"""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Try individual DB_* environment variables
    db_host = os.getenv('DB_HOST')
    if db_host:
        return (
            f"postgresql://{os.getenv('DB_USER', 'traduser')}:"
            f"{os.getenv('DB_PASSWORD', '')}@"
            f"{db_host}:"
            f"{os.getenv('DB_PORT', '5432')}/"
            f"{os.getenv('DB_NAME', 'trad')}"
        )
    
    return "postgresql://traduser:tradpass@localhost:5432/traddb"

# ===== Redis/RQ Configuration =====

def get_redis_connection() -> Redis:
    """Get Redis connection for RQ"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    return Redis.from_url(redis_url)

def get_training_queue() -> Queue:
    """Get RQ queue for training jobs"""
    redis_conn = get_redis_connection()
    return Queue('training', connection=redis_conn)

# ===== Request/Response Models =====

class TrainingJobCreate(BaseModel):
    """Request to create new training job"""
    strategy_name: str
    exchange: str
    pair: str
    timeframe: str
    regime: str
    config_id: Optional[str] = None  # FK to training_configurations if creating from existing
    # Training parameters
    lookback_days: int = 90
    optimizer: str = "bayesian"
    n_iterations: int = 200

class TrainingJobResponse(BaseModel):
    """Training job info for queue display"""
    id: str
    config_id: Optional[str]
    rq_job_id: Optional[str]
    status: str
    progress: float
    strategy_name: str
    exchange: str
    pair: str
    timeframe: str
    regime: str
    current_episode: Optional[int]
    total_episodes: Optional[int]
    current_reward: Optional[float]
    current_loss: Optional[float]
    current_stage: Optional[str]
    submitted_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

class ProgressUpdate(BaseModel):
    """Progress update for SSE streaming"""
    progress: float
    current_episode: Optional[int]
    total_episodes: Optional[int]
    current_reward: Optional[float]
    current_loss: Optional[float]
    stage: Optional[str]

# ===== API Endpoints =====

@router.post("/submit", response_model=TrainingJobResponse)
async def submit_training_job(request: TrainingJobCreate):
    """
    Submit new training job to queue
    Creates database record and enqueues job to RQ worker
    """
    try:
        conn = await asyncpg.connect(get_db_url())
        
        # Create job record in database
        # Note: id is auto-generated INTEGER (serial), not UUID
        
        # Convert config_id to UUID or None
        config_id_uuid = uuid.UUID(request.config_id) if request.config_id else None
        
        row = await conn.fetchrow(
            """
            INSERT INTO training_jobs (
                config_id, status, strategy, symbol, exchange, timeframe, regime,
                strategy_name, pair, optimizer, lookback_days, n_iterations, submitted_at, job_id
            )
            VALUES ($1, 'pending', $2::text, $3::text, $4, $5, $6, $7::varchar, $8::varchar, $9, $10, $11, NOW(), $12)
            RETURNING *
            """,
            config_id_uuid,
            request.strategy_name,  # $2 - strategy (text)
            request.pair,           # $3 - symbol (text)
            request.exchange,       # $4 - exchange
            request.timeframe,      # $5 - timeframe
            request.regime,         # $6 - regime
            request.strategy_name,  # $7 - strategy_name (varchar)
            request.pair,           # $8 - pair (varchar)
            request.optimizer,      # $9 - optimizer
            request.lookback_days,  # $10 - lookback_days
            request.n_iterations,   # $11 - n_iterations
            str(uuid.uuid4())       # $12 - job_id
        )
        
        # Enqueue to RQ worker
        queue = get_training_queue()
        rq_job = queue.enqueue(
            'training.rq_jobs.run_training_job',
            str(row['id']),  # job_id as first positional argument
            request.strategy_name,  # strategy
            request.pair,  # symbol
            request.exchange,
            request.timeframe,
            request.regime,
            request.optimizer,
            request.lookback_days,
            request.n_iterations,
            True,  # run_validation
            job_timeout=1800  # 30 minutes
        )
        
        # Update with RQ job ID
        await conn.execute(
            "UPDATE training_jobs SET rq_job_id = $1 WHERE id = $2",
            rq_job.id,
            row['id']
        )
        
        await conn.close()
        
        log.info(f"Submitted training job {row['id']}: {request.strategy_name} {request.pair}")
        
        return TrainingJobResponse(
            id=str(row['id']),
            config_id=str(row['config_id']) if row['config_id'] else None,
            rq_job_id=rq_job.id,
            status=row['status'],
            progress=float(row['progress'] or 0),
            strategy_name=row['strategy_name'],
            exchange=row['exchange'],
            pair=row['pair'],
            timeframe=row['timeframe'],
            regime=row['regime'],
            current_episode=row['current_episode'],
            total_episodes=row['total_episodes'],
            current_reward=float(row['current_reward']) if row['current_reward'] else None,
            current_loss=float(row['current_loss']) if row['current_loss'] else None,
            current_stage=row['current_stage'],
            submitted_at=row['submitted_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            error_message=row['error_message']
        )
        
    except Exception as e:
        log.error(f"Failed to submit training job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue", response_model=List[TrainingJobResponse])
async def list_training_queue():
    """
    Get all pending and running training jobs
    Completed jobs are removed from queue
    """
    try:
        conn = await asyncpg.connect(get_db_url())
        
        rows = await conn.fetch(
            """
            SELECT * FROM training_jobs
            WHERE status IN ('pending', 'running')
            ORDER BY submitted_at ASC
            """
        )
        
        await conn.close()
        
        jobs = []
        for row in rows:
            jobs.append(TrainingJobResponse(
                id=str(row['id']),
                config_id=str(row['config_id']) if row['config_id'] else None,
                rq_job_id=row['rq_job_id'],
                status=row['status'],
                progress=float(row['progress'] or 0),
                strategy_name=row['strategy_name'],
                exchange=row['exchange'],
                pair=row['pair'],
                timeframe=row['timeframe'],
                regime=row['regime'],
                current_episode=row['current_episode'],
                total_episodes=row['total_episodes'],
                current_reward=float(row['current_reward']) if row['current_reward'] else None,
                current_loss=float(row['current_loss']) if row['current_loss'] else None,
                current_stage=row['current_stage'],
                submitted_at=row['submitted_at'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                error_message=row['error_message']
            ))
        
        return jobs
        
    except Exception as e:
        log.error(f"Failed to fetch training queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{job_id}")
async def cancel_training_job(job_id: str):
    """
    Cancel or remove training job
    - Pending jobs: removed from queue
    - Running jobs: cancelled and marked as cancelled
    """
    try:
        conn = await asyncpg.connect(get_db_url())
        
        # job_id is an integer
        job_id_int = int(job_id)
        
        # Get job info
        job = await conn.fetchrow(
            "SELECT * FROM training_jobs WHERE id = $1",
            job_id_int
        )
        
        if not job:
            await conn.close()
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Cancel RQ job if exists
        if job['rq_job_id']:
            try:
                redis_conn = get_redis_connection()
                rq_job = Job.fetch(job['rq_job_id'], connection=redis_conn)
                rq_job.cancel()
                log.info(f"Cancelled RQ job {job['rq_job_id']}")
            except Exception as e:
                log.warning(f"Failed to cancel RQ job: {e}")
        
        # Update database
        if job['status'] == 'pending':
            # Remove pending jobs completely
            await conn.execute(
                "DELETE FROM training_jobs WHERE id = $1",
                job_id_int
            )
            log.info(f"Removed pending job {job_id}")
        else:
            # Mark running jobs as cancelled
            await conn.execute(
                """
                UPDATE training_jobs 
                SET status = 'cancelled', completed_at = NOW()
                WHERE id = $1
                """,
                job_id_int
            )
            log.info(f"Cancelled running job {job_id}")
        
        await conn.close()
        
        return {"success": True, "message": f"Job {job_id} cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}/stream")
async def stream_training_progress(job_id: str):
    """
    Server-Sent Events stream for real-time progress updates
    Lightweight SSE connection that pushes updates every 0.5s
    """
    async def event_generator():
        """Generate SSE events with training progress"""
        try:
            db_url = get_db_url()
            last_progress = -1
            job_id_int = int(job_id)
            
            while True:
                try:
                    conn = await asyncpg.connect(db_url)
                    
                    job = await conn.fetchrow(
                        "SELECT * FROM training_jobs WHERE id = $1",
                        job_id_int
                    )
                    
                    await conn.close()
                    
                    if not job:
                        yield {
                            "event": "error",
                            "data": json.dumps({"error": "Job not found"})
                        }
                        break
                    
                    # Only send update if progress changed
                    current_progress = float(job['progress'] or 0)
                    if current_progress != last_progress or job['status'] in ['completed', 'failed', 'cancelled']:
                        last_progress = current_progress
                        
                        yield {
                            "event": "progress",
                            "data": json.dumps({
                                "progress": current_progress,
                                "current_episode": job['current_episode'],
                                "total_episodes": job['total_episodes'],
                                "current_reward": float(job['current_reward']) if job['current_reward'] else None,
                                "current_loss": float(job['current_loss']) if job['current_loss'] else None,
                                "stage": job['current_stage'],
                                "status": job['status']
                            })
                        }
                    
                    # Stop streaming if job completed
                    if job['status'] in ['completed', 'failed', 'cancelled']:
                        yield {
                            "event": "complete",
                            "data": json.dumps({"status": job['status']})
                        }
                        break
                    
                    await asyncio.sleep(0.5)  # Check every 500ms
                    
                except Exception as e:
                    log.error(f"Error in event generator: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }
                    break
                    
        except Exception as e:
            log.error(f"Fatal error in event generator: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(event_generator())
