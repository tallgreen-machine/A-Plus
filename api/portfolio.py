"""
Portfolio API endpoints
Handles portfolio data, holdings, equity history, and performance metrics
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
import logging

from api.database import get_database
from api.auth_utils import get_current_user

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# TEMPORARY: Test endpoint without authentication
@router.get("/test")
async def test_portfolio(db=Depends(get_database)):
    """Test portfolio endpoint without authentication"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Get latest portfolio snapshot for any user (test)
            cur.execute(
                """
                SELECT timestamp, total_equity, cash_balance, market_value, unrealized_pnl, realized_pnl
                FROM portfolio_snapshots 
                ORDER BY timestamp DESC 
                LIMIT 1
                """
            )
            portfolio_row = cur.fetchone()
            
            if portfolio_row:
                return {
                    "portfolio": {
                        "timestamp": portfolio_row['timestamp'].isoformat() if portfolio_row['timestamp'] else None,
                        "equity": float(portfolio_row['total_equity'] or 0),
                        "cash": float(portfolio_row['cash_balance'] or 0)
                    },
                    "holdings": []
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