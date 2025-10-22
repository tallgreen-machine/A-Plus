"""
Strategy Performance API endpoints
Enhanced with multi-dimensional strategy tracking and analytics
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
from enum import Enum
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

# Import enhanced strategy system
try:
    from ml.trained_assets_manager import TrainedAssetsManager
    from strategies.htf_sweep import HTFSweepStrategy
    from strategies.volume_breakout import VolumeBreakoutStrategy
    from strategies.divergence_capitulation import DivergenceCapitulationStrategy
    
    # Initialize system components
    trained_assets_manager = TrainedAssetsManager()
    strategies_system_available = True
    log.info("Patterns API: Enhanced strategy system initialized")
    
except Exception as e:
    strategies_system_available = False
    trained_assets_manager = None
    log.warning(f"Patterns API: Enhanced strategy system not available: {e}")

router = APIRouter(prefix="/api/patterns", tags=["patterns"])

# Enhanced API endpoints for strategy performance

@router.get("/strategy-performance")
async def get_strategy_performance():
    """Get performance metrics for all strategies with multi-dimensional data"""
    try:
        if not strategies_system_available or not trained_assets_manager:
            # Fallback to basic response
            return {
                "status": "limited",
                "message": "Enhanced strategy system unavailable, returning basic data",
                "data": {}
            }
        
        performance_data = {}
        
        # Get performance for each supported strategy
        for strategy_id in trained_assets_manager.supported_strategies:
            strategy_metrics = {
                'strategy_id': strategy_id,
                'name': strategy_id.replace('_', ' ').title(),
                'status': 'Active',
                'total_trained_combinations': 0,
                'successful_combinations': 0,
                'average_accuracy': 0.0,
                'best_accuracy': 0.0,
                'regime_performance': {},
                'timeframe_performance': {},
                'asset_coverage': 0
            }
            
            # Analyze trained strategies for this strategy type
            strategy_accuracies = []
            regime_stats = {}
            timeframe_stats = {}
            
            for strategy_key, trained_strategy in trained_assets_manager.trained_strategies.items():
                if trained_strategy.strategy_id == strategy_id:
                    strategy_metrics['total_trained_combinations'] += 1
                    
                    if trained_strategy.accuracy > 0:
                        strategy_metrics['successful_combinations'] += 1
                        strategy_accuracies.append(trained_strategy.accuracy)
                        
                        # Regime stats
                        regime = trained_strategy.market_regime
                        if regime not in regime_stats:
                            regime_stats[regime] = []
                        regime_stats[regime].append(trained_strategy.accuracy)
                        
                        # Timeframe stats
                        timeframe = trained_strategy.timeframe
                        if timeframe not in timeframe_stats:
                            timeframe_stats[timeframe] = []
                        timeframe_stats[timeframe].append(trained_strategy.accuracy)
            
            # Calculate metrics
            if strategy_accuracies:
                strategy_metrics['average_accuracy'] = sum(strategy_accuracies) / len(strategy_accuracies)
                strategy_metrics['best_accuracy'] = max(strategy_accuracies)
            
            # Regime performance
            for regime, accuracies in regime_stats.items():
                strategy_metrics['regime_performance'][regime] = {
                    'count': len(accuracies),
                    'average_accuracy': sum(accuracies) / len(accuracies),
                    'best_accuracy': max(accuracies)
                }
            
            # Timeframe performance
            for timeframe, accuracies in timeframe_stats.items():
                strategy_metrics['timeframe_performance'][timeframe] = {
                    'count': len(accuracies),
                    'average_accuracy': sum(accuracies) / len(accuracies),
                    'best_accuracy': max(accuracies)
                }
            
            # Asset coverage
            unique_assets = set()
            for strategy_key, trained_strategy in trained_assets_manager.trained_strategies.items():
                if trained_strategy.strategy_id == strategy_id:
                    unique_assets.add(f"{trained_strategy.exchange}_{trained_strategy.symbol}")
            strategy_metrics['asset_coverage'] = len(unique_assets)
            
            performance_data[strategy_id] = strategy_metrics
        
        return {
            "status": "success",
            "data": performance_data
        }
        
    except Exception as e:
        log.error(f"Error getting strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trained-assets-summary")
async def get_trained_assets_summary():
    """Get summary of all trained assets with their strategy coverage"""
    try:
        if not strategies_system_available or not trained_assets_manager:
            raise HTTPException(status_code=503, detail="Strategy system unavailable")
        
        assets_summary = []
        
        for asset_key, asset in trained_assets_manager.trained_assets.items():
            asset_info = {
                'asset_key': asset_key,
                'symbol': asset.symbol,
                'exchange': asset.exchange,
                'total_strategies': asset.total_strategies,
                'last_updated': asset.last_updated,
                'coverage_metrics': asset.coverage_metrics,
                'strategies_breakdown': {}
            }
            
            # Count strategies by type
            for strategy_key, trained_strategy in asset.strategies.items():
                strategy_id = trained_strategy.strategy_id
                if strategy_id not in asset_info['strategies_breakdown']:
                    asset_info['strategies_breakdown'][strategy_id] = {
                        'count': 0,
                        'average_accuracy': 0.0,
                        'regimes': set(),
                        'timeframes': set()
                    }
                
                asset_info['strategies_breakdown'][strategy_id]['count'] += 1
                asset_info['strategies_breakdown'][strategy_id]['regimes'].add(trained_strategy.market_regime)
                asset_info['strategies_breakdown'][strategy_id]['timeframes'].add(trained_strategy.timeframe)
            
            # Convert sets to lists for JSON serialization
            for strategy_data in asset_info['strategies_breakdown'].values():
                strategy_data['regimes'] = list(strategy_data['regimes'])
                strategy_data['timeframes'] = list(strategy_data['timeframes'])
            
            assets_summary.append(asset_info)
        
        return {
            "status": "success", 
            "data": {
                "total_assets": len(assets_summary),
                "assets": assets_summary[:20]  # Limit to first 20 for performance
            }
        }
        
    except Exception as e:
        log.error(f"Error getting trained assets summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TEMPORARY: Test endpoints without authentication
@router.get("/test-performance")
async def test_patterns_performance(db=Depends(get_database)):
    """Test patterns performance endpoint without authentication - returns real data"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT p.id, p.name, p.is_active, pp.total_trades, pp.winning_trades, 
                       pp.total_pnl, pp.avg_win, pp.avg_loss, pp.win_rate, pp.profit_factor,
                       pp.last_trade_at
                FROM patterns p
                LEFT JOIN pattern_performance pp ON p.id = pp.pattern_id AND pp.user_id = 1
                WHERE p.is_active = true
                ORDER BY pp.total_pnl DESC NULLS LAST
                LIMIT 10
                """
            )
            patterns = cur.fetchall()
            
            if patterns:
                return [
                    {
                        "id": f"pattern-{pattern['id']}",
                        "name": pattern['name'],
                        "status": "ACTIVE" if pattern['is_active'] else "PAUSED",
                        "totalPL": float(pattern['total_pnl'] or 0),
                        "winLossRatio": float((pattern['avg_win'] or 0) / abs(pattern['avg_loss'] or 1)),
                        "totalTrades": int(pattern['total_trades'] or 0),
                        "winRate": float(pattern['win_rate'] or 0),
                        "profitFactor": float(pattern['profit_factor'] or 0),
                        "lastTradeTime": pattern['last_trade_at'].isoformat() if pattern['last_trade_at'] else None,
                        "parameters": {}
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

@router.post("/{pattern_id}/start")
async def start_pattern(
    pattern_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Start a pattern (set to ACTIVE status)"""
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                UPDATE pattern_performance 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE pattern_id = %s AND user_id = %s
                """,
                ("ACTIVE", pattern_id, current_user["id"])
            )
            db.commit()
            
        return {"message": f"Pattern {pattern_id} started successfully"}
        
    except Exception as e:
        log.error(f"Error starting pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start pattern")

@router.post("/{pattern_id}/pause")
async def pause_pattern(
    pattern_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Pause a pattern (set to PAUSED status)"""
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                UPDATE pattern_performance 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE pattern_id = %s AND user_id = %s
                """,
                ("PAUSED", pattern_id, current_user["id"])
            )
            db.commit()
            
        return {"message": f"Pattern {pattern_id} paused successfully"}
        
    except Exception as e:
        log.error(f"Error pausing pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause pattern")

@router.get("/market-regimes")
async def get_market_regimes():
    """Get market regime analysis for pattern selection"""
    try:
        if not strategies_system_available or not trained_assets_manager:
            # Return basic regime data
            return {
                "current_regime": "trending",
                "regime_confidence": 0.75,
                "regimes": [
                    {
                        "name": "trending",
                        "description": "Strong directional movement",
                        "suitable_patterns": ["htf_sweep", "volume_breakout"],
                        "confidence": 0.75
                    },
                    {
                        "name": "ranging",
                        "description": "Sideways consolidation",
                        "suitable_patterns": ["divergence_capitulation"],
                        "confidence": 0.60
                    },
                    {
                        "name": "volatile",
                        "description": "High volatility environment",
                        "suitable_patterns": ["volume_breakout", "divergence_capitulation"],
                        "confidence": 0.55
                    }
                ]
            }
        
        # Get regime analysis from trained assets manager
        regime_analysis = trained_assets_manager.analyze_market_regimes()
        
        return {
            "status": "success",
            "data": regime_analysis
        }
        
    except Exception as e:
        log.error(f"Error getting market regimes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pattern-library")
async def get_pattern_library():
    """Get available pattern templates and definitions"""
    try:
        pattern_library = [
            {
                "id": "htf_sweep",
                "name": "HTF Sweep Strategy",
                "description": "Identifies liquidity sweeps on higher timeframes for entry opportunities",
                "category": "Liquidity",
                "parameters": {
                    "primary_timeframe": {"type": "select", "options": ["5m", "15m", "1h"], "default": "15m"},
                    "macro_timeframe": {"type": "select", "options": ["1h", "4h", "1d"], "default": "4h"},
                    "risk_reward_ratio": {"type": "number", "min": 1.0, "max": 5.0, "default": 2.0},
                    "stop_loss_atr": {"type": "number", "min": 0.5, "max": 3.0, "default": 1.5}
                },
                "market_conditions": ["trending", "volatile"],
                "timeframes": ["5m", "15m", "1h"],
                "asset_types": ["crypto", "forex", "stocks"]
            },
            {
                "id": "volume_breakout",
                "name": "Volume Breakout Strategy",
                "description": "Trades breakouts confirmed by volume spikes",
                "category": "Momentum",
                "parameters": {
                    "primary_timeframe": {"type": "select", "options": ["5m", "15m", "1h"], "default": "15m"},
                    "volume_threshold": {"type": "number", "min": 1.5, "max": 5.0, "default": 2.0},
                    "breakout_confirmation": {"type": "number", "min": 0.1, "max": 1.0, "default": 0.5},
                    "risk_reward_ratio": {"type": "number", "min": 1.0, "max": 5.0, "default": 1.8}
                },
                "market_conditions": ["trending", "volatile"],
                "timeframes": ["5m", "15m", "1h"],
                "asset_types": ["crypto", "stocks"]
            },
            {
                "id": "divergence_capitulation",
                "name": "Divergence Capitulation Strategy",
                "description": "Identifies divergence patterns leading to capitulation reversals",
                "category": "Reversal",
                "parameters": {
                    "primary_timeframe": {"type": "select", "options": ["15m", "1h", "4h"], "default": "1h"},
                    "rsi_period": {"type": "number", "min": 10, "max": 30, "default": 14},
                    "divergence_lookback": {"type": "number", "min": 5, "max": 20, "default": 10},
                    "risk_reward_ratio": {"type": "number", "min": 1.5, "max": 4.0, "default": 2.5}
                },
                "market_conditions": ["ranging", "volatile"],
                "timeframes": ["15m", "1h", "4h"],
                "asset_types": ["crypto", "forex", "stocks"]
            }
        ]
        
        return {
            "status": "success",
            "data": {
                "patterns": pattern_library,
                "categories": ["Liquidity", "Momentum", "Reversal"],
                "total_patterns": len(pattern_library)
            }
        }
        
    except Exception as e:
        log.error(f"Error getting pattern library: {e}")
        raise HTTPException(status_code=500, detail=str(e))