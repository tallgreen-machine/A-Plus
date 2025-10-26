"""
Training Configurations API
Handles CRUD operations for trained strategy configurations (V2 Dashboard)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, UUID4
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import logging
import psycopg2.extras

from api.database import get_database

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training/configurations", tags=["Training Configurations"])


# =============================================================================
# Pydantic Models
# =============================================================================

class ConfigurationFilter(BaseModel):
    """Filter parameters for querying configurations"""
    strategy_name: Optional[str] = None
    exchange: Optional[str] = None
    pair: Optional[str] = None
    timeframe: Optional[str] = None
    regime: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class ConfigurationResponse(BaseModel):
    """Response model for a trained configuration"""
    id: str
    strategy_name: str
    exchange: str
    pair: str
    timeframe: str
    regime: str
    status: str
    is_active: bool
    parameters_json: Dict[str, Any]
    
    # Performance metrics
    gross_win_rate: Optional[float]
    avg_win: Optional[float]
    avg_loss: Optional[float]
    net_profit: Optional[float]
    sample_size: Optional[int]
    
    # Statistical validation
    sharpe_ratio: Optional[float]
    calmar_ratio: Optional[float]
    p_value: Optional[float]
    stability_score: Optional[float]
    
    # Execution metrics
    fill_rate: Optional[float]
    adverse_selection_score: Optional[float]
    
    # Risk metrics
    max_position_size: Optional[float]
    var_95: Optional[float]
    
    # Health tracking
    months_since_discovery: Optional[int]
    performance_degradation: Optional[float]
    death_signal_count: Optional[int]
    
    # Training metadata
    model_version: Optional[str]
    engine_hash: Optional[str]
    runtime_env: Optional[str]
    metadata_json: Optional[Dict[str, Any]]
    job_id: Optional[int]  # Training job ID that created this configuration
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_activated_at: Optional[datetime]
    last_deactivated_at: Optional[datetime]

    class Config:
        from_attributes = True


# =============================================================================
# Helper Functions
# =============================================================================

def convert_decimals(data: dict) -> dict:
    """Convert Decimal objects to float for JSON serialization"""
    result = {}
    for key, value in data.items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, dict):
            result[key] = convert_decimals(value)
        else:
            result[key] = value
    return result


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/", response_model=List[ConfigurationResponse])
async def list_configurations(
    strategy_name: Optional[str] = Query(None, description="Filter by strategy name"),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    pair: Optional[str] = Query(None, description="Filter by trading pair"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe"),
    regime: Optional[str] = Query(None, description="Filter by market regime"),
    status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """
    List all trained configurations with optional filters
    
    **Filters:**
    - strategy_name: e.g., "LIQUIDITY_SWEEP_V3", "HTF_SWEEP"
    - exchange: e.g., "binance", "coinbase"
    - pair: e.g., "BTC/USDT", "ETH/USDT"
    - timeframe: e.g., "1h", "4h", "1d"
    - regime: e.g., "bull", "bear", "sideways"
    - status: e.g., "DISCOVERY", "VALIDATION", "MATURE", "DECAY", "PAPER"
    - is_active: true/false
    """
    try:
        db = get_database()
        
        # Build dynamic query based on filters
        conditions = []
        params = []
        
        if strategy_name:
            conditions.append("strategy_name = %s")
            params.append(strategy_name)
        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)
        if pair:
            conditions.append("pair = %s")
            params.append(pair)
        if timeframe:
            conditions.append("timeframe = %s")
            params.append(timeframe)
        if regime:
            conditions.append("regime = %s")
            params.append(regime)
        if status:
            conditions.append("status = %s")
            params.append(status)
        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(is_active)
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
            SELECT 
                id, strategy_name, exchange, pair, timeframe, regime, status, is_active,
                parameters_json, gross_win_rate, avg_win, avg_loss, net_profit, sample_size,
                sharpe_ratio, calmar_ratio, p_value, stability_score,
                fill_rate, adverse_selection_score,
                max_position_size, var_95,
                months_since_discovery, performance_degradation, death_signal_count,
                model_version, engine_hash, runtime_env, metadata_json, job_id,
                created_at, updated_at, last_activated_at, last_deactivated_at
            FROM trained_configurations
            WHERE {where_clause}
            ORDER BY net_profit DESC NULLS LAST, sharpe_ratio DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        # Convert Decimal to float for JSON serialization
        configurations = [convert_decimals(dict(row)) for row in results]
        
        log.info(f"Retrieved {len(configurations)} configurations with filters: {dict(zip(['strategy_name', 'exchange', 'pair', 'timeframe', 'regime', 'status', 'is_active'], [strategy_name, exchange, pair, timeframe, regime, status, is_active]))}")
        
        return configurations
        
    except Exception as e:
        log.error(f"Error retrieving configurations: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{configuration_id}", response_model=ConfigurationResponse)
async def get_configuration(configuration_id: str):
    """Get a specific configuration by ID"""
    try:
        db = get_database()
        
        query = """
            SELECT 
                id, strategy_name, exchange, pair, timeframe, regime, status, is_active,
                parameters_json, gross_win_rate, avg_win, avg_loss, net_profit, sample_size,
                sharpe_ratio, calmar_ratio, p_value, stability_score,
                fill_rate, adverse_selection_score,
                max_position_size, var_95,
                months_since_discovery, performance_degradation, death_signal_count,
                model_version, engine_hash, runtime_env, metadata_json, job_id,
                created_at, updated_at, last_activated_at, last_deactivated_at
            FROM trained_configurations
            WHERE id = %s
        """
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, (configuration_id,))
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Configuration {configuration_id} not found")
        
        configuration = convert_decimals(dict(result))
        
        return configuration
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving configuration {configuration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{configuration_id}/activate")
async def activate_configuration(configuration_id: str):
    """
    Activate a configuration for live trading
    
    Sets is_active=true and updates last_activated_at timestamp.
    Does NOT change status - status remains as lifecycle stage (DISCOVERY/VALIDATION/MATURE/etc.)
    """
    try:
        db = get_database()
        
        query = """
            UPDATE trained_configurations
            SET is_active = true,
                last_activated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, strategy_name, exchange, pair, timeframe, regime, status
        """
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, (configuration_id,))
        result = cursor.fetchone()
        db.commit()
        cursor.close()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Configuration {configuration_id} not found")
        
        log.info(f"Activated configuration: {result['strategy_name']} on {result['exchange']} {result['pair']} {result['timeframe']} (lifecycle: {result['status']})")
        
        return {
            "success": True,
            "message": f"Configuration {configuration_id} activated",
            "configuration": dict(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error activating configuration {configuration_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{configuration_id}/deactivate")
async def deactivate_configuration(configuration_id: str):
    """
    Deactivate a configuration (stop live trading)
    
    Sets is_active=false and updates last_deactivated_at timestamp.
    Does NOT change status - status remains as lifecycle stage (DISCOVERY/VALIDATION/MATURE/etc.)
    """
    try:
        db = get_database()
        
        query = """
            UPDATE trained_configurations
            SET is_active = false,
                last_deactivated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, strategy_name, exchange, pair, timeframe, regime, status
        """
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, (configuration_id,))
        result = cursor.fetchone()
        db.commit()
        cursor.close()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Configuration {configuration_id} not found")
        
        log.info(f"Deactivated configuration: {result['strategy_name']} on {result['exchange']} {result['pair']} {result['timeframe']} (lifecycle: {result['status']})")
        
        return {
            "success": True,
            "message": f"Configuration {configuration_id} deactivated",
            "configuration": dict(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deactivating configuration {configuration_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats/summary")
async def get_configurations_summary():
    """Get summary statistics about all configurations"""
    try:
        db = get_database()
        
        query = """
            SELECT 
                COUNT(*) as total_configurations,
                COUNT(*) FILTER (WHERE is_active = true) as active_configurations,
                COUNT(DISTINCT strategy_name) as unique_strategies,
                COUNT(DISTINCT exchange) as unique_exchanges,
                COUNT(DISTINCT pair) as unique_pairs,
                COUNT(*) FILTER (WHERE status = 'DISCOVERY') as discovery_count,
                COUNT(*) FILTER (WHERE status = 'VALIDATION') as validation_count,
                COUNT(*) FILTER (WHERE status = 'MATURE') as mature_count,
                COUNT(*) FILTER (WHERE status = 'DECAY') as decay_count,
                COUNT(*) FILTER (WHERE status = 'PAPER') as paper_count,
                AVG(net_profit) as avg_net_profit,
                AVG(sharpe_ratio) as avg_sharpe_ratio,
                AVG(gross_win_rate) as avg_win_rate
            FROM trained_configurations
        """
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        
        summary = convert_decimals(dict(result))
        
        return summary
        
    except Exception as e:
        log.error(f"Error retrieving configuration summary: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{configuration_id}")
async def delete_configuration(configuration_id: str):
    """
    Permanently delete a trained configuration
    
    This will remove the configuration record from the database.
    Use with caution - this operation cannot be undone.
    """
    try:
        db = get_database()
        
        # First check if the configuration exists
        check_query = """
            SELECT id, strategy_name, exchange, pair, timeframe
            FROM trained_configurations
            WHERE id = %s
        """
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(check_query, (configuration_id,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            raise HTTPException(status_code=404, detail=f"Configuration {configuration_id} not found")
        
        config_info = dict(result)
        
        # Delete the configuration
        delete_query = """
            DELETE FROM trained_configurations
            WHERE id = %s
        """
        
        cursor.execute(delete_query, (configuration_id,))
        db.commit()
        cursor.close()
        
        log.info(f"Deleted configuration: {config_info['strategy_name']} on {config_info['exchange']} {config_info['pair']} {config_info['timeframe']}")
        
        return {
            "success": True,
            "message": f"Configuration {configuration_id} permanently deleted",
            "deleted_configuration": config_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting configuration {configuration_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

