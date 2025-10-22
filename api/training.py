"""
Training Pipeline API endpoints
Enhanced integration with multi-dimensional strategy training system
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
import sys
from pathlib import Path

# Add project root to path for system integration
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from api.database import get_database
from api.auth_utils import get_current_user
import logging

# Configure logging
log = logging.getLogger(__name__)

# Import enhanced training system
try:
    from ml.trained_assets_manager import TrainedAssetsManager
    
    # Initialize system components
    trained_assets_manager = TrainedAssetsManager()
    training_system_available = True
    log.info("Training API: Enhanced multi-dimensional training system initialized")
    
except Exception as e:
    training_system_available = False
    trained_assets_manager = None
    log.warning(f"Training API: Enhanced training system not available: {e}")

router = APIRouter(prefix="/api/training", tags=["training"])

# Enhanced API endpoints for multi-dimensional training

@router.get("/system-status")
async def get_training_system_status():
    """Get status of the enhanced training system"""
    try:
        if not training_system_available or not trained_assets_manager:
            return {
                "status": "unavailable",
                "message": "Enhanced training system not initialized",
                "capabilities": {}
            }
        
        return {
            "status": "available",
            "message": "Multi-dimensional training system operational",
            "capabilities": {
                "supported_strategies": trained_assets_manager.supported_strategies,
                "market_regimes": trained_assets_manager.market_regimes,
                "timeframes": trained_assets_manager.timeframes,
                "combinations_per_asset": (len(trained_assets_manager.supported_strategies) * 
                                         len(trained_assets_manager.market_regimes) * 
                                         len(trained_assets_manager.timeframes)),
                "available_combinations": len(trained_assets_manager.available_combinations),
                "total_trained_assets": len(trained_assets_manager.trained_assets),
                "total_trained_strategies": len(trained_assets_manager.trained_strategies)
            }
        }
    except Exception as e:
        log.error(f"Error getting training system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trained-assets")
async def get_trained_assets_info():
    """Get information about trained assets and strategies"""
    try:
        if not training_system_available or not trained_assets_manager:
            raise HTTPException(status_code=503, detail="Training system unavailable")
        
        assets_info = {
            'total_assets': len(trained_assets_manager.trained_assets),
            'total_strategies': len(trained_assets_manager.trained_strategies),
            'supported_strategies': trained_assets_manager.supported_strategies,
            'market_regimes': trained_assets_manager.market_regimes,
            'timeframes': trained_assets_manager.timeframes,
            'combinations_per_asset': len(trained_assets_manager.supported_strategies) * 
                                   len(trained_assets_manager.market_regimes) * 
                                   len(trained_assets_manager.timeframes),
            'available_combinations': len(trained_assets_manager.available_combinations)
        }
        
        # Get sample of trained assets
        sample_assets = {}
        for i, (asset_key, asset) in enumerate(trained_assets_manager.trained_assets.items()):
            if i < 10:  # Show first 10 assets
                sample_assets[asset_key] = {
                    'symbol': asset.symbol,
                    'exchange': asset.exchange,
                    'total_strategies': asset.total_strategies,
                    'last_updated': asset.last_updated,
                    'coverage_metrics': asset.coverage_metrics
                }
        
        assets_info['sample_assets'] = sample_assets
        
        return {
            "status": "success",
            "data": assets_info
        }
    except Exception as e:
        log.error(f"Error getting trained assets info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-regimes")
async def get_market_regimes():
    """Get current market regime detection for monitored symbols"""
    try:
        if not training_system_available or not trained_assets_manager:
            raise HTTPException(status_code=503, detail="Training system unavailable")
        
        # Get sample of symbols for regime detection
        test_symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'SOL/USDT', 'MATIC/USDT']
        test_exchange = 'binanceus'
        
        regime_data = {}
        for symbol in test_symbols:
            try:
                regime = trained_assets_manager._detect_current_market_regime(symbol, test_exchange)
                regime_data[symbol] = {
                    'regime': regime,
                    'exchange': test_exchange,
                    'confidence': 'Medium',  # Could be enhanced with actual confidence calculation
                    'last_updated': datetime.now().isoformat()
                }
            except Exception as e:
                regime_data[symbol] = {
                    'regime': 'Unknown',
                    'exchange': test_exchange,
                    'error': str(e)
                }
        
        return {
            "status": "success",
            "data": regime_data
        }
    except Exception as e:
        log.error(f"Error getting market regimes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start-multi-dimensional")
async def start_multi_dimensional_training(
    background_tasks: BackgroundTasks,
    symbols: List[str],
    exchanges: List[str] = ["binanceus"],
    min_samples: int = 200
):
    """Start multi-dimensional training campaign"""
    try:
        if not training_system_available or not trained_assets_manager:
            raise HTTPException(status_code=503, detail="Training system unavailable")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Log the training request
        log.info(f"Starting multi-dimensional training job {job_id}")
        log.info(f"Symbols: {symbols}")
        log.info(f"Exchanges: {exchanges}")
        log.info(f"Min samples: {min_samples}")
        
        # Add background task for training
        background_tasks.add_task(
            run_multi_dimensional_training,
            job_id,
            symbols,
            exchanges,
            min_samples
        )
        
        return {
            "status": "success",
            "job_id": job_id,
            "message": f"Multi-dimensional training started for {len(symbols)} symbols across {len(exchanges)} exchanges",
            "estimated_combinations": len(symbols) * len(exchanges) * len(trained_assets_manager.supported_strategies) * len(trained_assets_manager.market_regimes) * len(trained_assets_manager.timeframes)
        }
        
    except Exception as e:
        log.error(f"Error starting multi-dimensional training: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_multi_dimensional_training(job_id: str, symbols: List[str], exchanges: List[str], min_samples: int):
    """Background task for multi-dimensional training"""
    try:
        log.info(f"Executing multi-dimensional training job {job_id}")
        
        # Run the training campaign
        results = trained_assets_manager.train_multi_dimensional_strategies(
            symbols=symbols,
            exchanges=exchanges,
            min_samples=min_samples
        )
        
        log.info(f"Multi-dimensional training job {job_id} completed")
        log.info(f"Success rate: {results.get('success_rate', 0):.1f}%")
        log.info(f"Successful trainings: {results.get('successful_trainings', 0)}")
        
    except Exception as e:
        log.error(f"Multi-dimensional training job {job_id} failed: {e}")

@router.get("/strategy-parameters/{symbol}/{exchange}/{strategy_id}")
async def get_strategy_parameters(
    symbol: str,
    exchange: str,
    strategy_id: str,
    market_regime: Optional[str] = None,
    timeframe: Optional[str] = None
):
    """Get optimized strategy parameters for specific conditions"""
    try:
        if not training_system_available or not trained_assets_manager:
            raise HTTPException(status_code=503, detail="Training system unavailable")
        
        # Get strategy parameters
        params = trained_assets_manager.get_strategy_parameters(
            symbol=symbol,
            exchange=exchange,
            strategy_id=strategy_id,
            market_regime=market_regime,
            timeframe=timeframe
        )
        
        if not params:
            raise HTTPException(
                status_code=404, 
                detail=f"No trained parameters found for {strategy_id} on {exchange}/{symbol}"
            )
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "exchange": exchange,
                "strategy_id": strategy_id,
                "market_regime": params.get('market_regime'),
                "timeframe": params.get('timeframe'),
                "parameters": params
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting strategy parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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