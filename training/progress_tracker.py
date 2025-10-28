"""
Training Progress Tracker

Real-time progress tracking for training jobs.
Publishes progress updates to the training_jobs table for frontend consumption.
"""

import asyncpg
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import httpx

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks and publishes training job progress in real-time.
    
    Workflow Steps:
    1. Optimization/Training (0-100%)
    
    Data preparation is fast and not shown in progress.
    Reports progress to training_jobs table as iterations complete.
    """
    
    STEPS = {
        'optimization': {'number': 1, 'name': 'Training', 'weight': 1.0},
    }
    
    def __init__(self, job_id: str, db_url: str):
        self.job_id = job_id
        self.db_url = db_url
        self.current_step = None
        self.started_at = datetime.utcnow()
        self.last_percentage = 0.0
        self.last_step_number = 0
        # API endpoint for logging (defaults to localhost in worker)
        self.api_url = os.getenv('API_URL', 'http://localhost:8000')
        
    async def _save_log(
        self, 
        message: str, 
        progress: float = 0.0, 
        log_level: str = 'INFO'
    ):
        """Save log entry to training_logs table via API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.api_url}/api/training/{self.job_id}/logs",
                    json={
                        'timestamp': datetime.utcnow().isoformat(),
                        'message': message,
                        'progress': round(progress, 1),
                        'log_level': log_level
                    }
                )
        except Exception as e:
            # Don't fail the job if logging fails
            logger.warning(f"Failed to save log for job {self.job_id}: {e}")
        
    async def start(self, step_name: str, step_details: Optional[Dict[str, Any]] = None):
        """Start tracking a new step."""
        if step_name not in self.STEPS:
            raise ValueError(f"Unknown step: {step_name}. Valid: {list(self.STEPS.keys())}")
        
        self.current_step = step_name
        step_info = self.STEPS[step_name]
        
        logger.info(f"[{self.job_id}] Starting step {step_info['number']}/4: {step_info['name']}")
        
        # Calculate overall percentage at start of this step
        overall_pct = sum(
            self.STEPS[s]['weight'] * 100 
            for s in self.STEPS.keys() 
            if self.STEPS[s]['number'] < step_info['number']
        )
        
        # Update training_jobs table with new status (for live display only, not logged)
        await self._update_job_status(
            status='running',
            progress=overall_pct,
            current_stage=step_info['name']
        )
    
    async def update(
        self, 
        step_percentage: float,
        iteration: Optional[int] = None,
        total_iterations: Optional[int] = None,
        best_score: Optional[float] = None,
        current_score: Optional[float] = None,
        best_params: Optional[Dict[str, Any]] = None,
        step_details: Optional[Dict[str, Any]] = None,
        reward: Optional[float] = None,
        loss: Optional[float] = None
    ):
        """
        Update progress within current step.
        
        Supports both optimizer iterations and episode-based training.
        Reports progress every 0.1% for smooth UI updates.
        """
        if not self.current_step:
            raise RuntimeError("No active step. Call start() first.")
        
        step_info = self.STEPS[self.current_step]
        
        # Calculate overall percentage
        previous_weight = sum(
            self.STEPS[s]['weight'] 
            for s in self.STEPS.keys() 
            if self.STEPS[s]['number'] < step_info['number']
        )
        current_contribution = step_info['weight'] * (step_percentage / 100.0)
        overall_pct = (previous_weight + current_contribution) * 100
        
        # Build CLI-style progress message for SSE stream
        # Line 1: Status with details
        status_parts = [f"{step_info['name']}..."]
        if iteration and total_iterations:
            status_parts.append(f"Episode {iteration}/{total_iterations}")
        if reward is not None:
            status_parts.append(f"Reward: {reward:.2f}")
        if loss is not None:
            status_parts.append(f"Loss: {loss:.4f}")
        
        status_line = " | ".join(status_parts)
        
        # Line 2: ASCII progress bar
        bar_width = 50
        filled = int(bar_width * overall_pct / 100)
        bar = '█' * filled + '░' * (bar_width - filled)
        progress_line = f"[{overall_pct:.2f}%] {bar}"
        
        # Combine both lines
        progress_message = f"{status_line}\n{progress_line}"
        
        # Always update job status for SSE/live display (this is lightweight)
        await self._update_job_status(
            status='running',
            progress=overall_pct,
            current_stage=step_info['name'],
            current_episode=iteration,
            total_episodes=total_iterations,
            current_reward=reward,
            current_loss=loss
        )
        
        # Don't persist progress updates to database - only show in live display
        # History logs should only contain final completion messages
    
    async def complete(self):
        """Mark training as complete."""
        logger.info(f"[{self.job_id}] Training complete!")
        
        # Fetch job metadata from database to include in completion message
        try:
            conn = await asyncpg.connect(self.db_url)
            try:
                job_data = await conn.fetchrow(
                    """
                    SELECT strategy_name, pair, exchange, timeframe, regime, submitted_at
                    FROM training_jobs
                    WHERE id = $1
                    """,
                    int(self.job_id)
                )
                
                if job_data:
                    # Build completion message with job details
                    complete_message = (
                        f"✓ Job #{self.job_id} | {job_data['strategy_name']} | "
                        f"{job_data['pair']} | {job_data['exchange']} | "
                        f"{job_data['timeframe']} | {job_data['regime']} | "
                        f"Completed successfully"
                    )
                else:
                    complete_message = f"✓ Job #{self.job_id} completed successfully"
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Failed to fetch job metadata: {e}")
            complete_message = f"✓ Job #{self.job_id} completed successfully"
        
        await self._save_log(
            message=complete_message,
            progress=100.0,
            log_level='SUCCESS'
        )
        
        await self._update_job_status(
            status='completed',
            progress=100.0,
            current_stage='Complete',
            completed_at=datetime.utcnow()
        )
    
    async def error(self, error_message: str):
        """Mark training as failed."""
        logger.error(f"[{self.job_id}] Training failed: {error_message}")
        
        # Save error log
        await self._save_log(
            message=f"✗ Error: {error_message}",
            progress=self.last_percentage or 0.0,
            log_level='ERROR'
        )
        
        await self._update_job_status(
            status='failed',
            progress=self.last_percentage or 0.0,
            current_stage='Failed',
            error_message=error_message,
            completed_at=datetime.utcnow()
        )
    
    async def _update_job_status(
        self,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        current_stage: Optional[str] = None,
        current_episode: Optional[int] = None,
        total_episodes: Optional[int] = None,
        current_reward: Optional[float] = None,
        current_loss: Optional[float] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ):
        """Update training_jobs table with current progress."""
        conn = None
        try:
            conn = await asyncpg.connect(self.db_url)
            
            # Build dynamic UPDATE query
            updates = []
            params = []
            param_idx = 1
            
            if status:
                updates.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1
                
                # Set started_at on first 'running' status
                if status == 'running':
                    updates.append(f"started_at = COALESCE(started_at, ${param_idx})")
                    params.append(datetime.utcnow())
                    param_idx += 1
            
            if progress is not None:
                updates.append(f"progress = ${param_idx}")
                params.append(round(progress, 2))  # Round to 2 decimal places
                param_idx += 1
            
            if current_stage:
                updates.append(f"current_stage = ${param_idx}")
                params.append(current_stage)
                param_idx += 1
            
            if current_episode is not None:
                updates.append(f"current_episode = ${param_idx}")
                params.append(current_episode)
                param_idx += 1
            
            if total_episodes is not None:
                updates.append(f"total_episodes = ${param_idx}")
                params.append(total_episodes)
                param_idx += 1
            
            if current_reward is not None:
                updates.append(f"current_reward = ${param_idx}")
                params.append(current_reward)
                param_idx += 1
            
            if current_loss is not None:
                updates.append(f"current_loss = ${param_idx}")
                params.append(current_loss)
                param_idx += 1
            
            if error_message:
                updates.append(f"error_message = ${param_idx}")
                params.append(error_message)
                param_idx += 1
            
            if completed_at:
                updates.append(f"completed_at = ${param_idx}")
                params.append(completed_at)
                param_idx += 1
            
            if updates:
                query = f"""
                    UPDATE training_jobs
                    SET {', '.join(updates)}
                    WHERE id = ${param_idx}
                """
                params.append(int(self.job_id))  # Convert string job_id to integer
                
                await conn.execute(query, *params)
            
        except Exception as e:
            logger.error(f"Failed to update job {self.job_id}: {e}")
        finally:
            if conn:
                await conn.close()
