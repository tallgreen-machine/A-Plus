"""
Pattern Performance API endpoints
Handles pattern tracking, analytics, and parameter management
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
from enum import Enum

from api.database import get_database
from api.auth_utils import get_current_user
import logging

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/patterns", tags=["patterns"])

# TEMPORARY: Test endpoints without authentication
@router.get("/test-performance")
async def test_patterns_performance(db=Depends(get_database)):
    """Test patterns performance endpoint without authentication"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT pattern_name, status, total_trades, winning_trades, 
                       total_pnl, avg_win, avg_loss, win_rate
                FROM pattern_performance 
                ORDER BY total_pnl DESC 
                LIMIT 10
                """
            )
            patterns = cur.fetchall()
            
            if patterns:
                return [
                    {
                        "id": f"pattern-{i}",
                        "name": pattern['pattern_name'],
                        "status": pattern['status'] or "ACTIVE",
                        "totalPL": float(pattern['total_pnl'] or 0),
                        "winLossRatio": float(pattern['win_rate'] or 0),
                        "totalTrades": int(pattern['total_trades'] or 0),
                        "lastTradeTime": "2024-01-01T10:00:00"
                    }
                    for i, pattern in enumerate(patterns)
                ]
            else:
                # Return sample data
                return [
                    {
                        "id": "pattern-1",
                        "name": "Liquidity Sweep Reversal",
                        "status": "ACTIVE",
                        "totalPL": 2500.0,
                        "winLossRatio": 2.1,
                        "totalTrades": 45,
                        "lastTradeTime": "2024-01-01T10:00:00"
                    },
                    {
                        "id": "pattern-2", 
                        "name": "Capitulation Reversal",
                        "status": "ACTIVE",
                        "totalPL": 1800.0,
                        "winLossRatio": 1.8,
                        "totalTrades": 32,
                        "lastTradeTime": "2024-01-01T09:30:00"
                    }
                ]
    except Exception as e:
        return {"error": str(e)}

@router.get("/test-trained-assets")
async def test_trained_assets(db=Depends(get_database)):
    """Test trained assets endpoint without authentication"""
    try:
        # Return sample trained assets data
        return [
            {
                "symbol": "BTC/USDT",
                "patterns": [
                    {"patternId": "pattern-1", "initials": "LSR", "totalPL": 1500.0, "status": "ACTIVE"},
                    {"patternId": "pattern-2", "initials": "CR", "totalPL": 800.0, "status": "ACTIVE"}
                ],
                "totalPL": 2300.0,
                "activePatterns": 2,
                "status": "ACTIVE"
            },
            {
                "symbol": "ETH/USDT", 
                "patterns": [
                    {"patternId": "pattern-1", "initials": "LSR", "totalPL": 900.0, "status": "ACTIVE"},
                    {"patternId": "pattern-2", "initials": "CR", "totalPL": 650.0, "status": "PAUSED"}
                ],
                "totalPL": 1550.0,
                "activePatterns": 1,
                "status": "ACTIVE"
            }
        ]
    except Exception as e:
        return {"error": str(e)}

# Enums
class PatternStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    PAPER_TRADING = "PAPER_TRADING"

# Pydantic models
class PatternPerformance(BaseModel):
    id: str
    name: str
    status: PatternStatus
    totalPL: float
    winLossRatio: float
    totalTrades: int
    parameters: Dict[str, Any]

class TrainedAsset(BaseModel):
    symbol: str
    patterns: List[Dict[str, Any]]

def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

@router.get("/performance", response_model=List[PatternPerformance])
async def get_patterns_performance(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get pattern performance metrics"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT p.id, p.name, pp.status, pp.total_pnl, pp.win_rate, 
                       pp.total_trades, pp.winning_trades, pp.losing_trades
                FROM patterns p
                LEFT JOIN pattern_performance pp ON p.id = pp.pattern_id AND pp.user_id = %s
                WHERE p.is_active = true
                ORDER BY pp.total_pnl DESC NULLS LAST
                """,
                (current_user["id"],)
            )
            pattern_rows = cur.fetchall()
            
            if not pattern_rows:
                # Return sample patterns if none exist
                return [
                    PatternPerformance(
                        id="1",
                        name="Liquidity Sweep",
                        status=PatternStatus.ACTIVE,
                        totalPL=1250.50,
                        winLossRatio=1.8,
                        totalTrades=45,
                        parameters={
                            "primaryTimeframe": "1h",
                            "macroTimeframe": "4h",
                            "riskRewardRatio": 2.0,
                            "stopLossType": "ATR",
                            "stopLossValue": 1.5
                        }
                    ),
                    PatternPerformance(
                        id="2",
                        name="Volume Breakout",
                        status=PatternStatus.ACTIVE,
                        totalPL=890.25,
                        winLossRatio=1.5,
                        totalTrades=32,
                        parameters={
                            "primaryTimeframe": "15m",
                            "macroTimeframe": "1h",
                            "riskRewardRatio": 1.8,
                            "stopLossType": "Percentage",
                            "stopLossValue": 2.0
                        }
                    ),
                    PatternPerformance(
                        id="3",
                        name="Divergence Capitulation",
                        status=PatternStatus.PAUSED,
                        totalPL=-150.75,
                        winLossRatio=0.9,
                        totalTrades=18,
                        parameters={
                            "primaryTimeframe": "1h",
                            "macroTimeframe": "4h",
                            "riskRewardRatio": 2.5,
                            "stopLossType": "ATR",
                            "stopLossValue": 2.0
                        }
                    )
                ]
            
            results = []
            for row in pattern_rows:
                # Calculate win/loss ratio
                win_loss_ratio = 0.0
                if row["losing_trades"] and row["losing_trades"] > 0:
                    win_loss_ratio = decimal_to_float(row["winning_trades"]) / decimal_to_float(row["losing_trades"])
                
                # Get pattern parameters
                cur.execute(
                    """
                    SELECT parameter_name, parameter_value
                    FROM pattern_parameters
                    WHERE pattern_id = %s AND user_id = %s
                    """,
                    (row["id"], current_user["id"])
                )
                param_rows = cur.fetchall()
                parameters = {param["parameter_name"]: param["parameter_value"] for param in param_rows}
                
                # Add default parameters if none exist
                if not parameters:
                    parameters = {
                        "primaryTimeframe": "1h",
                        "macroTimeframe": "4h",
                        "riskRewardRatio": 2.0,
                        "stopLossType": "ATR",
                        "stopLossValue": 1.5
                    }
                
                results.append(PatternPerformance(
                    id=str(row["id"]),
                    name=row["name"],
                    status=PatternStatus(row["status"]) if row["status"] else PatternStatus.ACTIVE,
                    totalPL=decimal_to_float(row["total_pnl"]) or 0.0,
                    winLossRatio=win_loss_ratio,
                    totalTrades=row["total_trades"] or 0,
                    parameters=parameters
                ))
            
            return results
            
    except Exception as e:
        log.error(f"Error getting pattern performance for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pattern performance")

@router.get("/trained-assets", response_model=List[TrainedAsset])
async def get_trained_assets(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get assets that have been trained with patterns"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT pp.symbol, p.id as pattern_id, p.name, pp.status, pp.total_pnl
                FROM pattern_performance pp
                JOIN patterns p ON pp.pattern_id = p.id
                WHERE pp.user_id = %s AND pp.symbol IS NOT NULL
                ORDER BY pp.symbol, pp.total_pnl DESC
                """,
                (current_user["id"],)
            )
            asset_rows = cur.fetchall()
            
            if not asset_rows:
                # Return sample trained assets if none exist
                return [
                    TrainedAsset(
                        symbol="BTC/USDT",
                        patterns=[
                            {
                                "patternId": "1",
                                "initials": "LS",
                                "totalPL": 1250.50,
                                "status": "ACTIVE"
                            },
                            {
                                "patternId": "2", 
                                "initials": "VB",
                                "totalPL": 890.25,
                                "status": "ACTIVE"
                            }
                        ]
                    ),
                    TrainedAsset(
                        symbol="ETH/USDT",
                        patterns=[
                            {
                                "patternId": "1",
                                "initials": "LS",
                                "totalPL": 675.30,
                                "status": "ACTIVE"
                            },
                            {
                                "patternId": "3",
                                "initials": "DC", 
                                "totalPL": -150.75,
                                "status": "PAUSED"
                            }
                        ]
                    )
                ]
            
            # Group by symbol
            assets_dict = {}
            for row in asset_rows:
                symbol = row["symbol"]
                if symbol not in assets_dict:
                    assets_dict[symbol] = []
                
                # Create initials from pattern name
                initials = "".join([word[0] for word in row["name"].split()[:2]]).upper()
                
                assets_dict[symbol].append({
                    "patternId": str(row["pattern_id"]),
                    "initials": initials,
                    "totalPL": decimal_to_float(row["total_pnl"]) or 0.0,
                    "status": row["status"] or "ACTIVE"
                })
            
            return [
                TrainedAsset(symbol=symbol, patterns=patterns)
                for symbol, patterns in assets_dict.items()
            ]
            
    except Exception as e:
        log.error(f"Error getting trained assets for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trained assets")

@router.get("/{pattern_id}/parameters")
async def get_pattern_parameters(
    pattern_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get pattern parameters"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT parameter_name, parameter_value, parameter_type, default_value, description
                FROM pattern_parameters
                WHERE pattern_id = %s AND user_id = %s
                """,
                (pattern_id, current_user["id"])
            )
            param_rows = cur.fetchall()
            
            return {
                param["parameter_name"]: {
                    "value": param["parameter_value"],
                    "type": param["parameter_type"],
                    "default": param["default_value"],
                    "description": param["description"]
                }
                for param in param_rows
            }
            
    except Exception as e:
        log.error(f"Error getting pattern parameters: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pattern parameters")

@router.put("/{pattern_id}/parameters")
async def update_pattern_parameters(
    pattern_id: int,
    parameters: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Update pattern parameters"""
    try:
        with db.cursor() as cur:
            for param_name, param_value in parameters.items():
                cur.execute(
                    """
                    INSERT INTO pattern_parameters (pattern_id, user_id, parameter_name, parameter_value, parameter_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (pattern_id, user_id, parameter_name)
                    DO UPDATE SET parameter_value = EXCLUDED.parameter_value, updated_at = CURRENT_TIMESTAMP
                    """,
                    (pattern_id, current_user["id"], param_name, param_value, type(param_value).__name__)
                )
            db.commit()
            
        return {"message": "Parameters updated successfully"}
        
    except Exception as e:
        log.error(f"Error updating pattern parameters: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pattern parameters")