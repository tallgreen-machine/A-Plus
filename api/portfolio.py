"""
Portfolio API endpoints
Handles portfolio data, holdings, equity history, and performance metrics
Enhanced with system integration for risk management and OCO orders
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
from enum import Enum

# Add project root to path for system integration
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Configure logging
import logging
log = logging.getLogger(__name__)

# Try to import auth and database utils
try:
    from api.database import get_database
    from api.auth_utils import get_current_user
    auth_available = True
except Exception as e:
    auth_available = False
    log.warning(f"Auth/Database utils not available: {e}")
    # Create dummy functions for now
    def get_current_user():
        return {"id": 1, "username": "admin"}
    def get_database():
        return None

# Import system components for enhanced functionality
try:
    from core.execution_core import ExecutionCore
    from core.event_system import EventBus
    from core.data_handler import DataHandler
    from ml.trained_assets_manager import TrainedAssetsManager
    
    # Initialize system components with default config
    event_bus = EventBus()
    # Initialize data handler with default symbols and timeframes
    default_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    default_timeframes = ['1m', '5m', '15m', '1h', '4h']
    data_handler = DataHandler(event_bus, default_symbols, default_timeframes)
    execution_core = ExecutionCore(event_bus, data_handler)
    trained_assets_manager = TrainedAssetsManager()
    
    system_available = True
    log.info("Portfolio API: Enhanced system components initialized")
    
except Exception as e:
    system_available = False
    execution_core = None
    trained_assets_manager = None
    log.warning(f"Portfolio API: System components not available: {e}")

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Enhanced API endpoints for system integration

@router.get("/summary")
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    """Get comprehensive portfolio summary with risk metrics and OCO status"""
    try:
        if not system_available or not execution_core:
            raise HTTPException(status_code=503, detail="Enhanced portfolio system unavailable")
        
        summary = execution_core.get_portfolio_summary()
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        log.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk-management")
async def get_risk_management(current_user: dict = Depends(get_current_user)):
    """Get current risk management status for all wallets"""
    try:
        if not system_available or not execution_core:
            raise HTTPException(status_code=503, detail="Risk management system unavailable")
        
        portfolio_summary = execution_core.get_portfolio_summary()
        
        risk_data = {
            'total_wallets': portfolio_summary.get('total_wallets', 0),
            'total_equity': portfolio_summary.get('total_equity', 0.0),
            'total_risk': portfolio_summary.get('total_risk', 0.0),
            'oco_summary': portfolio_summary.get('oco_summary', {}),
            'wallets': {}
        }
        
        # Enhanced wallet-specific risk metrics
        for wallet_id, wallet_data in portfolio_summary.get('wallets', {}).items():
            risk_data['wallets'][wallet_id] = {
                'equity': wallet_data.get('equity', 0.0),
                'drawdown_percent': wallet_data.get('drawdown_percent', 0.0),
                'portfolio_risk_percent': wallet_data.get('portfolio_risk_percent', 0.0),
                'open_positions': wallet_data.get('open_positions', 0),
                'trading_allowed': wallet_data.get('trading_allowed', False),
                'risk_status': 'Healthy' if wallet_data.get('drawdown_percent', 0) < 10 else 
                             'Warning' if wallet_data.get('drawdown_percent', 0) < 20 else 'Critical'
            }
        
        return {
            "status": "success",
            "data": risk_data
        }
    except Exception as e:
        log.error(f"Error getting risk management data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/oco-orders")
async def get_oco_orders(current_user: dict = Depends(get_current_user)):
    """Get active OCO orders across all wallets"""
    try:
        if not system_available or not execution_core:
            raise HTTPException(status_code=503, detail="OCO system unavailable")
        
        active_oco_orders = execution_core.get_active_oco_orders()
        
        oco_data = []
        for oco_pair in active_oco_orders:
            oco_data.append({
                'id': oco_pair.id,
                'symbol': oco_pair.symbol,
                'wallet_id': oco_pair.wallet_id,
                'exchange': oco_pair.exchange,
                'status': oco_pair.status.value,
                'stop_loss_price': oco_pair.stop_loss_price,
                'take_profit_price': oco_pair.take_profit_price,
                'quantity': oco_pair.quantity,
                'native_oco_supported': oco_pair.native_oco_supported,
                'created_at': oco_pair.created_at,
                'linked_orders': len(oco_pair.linked_orders)
            })
        
        return {
            "status": "success",
            "data": {
                'active_oco_orders': oco_data,
                'total_active': len(oco_data)
            }
        }
    except Exception as e:
        log.error(f"Error getting OCO orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TEMPORARY: Test endpoint without authentication
@router.get("/test")
async def test_portfolio(db=Depends(get_database)):
    """Test portfolio endpoint without authentication - returns real data"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Get latest portfolio snapshot for user 1 (admin)
            cur.execute(
                """
                SELECT timestamp, total_equity, cash_balance, market_value, unrealized_pnl, realized_pnl, total_pnl
                FROM portfolio_snapshots 
                WHERE user_id = 1
                ORDER BY timestamp DESC 
                LIMIT 1
                """
            )
            portfolio_row = cur.fetchone()
            
            # Get holdings for user 1
            cur.execute(
                """
                SELECT symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl, unrealized_pnl_percent
                FROM holdings 
                WHERE user_id = 1 AND quantity > 0
                ORDER BY market_value DESC
                """
            )
            holdings_rows = cur.fetchall()
            
            if portfolio_row:
                holdings = []
                for holding in holdings_rows:
                    holdings.append({
                        "symbol": holding['symbol'],
                        "quantity": float(holding['quantity'] or 0),
                        "avgCost": float(holding['avg_cost'] or 0),
                        "currentPrice": float(holding['current_price'] or 0),
                        "marketValue": float(holding['market_value'] or 0),
                        "unrealizedPL": float(holding['unrealized_pnl'] or 0),
                        "unrealizedPLPercent": float(holding['unrealized_pnl_percent'] or 0)
                    })
                
                return {
                    "portfolio": {
                        "timestamp": portfolio_row['timestamp'].isoformat() if portfolio_row['timestamp'] else datetime.now().isoformat(),
                        "equity": float(portfolio_row['total_equity'] or 0),
                        "cash": float(portfolio_row['cash_balance'] or 0),
                        "marketValue": float(portfolio_row['market_value'] or 0),
                        "unrealizedPL": float(portfolio_row['unrealized_pnl'] or 0),
                        "realizedPL": float(portfolio_row['realized_pnl'] or 0),
                        "totalPL": float(portfolio_row['total_pnl'] or 0)
                    },
                    "holdings": holdings
                }
            else:
                return {
                    "portfolio": {
                        "timestamp": "2024-01-01T00:00:00",
                        "equity": 100000.0,
                        "cash": 25000.0
                    },
                    "holdings": []
                }
    except Exception as e:
        return {"error": str(e)}

# Pydantic models
class Portfolio(BaseModel):
    timestamp: str
    equity: float
    cash: float

class PortfolioResponse(BaseModel):
    portfolio: Portfolio
    holdings: List[dict]

class Holding(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percent: Optional[float] = None

class EquityPoint(BaseModel):
    timestamp: str
    equity: float

class PerformanceMetrics(BaseModel):
    totalPL: dict  # {value: float, percentage: float}
    sharpeRatio: float
    maxDrawdown: float
    winLossRatio: float
    avgProfit: float
    avgLoss: float
    totalTrades: int

def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

@router.get("/", response_model=PortfolioResponse)
async def get_portfolio(current_user: dict = Depends(get_current_user), db=Depends(get_database)):
    """Get current portfolio snapshot with holdings"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Get latest portfolio snapshot
            cur.execute(
                """
                SELECT timestamp, total_equity, cash_balance, market_value, unrealized_pnl, realized_pnl
                FROM portfolio_snapshots 
                WHERE user_id = %s 
                ORDER BY timestamp DESC 
                LIMIT 1
                """,
                (current_user["id"],)
            )
            portfolio_row = cur.fetchone()
            
            if not portfolio_row:
                # Create default portfolio if none exists
                portfolio = Portfolio(
                    timestamp=datetime.utcnow().isoformat(),
                    equity=10000.0,  # Default starting equity
                    cash=10000.0
                )
                holdings = []
            else:
                portfolio = Portfolio(
                    timestamp=portfolio_row["timestamp"].isoformat(),
                    equity=decimal_to_float(portfolio_row["total_equity"]),
                    cash=decimal_to_float(portfolio_row["cash_balance"])
                )
                
                # Get current holdings
                cur.execute(
                    """
                    SELECT symbol, quantity, avg_cost, current_price, market_value, 
                           unrealized_pnl, unrealized_pnl_percent
                    FROM holdings 
                    WHERE user_id = %s AND quantity > 0
                    ORDER BY market_value DESC
                    """,
                    (current_user["id"],)
                )
                holdings_rows = cur.fetchall()
                holdings = [
                    {
                        "symbol": row["symbol"],
                        "quantity": decimal_to_float(row["quantity"]),
                        "avg_cost": decimal_to_float(row["avg_cost"]),
                        "current_price": decimal_to_float(row["current_price"]),
                        "market_value": decimal_to_float(row["market_value"]),
                        "unrealized_pnl": decimal_to_float(row["unrealized_pnl"]),
                        "unrealized_pnl_percent": decimal_to_float(row["unrealized_pnl_percent"])
                    }
                    for row in holdings_rows
                ]
            
            return PortfolioResponse(portfolio=portfolio, holdings=holdings)
            
    except Exception as e:
        log.error(f"Error getting portfolio for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolio")

@router.get("/history", response_model=List[EquityPoint])
async def get_portfolio_history(
    days: int = 30,
    current_user: dict = Depends(get_current_user), 
    db=Depends(get_database)
):
    """Get portfolio equity history for charting"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            start_date = datetime.utcnow() - timedelta(days=days)
            cur.execute(
                """
                SELECT timestamp, equity
                FROM equity_history
                WHERE user_id = %s AND timestamp >= %s
                ORDER BY timestamp ASC
                """,
                (current_user["id"], start_date)
            )
            history_rows = cur.fetchall()
            
            if not history_rows:
                # Generate sample data if none exists
                base_equity = 10000.0
                sample_data = []
                for i in range(30):
                    date = datetime.utcnow() - timedelta(days=29-i)
                    # Add some realistic variation
                    equity = base_equity + (i * 50) + ((i % 7) * 100)
                    sample_data.append(EquityPoint(
                        timestamp=date.isoformat(),
                        equity=equity
                    ))
                return sample_data
            
            return [
                EquityPoint(
                    timestamp=row["timestamp"].isoformat(),
                    equity=decimal_to_float(row["equity"])
                )
                for row in history_rows
            ]
            
    except Exception as e:
        log.error(f"Error getting portfolio history for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolio history")

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get portfolio performance metrics"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Get latest performance metrics
            start_date = datetime.utcnow() - timedelta(days=days)
            cur.execute(
                """
                SELECT total_return, total_return_percent, sharpe_ratio, max_drawdown,
                       win_rate, avg_win, avg_loss, total_trades, winning_trades, losing_trades
                FROM performance_metrics
                WHERE user_id = %s AND period_start >= %s
                ORDER BY calculated_at DESC
                LIMIT 1
                """,
                (current_user["id"], start_date)
            )
            perf_row = cur.fetchone()
            
            if not perf_row:
                # Return default metrics if none calculated yet
                return PerformanceMetrics(
                    totalPL={"value": 0.0, "percentage": 0.0},
                    sharpeRatio=0.0,
                    maxDrawdown=0.0,
                    winLossRatio=0.0,
                    avgProfit=0.0,
                    avgLoss=0.0,
                    totalTrades=0
                )
            
            # Calculate win/loss ratio
            win_loss_ratio = 0.0
            if perf_row["losing_trades"] and perf_row["losing_trades"] > 0:
                win_loss_ratio = decimal_to_float(perf_row["winning_trades"]) / decimal_to_float(perf_row["losing_trades"])
            
            return PerformanceMetrics(
                totalPL={
                    "value": decimal_to_float(perf_row["total_return"]) or 0.0,
                    "percentage": decimal_to_float(perf_row["total_return_percent"]) or 0.0
                },
                sharpeRatio=decimal_to_float(perf_row["sharpe_ratio"]) or 0.0,
                maxDrawdown=decimal_to_float(perf_row["max_drawdown"]) or 0.0,
                winLossRatio=win_loss_ratio,
                avgProfit=decimal_to_float(perf_row["avg_win"]) or 0.0,
                avgLoss=decimal_to_float(perf_row["avg_loss"]) or 0.0,
                totalTrades=perf_row["total_trades"] or 0
            )
            
    except Exception as e:
        log.error(f"Error getting performance metrics for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")