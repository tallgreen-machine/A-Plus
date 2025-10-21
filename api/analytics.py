"""
Asset Analytics API endpoints
Handles asset ranking, viability assessment, and detailed analytics
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
from enum import Enum

from database import get_database
from auth_utils import get_current_user
import logging

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Enums
class PatternStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    PAPER_TRADING = "PAPER_TRADING"

# Pydantic models
class AssetAnalytics(BaseModel):
    symbol: str
    totalPL: float
    winRate: float
    totalTrades: int
    avgProfit: float
    avgLoss: float
    sharpeRatio: float
    maxDrawdown: float
    volatilityIndex: float
    liquidityScore: float
    patternBreakdown: List[Dict[str, Any]]

class TrainedAssetDetails(BaseModel):
    symbol: str
    patterns: List[Dict[str, Any]]

class WalkForwardResult(BaseModel):
    period: str
    winRate: float
    totalReturn: float
    maxDrawdown: float
    sharpeRatio: float

def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

@router.get("/assets/{symbol}", response_model=AssetAnalytics)
async def get_asset_analytics(
    symbol: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get detailed analytics for a specific asset"""
    try:
        # In production, this would query the database for real analytics
        # For now, generate sample data based on the symbol
        
        # Base metrics that vary by symbol
        symbol_metrics = {
            "BTC/USDT": {
                "totalPL": 2345.75,
                "winRate": 0.68,
                "totalTrades": 156,
                "avgProfit": 145.30,
                "avgLoss": -67.85,
                "sharpeRatio": 1.85,
                "maxDrawdown": 0.12,
                "volatilityIndex": 8.5,
                "liquidityScore": 9.8
            },
            "ETH/USDT": {
                "totalPL": 1567.40,
                "winRate": 0.72,
                "totalTrades": 128,
                "avgProfit": 132.60,
                "avgLoss": -71.20,
                "sharpeRatio": 1.92,
                "maxDrawdown": 0.09,
                "volatilityIndex": 8.8,
                "liquidityScore": 9.5
            }
        }
        
        # Use BTC/USDT as default if symbol not found
        metrics = symbol_metrics.get(symbol, symbol_metrics["BTC/USDT"])
        
        # Generate pattern breakdown
        pattern_breakdown = [
            {
                "patternName": "Liquidity Sweep",
                "trades": 67,
                "winRate": 0.71,
                "totalPL": 1234.50,
                "avgProfit": 167.30,
                "avgLoss": -78.90,
                "status": "ACTIVE"
            },
            {
                "patternName": "Volume Breakout",
                "trades": 54,
                "winRate": 0.65,
                "totalPL": 891.25,
                "avgProfit": 145.70,
                "avgLoss": -82.40,
                "status": "ACTIVE"
            },
            {
                "patternName": "Divergence Capitulation",
                "trades": 35,
                "winRate": 0.51,
                "totalPL": 220.00,
                "avgProfit": 125.80,
                "avgLoss": -89.30,
                "status": "PAUSED"
            }
        ]
        
        return AssetAnalytics(
            symbol=symbol,
            totalPL=metrics["totalPL"],
            winRate=metrics["winRate"],
            totalTrades=metrics["totalTrades"],
            avgProfit=metrics["avgProfit"],
            avgLoss=metrics["avgLoss"],
            sharpeRatio=metrics["sharpeRatio"],
            maxDrawdown=metrics["maxDrawdown"],
            volatilityIndex=metrics["volatilityIndex"],
            liquidityScore=metrics["liquidityScore"],
            patternBreakdown=pattern_breakdown
        )
        
    except Exception as e:
        log.error(f"Error getting asset analytics for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve asset analytics")

@router.get("/assets/{symbol}/details", response_model=TrainedAssetDetails)
async def get_asset_details(
    symbol: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get detailed training information for an asset"""
    try:
        # Generate sample detailed asset information
        sample_patterns = [
            {
                "id": "1",
                "name": "Liquidity Sweep",
                "status": "ACTIVE",
                "parameters": {
                    "primaryTimeframe": "1h",
                    "macroTimeframe": "4h",
                    "primarySignal": {
                        "lookback": 20,
                        "threshold": 0.8
                    },
                    "macroConfirmation": {
                        "trendFilter": "EMA_200",
                        "requiredState": "Above"
                    },
                    "riskManagement": {
                        "riskRewardRatio": 2.0,
                        "stopLossType": "ATR",
                        "stopLossValue": 1.5
                    }
                },
                "trainedHistory": "2024-10-15T14:30:00Z",
                "analytics": {
                    "winRate": 0.71,
                    "avgProfit": 167.30,
                    "avgLoss": -78.90
                },
                "regimePerformance": [
                    {
                        "regime": "Bull Market",
                        "status": "ACTIVE",
                        "exchangePerformance": [
                            {
                                "exchange": "binanceus",
                                "status": "ACTIVE",
                                "winRate": 0.75,
                                "avgProfit": 180.50,
                                "avgLoss": -72.30,
                                "totalTrades": 45,
                                "totalPL": 1234.75,
                                "avgSlippage": 0.08,
                                "avgFees": 0.12,
                                "avgLatencyMs": 45
                            }
                        ]
                    }
                ],
                "recentTrades": [
                    {
                        "id": 1,
                        "timestamp": "2024-10-20T10:30:00Z",
                        "symbol": symbol,
                        "direction": "BUY",
                        "quantity": 0.1,
                        "price": 67500.0,
                        "fill_cost": 6750.0,
                        "pnl": 150.75
                    }
                ]
            }
        ]
        
        return TrainedAssetDetails(
            symbol=symbol,
            patterns=sample_patterns
        )
        
    except Exception as e:
        log.error(f"Error getting asset details for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve asset details")

@router.get("/walk-forward/{symbol}", response_model=List[WalkForwardResult])
async def get_walk_forward_results(
    symbol: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get walk-forward validation results for an asset"""
    try:
        # Generate sample walk-forward validation results
        base_date = datetime.utcnow() - timedelta(days=180)
        
        results = []
        for i in range(6):  # 6 months of data
            period_start = base_date + timedelta(days=i*30)
            period_end = period_start + timedelta(days=30)
            
            # Simulate varying performance over time
            base_win_rate = 0.65 + (i * 0.02) - (0.1 if i > 3 else 0)  # Performance degrades over time
            base_return = 0.08 + (i * 0.01) - (0.15 if i > 3 else 0)
            
            results.append(WalkForwardResult(
                period=f"{period_start.strftime('%Y-%m')} to {period_end.strftime('%Y-%m')}",
                winRate=max(0.4, min(0.8, base_win_rate)),
                totalReturn=max(-0.2, min(0.3, base_return)),
                maxDrawdown=0.05 + (i * 0.01),
                sharpeRatio=max(0.5, 2.0 - (i * 0.2))
            ))
        
        return results
        
    except Exception as e:
        log.error(f"Error getting walk-forward results for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve walk-forward results")

@router.get("/market-overview")
async def get_market_overview(current_user: dict = Depends(get_current_user)):
    """Get overall market analytics and insights"""
    try:
        overview = {
            "totalAssets": 25,
            "activePatterns": 4,
            "totalTrades": 1547,
            "overallWinRate": 0.68,
            "totalPL": 8756.30,
            "bestPerformingAsset": "ETH/USDT",
            "worstPerformingAsset": "ADA/USDT",
            "marketRegime": "SIDEWAYS",
            "regimeConfidence": 0.78,
            "riskLevel": "MEDIUM",
            "recommendations": [
                "Consider reducing position sizes in high volatility assets",
                "ETH/USDT showing strong pattern consistency",
                "Review Divergence Capitulation pattern parameters"
            ],
            "alerts": [
                {
                    "type": "WARNING",
                    "message": "DOGE/USDT pattern performance below threshold",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "type": "INFO", 
                    "message": "New training data available for BTC/USDT",
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat()
                }
            ]
        }
        
        return overview
        
    except Exception as e:
        log.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve market overview")

@router.get("/correlation-matrix")
async def get_correlation_matrix(current_user: dict = Depends(get_current_user)):
    """Get asset correlation matrix for portfolio optimization"""
    try:
        # Generate sample correlation matrix
        assets = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"]
        
        # Generate realistic correlation values
        correlation_matrix = {}
        for i, asset1 in enumerate(assets):
            correlation_matrix[asset1] = {}
            for j, asset2 in enumerate(assets):
                if i == j:
                    correlation_matrix[asset1][asset2] = 1.0
                elif abs(i - j) == 1:
                    correlation_matrix[asset1][asset2] = 0.7 + (0.1 * (i + j) % 3)  # High correlation for adjacent pairs
                else:
                    correlation_matrix[asset1][asset2] = 0.3 + (0.2 * (i + j) % 4)  # Moderate correlation for others
        
        return {
            "assets": assets,
            "correlationMatrix": correlation_matrix,
            "lastUpdated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting correlation matrix: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve correlation matrix")