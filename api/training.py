"""
Training Pipeline API endpoints
Integrates with existing training system for AI pattern optimization
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
from enum import Enum
import subprocess
import uuid
import json

from api.database import get_database
from api.auth_utils import get_current_user
import logging

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training", tags=["training"])

# Enums
class TrainingPhase(str, Enum):
    DATA_COLLECTION = "Data Collection"
    VIABILITY_ASSESSMENT = "Viability Assessment"
    TIMEFRAME_TESTING = "Multi-Timeframe Testing"
    OPTIMIZATION = "Bayesian Optimization"
    VALIDATION = "Walk-Forward Validation"
    ROBUSTNESS = "Robustness & Stress Testing"
    SCORING = "Final Confidence Scoring"
    COMPLETE = "Complete"

# Pydantic models
class AssetRanking(BaseModel):
    symbol: str
    suitabilityScore: float
    volatilityIndex: float
    liquidityIndex: float
    dataAvailability: str
    reason: str
    estimatedTime: str
    riskLevel: str

class PatternViability(BaseModel):
    name: str
    winRate: float
    signals: int
    status: str

class TrainingStatus(BaseModel):
    jobId: str
    assetSymbol: str
    phase: TrainingPhase
    progress: float
    message: str
    eta: str
    patternAnalysis: Optional[List[PatternViability]] = None
    currentBest: Optional[Dict[str, float]] = None

class TrainingResults(BaseModel):
    jobId: str
    assetSymbol: str
    completedAt: str
    results: Dict[str, Any]

class StartTrainingRequest(BaseModel):
    symbols: List[str]
    patterns: List[str]
    timeframes: List[str]
    optimizationMethod: str = "bayesian"

def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

# In-memory storage for training jobs (in production, use Redis or database)
training_jobs = {}

@router.get("/asset-rankings", response_model=List[AssetRanking])
async def get_asset_rankings(current_user: dict = Depends(get_current_user)):
    """Get asset suitability rankings for training"""
    # In production, this would analyze actual market data
    sample_rankings = [
        AssetRanking(
            symbol="BTC/USDT",
            suitabilityScore=95.2,
            volatilityIndex=8.5,
            liquidityIndex=9.8,
            dataAvailability="Excellent",
            reason="High liquidity, consistent patterns, extensive historical data",
            estimatedTime="2-3 hours",
            riskLevel="Low"
        ),
        AssetRanking(
            symbol="ETH/USDT", 
            suitabilityScore=91.7,
            volatilityIndex=8.8,
            liquidityIndex=9.5,
            dataAvailability="Excellent",
            reason="Strong correlation patterns, high volume trading",
            estimatedTime="2-4 hours",
            riskLevel="Low"
        ),
        AssetRanking(
            symbol="BNB/USDT",
            suitabilityScore=78.3,
            volatilityIndex=7.2,
            liquidityIndex=8.1,
            dataAvailability="Good",
            reason="Moderate liquidity, exchange-specific patterns",
            estimatedTime="3-5 hours",
            riskLevel="Medium"
        ),
        AssetRanking(
            symbol="ADA/USDT",
            suitabilityScore=68.9,
            volatilityIndex=9.1,
            liquidityIndex=7.3,
            dataAvailability="Good", 
            reason="High volatility, emerging patterns",
            estimatedTime="4-6 hours",
            riskLevel="Medium"
        ),
        AssetRanking(
            symbol="DOGE/USDT",
            suitabilityScore=45.2,
            volatilityIndex=12.4,
            liquidityIndex=6.8,
            dataAvailability="Fair",
            reason="Extremely high volatility, unpredictable patterns",
            estimatedTime="6-8 hours",
            riskLevel="High"
        )
    ]
    
    return sample_rankings

@router.post("/start", response_model=Dict[str, str])
async def start_training(
    request: StartTrainingRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Start a new training job"""
    try:
        job_id = str(uuid.uuid4())
        
        # Create training job record
        training_jobs[job_id] = {
            "jobId": job_id,
            "userId": current_user["id"],
            "symbols": request.symbols,
            "patterns": request.patterns,
            "timeframes": request.timeframes,
            "status": "STARTED",
            "phase": TrainingPhase.DATA_COLLECTION,
            "progress": 0.0,
            "message": "Initializing training job...",
            "startedAt": datetime.utcnow().isoformat(),
            "eta": "Calculating..."
        }
        
        # Add background task to run training
        background_tasks.add_task(run_training_job, job_id, request, current_user["id"])
        
        log.info(f"Started training job {job_id} for user {current_user['id']}")
        
        return {"jobId": job_id, "message": "Training job started successfully"}
        
    except Exception as e:
        log.error(f"Error starting training job: {e}")
        raise HTTPException(status_code=500, detail="Failed to start training job")

async def update_training_status(job_id: str, status_update: dict):
    """Callback function for training runner to update job status"""
    if job_id in training_jobs:
        training_jobs[job_id].update(status_update)
        log.info(f"Updated training job {job_id}: {status_update.get('message', 'Status update')}")

async def run_training_job(job_id: str, request: StartTrainingRequest, user_id: int):
    """Background task to run the actual ML training job"""
    try:
        from ml.real_training_runner import RealTrainingRunner
        
        log.info(f"Starting real ML training for job {job_id}")
        
        # Create training runner with callback
        runner = RealTrainingRunner(
            job_id=job_id,
            symbols=request.symbols,
            patterns=request.patterns,
            update_callback=update_training_status
        )
        
        # Execute the training
        results = await runner.run_training()
        
        # Mark as complete with results
        if job_id in training_jobs:
            training_jobs[job_id].update({
                "status": "COMPLETE",
                "phase": TrainingPhase.COMPLETE,
                "progress": 100.0,
                "message": "Training completed successfully!",
                "eta": "Complete",
                "completedAt": datetime.utcnow().isoformat(),
                "results": results
            })
            
        log.info(f"Training job {job_id} completed successfully")
        
    except ImportError as e:
        log.error(f"Failed to import training dependencies: {e}")
        # Fall back to simulation mode
        await run_simulation_training_job(job_id, request, user_id)
        
    except Exception as e:
        log.error(f"Error in training job {job_id}: {e}")
        if job_id in training_jobs:
            training_jobs[job_id].update({
                "status": "FAILED",
                "message": f"Training failed: {str(e)}",
                "eta": "Failed"
            })



async def run_simulation_training_job(job_id: str, request: StartTrainingRequest, user_id: int):
    """Fallback simulation training job (original implementation)"""
    try:
        job = training_jobs[job_id]
        
        # Simulate training phases (fallback for missing dependencies)
        log.warning(f"Running simulation training for job {job_id} (real training unavailable)")
        
        phases = [
            (TrainingPhase.DATA_COLLECTION, "Collecting historical market data..."),
            (TrainingPhase.VIABILITY_ASSESSMENT, "Analyzing pattern viability..."),
            (TrainingPhase.TIMEFRAME_TESTING, "Testing multiple timeframes..."),
            (TrainingPhase.OPTIMIZATION, "Optimizing parameters..."),
            (TrainingPhase.VALIDATION, "Running walk-forward validation..."),
            (TrainingPhase.ROBUSTNESS, "Stress testing patterns..."),
            (TrainingPhase.SCORING, "Calculating confidence scores..."),
        ]
        
        for i, (phase, message) in enumerate(phases):
            if job_id not in training_jobs:
                break
                
            progress = (i + 1) / len(phases) * 100
            eta_minutes = (len(phases) - i - 1) * 3  # Faster simulation
            eta = f"{eta_minutes} minutes" if eta_minutes > 0 else "Complete"
            
            job.update({
                "phase": phase,
                "progress": progress,
                "message": f"[SIMULATION] {message}",
                "eta": eta
            })
            
            # Simulate work
            import asyncio
            await asyncio.sleep(2)  # Reduced simulation time
            
        # Mark as complete
        if job_id in training_jobs:
            job.update({
                "status": "COMPLETE",
                "phase": TrainingPhase.COMPLETE,
                "progress": 100.0,
                "message": "Simulation training completed!",
                "eta": "Complete",
                "completedAt": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        log.error(f"Error in simulation training job {job_id}: {e}")
        if job_id in training_jobs:
            training_jobs[job_id].update({
                "status": "FAILED",
                "message": f"Simulation training failed: {str(e)}",
                "eta": "Failed"
            })

@router.get("/status/{job_id}", response_model=TrainingStatus)
async def get_training_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get training job status"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    job = training_jobs[job_id]
    
    # Check user permission
    if job["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate sample pattern analysis if in viability phase
    pattern_analysis = None
    if job["phase"] == TrainingPhase.VIABILITY_ASSESSMENT:
        pattern_analysis = [
            PatternViability(name="Liquidity Sweep", winRate=0.68, signals=45, status="Viable"),
            PatternViability(name="Volume Breakout", winRate=0.72, signals=32, status="Viable"),
            PatternViability(name="Divergence Capitulation", winRate=0.45, signals=18, status="Not Viable")
        ]
    
    # Generate current best if in optimization phase
    current_best = None
    if job["phase"] in [TrainingPhase.OPTIMIZATION, TrainingPhase.VALIDATION, TrainingPhase.ROBUSTNESS, TrainingPhase.SCORING]:
        current_best = {
            "winRate": 0.72,
            "rr": 2.1,
            "score": 0.85
        }
    
    return TrainingStatus(
        jobId=job["jobId"],
        assetSymbol=job["symbols"][0] if job["symbols"] else "Unknown",
        phase=TrainingPhase(job["phase"]),
        progress=job["progress"],
        message=job["message"],
        eta=job["eta"],
        patternAnalysis=pattern_analysis,
        currentBest=current_best
    )

@router.get("/jobs", response_model=List[TrainingStatus])
async def get_training_jobs(current_user: dict = Depends(get_current_user)):
    """Get all training jobs for current user"""
    user_jobs = [
        TrainingStatus(
            jobId=job["jobId"],
            assetSymbol=job["symbols"][0] if job["symbols"] else "Unknown",
            phase=TrainingPhase(job["phase"]),
            progress=job["progress"],
            message=job["message"],
            eta=job["eta"]
        )
        for job in training_jobs.values()
        if job["userId"] == current_user["id"]
    ]
    
    return user_jobs

@router.get("/results/{job_id}", response_model=TrainingResults)
async def get_training_results(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get training job results"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    job = training_jobs[job_id]
    
    # Check user permission
    if job["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if job["status"] != "COMPLETE":
        raise HTTPException(status_code=400, detail="Training job not complete")
    
    # Generate sample results
    results = {
        "patterns": {
            "Liquidity Sweep": {
                "winRate": 0.68,
                "totalTrades": 45,
                "profitFactor": 1.85,
                "sharpeRatio": 1.42,
                "maxDrawdown": 0.08,
                "confidence": 0.85
            },
            "Volume Breakout": {
                "winRate": 0.72,
                "totalTrades": 32,
                "profitFactor": 2.1,
                "sharpeRatio": 1.67,
                "maxDrawdown": 0.06,
                "confidence": 0.91
            }
        },
        "overallScore": 0.88,
        "recommendedPatterns": ["Volume Breakout", "Liquidity Sweep"],
        "estimatedMonthlyReturn": 0.12,
        "estimatedMaxDrawdown": 0.15
    }
    
    return TrainingResults(
        jobId=job_id,
        assetSymbol=job["symbols"][0] if job["symbols"] else "Unknown",
        completedAt=job.get("completedAt", datetime.utcnow().isoformat()),
        results=results
    )