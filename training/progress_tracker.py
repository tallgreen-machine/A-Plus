"""
Training Progress Tracker

Real-time progress tracking for training jobs.
Publishes progress updates to the database for frontend polling.
"""

import asyncpg
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks and publishes training job progress in real-time.
    
    Workflow Steps:
    1. Data Collection (0-25%)
    2. Optimization (25-75%)
    3. Validation (75-95%)
    4. Configuration Save (95-100%)
    """
    
    STEPS = {
        'data_preparation': {'number': 1, 'name': 'Preparing Data', 'weight': 0.25},
        'optimization': {'number': 2, 'name': 'Optimization', 'weight': 0.50},
        'validation': {'number': 3, 'name': 'Validation', 'weight': 0.20},
        'save_config': {'number': 4, 'name': 'Saving Configuration', 'weight': 0.05},
    }
    
    def __init__(self, job_id: str, db_url: str):
        self.job_id = job_id
        self.db_url = db_url
        self.current_step = None
        self.started_at = datetime.utcnow()
        self.last_percentage = 0.0  # Track last known percentage for error handling
        self.last_step_number = 0  # Track last step number for error handling
        
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
        
        await self._publish_update(
            percentage=overall_pct,
            current_step=step_info['name'],
            step_number=step_info['number'],
            step_percentage=0.0,
            step_details=step_details
        )
    
    async def update(
        self, 
        step_percentage: float,
        iteration: Optional[int] = None,
        total_iterations: Optional[int] = None,
        best_score: Optional[float] = None,
        current_score: Optional[float] = None,
        best_params: Optional[Dict[str, Any]] = None,
        step_details: Optional[Dict[str, Any]] = None
    ):
        """Update progress within current step."""
        if not self.current_step:
            raise RuntimeError("No active step. Call start() first.")
        
        step_info = self.STEPS[self.current_step]
        
        # Calculate overall percentage
        # = (completed steps weight) + (current step weight * current step progress)
        previous_weight = sum(
            self.STEPS[s]['weight'] 
            for s in self.STEPS.keys() 
            if self.STEPS[s]['number'] < step_info['number']
        )
        current_contribution = step_info['weight'] * (step_percentage / 100.0)
        overall_pct = (previous_weight + current_contribution) * 100
        
        # Estimate completion time based on current progress
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        if overall_pct > 0:
            estimated_total_seconds = (elapsed / overall_pct) * 100
            eta = self.started_at + timedelta(seconds=estimated_total_seconds)
        else:
            eta = None
        
        await self._publish_update(
            percentage=overall_pct,
            current_step=step_info['name'],
            step_number=step_info['number'],
            step_percentage=step_percentage,
            step_details=step_details,
            estimated_completion=eta,
            current_iteration=iteration,
            total_iterations=total_iterations,
            best_score=best_score,
            current_score=current_score,
            best_params=best_params
        )
    
    async def complete(self):
        """Mark training as complete."""
        logger.info(f"[{self.job_id}] Training complete!")
        
        await self._publish_update(
            percentage=100.0,
            current_step='Complete',
            step_number=4,
            step_percentage=100.0,
            is_complete=True
        )
    
    async def error(self, error_message: str):
        """Mark training as failed."""
        logger.error(f"[{self.job_id}] Training failed: {error_message}")
        
        await self._publish_update(
            percentage=self.last_percentage or 0.0,  # Use last known percentage or 0
            step_number=self.last_step_number or 1,  # Use last known step or 1
            step_percentage=0.0,  # Set to 0 for error state
            current_step='Failed',
            error_message=error_message,
            is_complete=True
        )
    
    async def _publish_update(
        self,
        percentage: Optional[float] = None,
        current_step: Optional[str] = None,
        step_number: Optional[int] = None,
        step_percentage: Optional[float] = None,
        step_details: Optional[Dict[str, Any]] = None,
        estimated_completion: Optional[datetime] = None,
        current_iteration: Optional[int] = None,
        total_iterations: Optional[int] = None,
        best_score: Optional[float] = None,
        current_score: Optional[float] = None,
        best_params: Optional[Dict[str, Any]] = None,
        is_complete: bool = False,
        error_message: Optional[str] = None
    ):
        """Publish progress update to database."""
        conn = None
        try:
            conn = await asyncpg.connect(self.db_url)
            
            # Upsert progress record (insert or update if exists)
            query = """
                INSERT INTO training_progress (
                    job_id, percentage, current_step, step_number, total_steps,
                    step_percentage, step_details, estimated_completion,
                    current_iteration, total_iterations, best_score, current_score,
                    best_params, is_complete, error_message, started_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                )
                ON CONFLICT (job_id) 
                DO UPDATE SET
                    percentage = COALESCE(EXCLUDED.percentage, training_progress.percentage),
                    current_step = COALESCE(EXCLUDED.current_step, training_progress.current_step),
                    step_number = COALESCE(EXCLUDED.step_number, training_progress.step_number),
                    step_percentage = COALESCE(EXCLUDED.step_percentage, training_progress.step_percentage),
                    step_details = COALESCE(EXCLUDED.step_details, training_progress.step_details),
                    estimated_completion = COALESCE(EXCLUDED.estimated_completion, training_progress.estimated_completion),
                    current_iteration = COALESCE(EXCLUDED.current_iteration, training_progress.current_iteration),
                    total_iterations = COALESCE(EXCLUDED.total_iterations, training_progress.total_iterations),
                    best_score = COALESCE(EXCLUDED.best_score, training_progress.best_score),
                    current_score = COALESCE(EXCLUDED.current_score, training_progress.current_score),
                    best_params = COALESCE(EXCLUDED.best_params, training_progress.best_params),
                    is_complete = EXCLUDED.is_complete,
                    error_message = COALESCE(EXCLUDED.error_message, training_progress.error_message),
                    updated_at = NOW()
            """
            
            await conn.execute(
                query,
                self.job_id,
                percentage,
                current_step,
                step_number,
                4,  # total_steps
                step_percentage,
                json.dumps(step_details) if step_details else None,
                estimated_completion,
                current_iteration,
                total_iterations,
                best_score,
                current_score,
                json.dumps(best_params) if best_params else None,
                is_complete,
                error_message,
                self.started_at
            )
            
            # Track last percentage and step_number for error handling
            if percentage is not None:
                self.last_percentage = percentage
            if step_number is not None:
                self.last_step_number = step_number
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Failed to publish progress update: {e}")
            if conn:
                await conn.close()
