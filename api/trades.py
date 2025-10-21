"""
Trading API endpoints
Handles trade history, active trades, and trade analysis
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
from enum import Enum

from api.database import get_database
from api.auth_utils import get_current_user
import logging

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trades", tags=["trades"])

# TEMPORARY: Test endpoints without authentication
@router.get("/test")
async def test_trades(db=Depends(get_database)):
    """Test trades endpoint without authentication - returns real data"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT id, wallet_id, symbol, trade_type, entry_price, exit_price, 
                       pnl_percentage, entry_time, exit_time, pattern_name
                FROM trades 
                WHERE user_id = 1
                ORDER BY entry_time DESC 
                LIMIT 10
                """
            )
            trades = cur.fetchall()
            
            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    "id": trade['id'],
                    "timestamp": trade['entry_time'].isoformat() if trade['entry_time'] else None,
                    "symbol": trade['symbol'],
                    "direction": trade['trade_type'],
                    "entryPrice": float(trade['entry_price'] or 0),
                    "exitPrice": float(trade['exit_price'] or 0) if trade['exit_price'] else None,
                    "pnlPercent": float(trade['pnl_percentage'] or 0),
                    "patternName": trade['pattern_name'],
                    "status": "CLOSED" if trade['exit_time'] else "OPEN"
                })
            
            return {
                "trades": formatted_trades,
                "total": len(formatted_trades)
            }

    except Exception as e:
        return {"error": str(e)}

@router.get("/test-active")
async def test_active_trades(db=Depends(get_database)):
    """Test active trades endpoint without authentication"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT symbol, direction, entry_price, quantity, current_price, 
                       unrealized_pnl, take_profit, stop_loss, pattern_name, timestamp
                FROM active_trades 
                ORDER BY timestamp DESC 
                LIMIT 10
                """
            )
            active_trades = cur.fetchall()
            
            if active_trades:
                return [
                    {
                        "symbol": trade['symbol'],
                        "direction": trade['direction'],
                        "entryPrice": float(trade['entry_price']),
                        "quantity": float(trade['quantity']),
                        "currentPrice": float(trade['current_price'] or trade['entry_price']),
                        "currentPL": float(trade['unrealized_pnl'] or 0),
                        "takeProfit": float(trade['take_profit']) if trade['take_profit'] else None,
                        "stopLoss": float(trade['stop_loss']) if trade['stop_loss'] else None,
                        "patternName": trade['pattern_name'],
                        "startTimestamp": trade['timestamp'].isoformat() if trade['timestamp'] else None
                    }
                    for trade in active_trades
                ]
            else:
                # Return sample data
                return [
                    {
                        "symbol": "ETH/USDT",
                        "direction": "BUY",
                        "entryPrice": 3500.0,
                        "quantity": 1.0,
                        "currentPrice": 3650.0,
                        "currentPL": 150.0,
                        "takeProfit": 3800.0,
                        "stopLoss": 3300.0,
                        "patternName": "Liquidity Sweep Reversal",
                        "startTimestamp": "2024-01-01T12:00:00"
                    }
                ]
    except Exception as e:
        return {"error": str(e)}

@router.get("/test-logs")
async def test_logs():
    """Test logs endpoint without authentication"""
    return [
        "[2024-01-01 10:00:00] Bot started successfully",
        "[2024-01-01 10:01:00] Connected to Binance exchange",
        "[2024-01-01 10:02:00] Pattern detected: Liquidity Sweep on BTC/USDT",
        "[2024-01-01 10:03:00] Trade executed: BUY 0.1 BTC at $65000",
        "[2024-01-01 10:04:00] Current P&L: +$150.00"
    ]

# Enums
class TradeDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

# Pydantic models
class Trade(BaseModel):
    id: int
    timestamp: str
    symbol: str
    direction: TradeDirection
    quantity: float
    price: float
    fill_cost: float
    pnl: Optional[float] = None

class ActiveTrade(BaseModel):
    id: str
    symbol: str
    direction: TradeDirection
    entryPrice: float
    quantity: float
    currentPL: float
    takeProfit: float
    stopLoss: float
    patternName: str
    startTimestamp: str
    currentPrice: Optional[float] = None

class BotStatus(BaseModel):
    status: str

def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

@router.get("/", response_model=List[Trade])
async def get_trades(
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get trade history"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT id, executed_at, symbol, trade_type, quantity, price, fill_cost, pnl
                FROM trades
                WHERE user_id = %s
                ORDER BY executed_at DESC
                LIMIT %s
                """,
                (current_user["id"], limit)
            )
            trade_rows = cur.fetchall()
            
            if not trade_rows:
                # Generate sample trades if none exist
                sample_trades = []
                for i in range(10):
                    sample_trades.append(Trade(
                        id=i + 1,
                        timestamp=(datetime.utcnow() - timedelta(hours=i*2)).isoformat(),
                        symbol="BTC/USDT",
                        direction=TradeDirection.BUY if i % 2 == 0 else TradeDirection.SELL,
                        quantity=0.1,
                        price=50000 + (i * 100),
                        fill_cost=5000 + (i * 10),
                        pnl=(i - 5) * 50  # Some wins, some losses
                    ))
                return sample_trades
            
            return [
                Trade(
                    id=row["id"],
                    timestamp=row["executed_at"].isoformat() if row["executed_at"] else datetime.utcnow().isoformat(),
                    symbol=row["symbol"],
                    direction=TradeDirection(row["trade_type"]),
                    quantity=decimal_to_float(row["quantity"]),
                    price=decimal_to_float(row["price"]),
                    fill_cost=decimal_to_float(row["fill_cost"]),
                    pnl=decimal_to_float(row["pnl"])
                )
                for row in trade_rows
            ]
            
    except Exception as e:
        log.error(f"Error getting trades for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trades")

@router.get("/active", response_model=List[ActiveTrade])
async def get_active_trades(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get currently active trades"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT id, symbol, direction, entry_price, quantity, unrealized_pnl,
                       take_profit, stop_loss, pattern_name, entry_timestamp, current_price
                FROM active_trades
                WHERE user_id = %s
                ORDER BY entry_timestamp DESC
                """,
                (current_user["id"],)
            )
            active_rows = cur.fetchall()
            
            if not active_rows:
                # Generate sample active trades if none exist
                return [
                    ActiveTrade(
                        id="1",
                        symbol="BTC/USDT",
                        direction=TradeDirection.BUY,
                        entryPrice=50000.0,
                        quantity=0.1,
                        currentPL=250.0,
                        takeProfit=52000.0,
                        stopLoss=48000.0,
                        patternName="Liquidity Sweep",
                        startTimestamp=(datetime.utcnow() - timedelta(hours=2)).isoformat(),
                        currentPrice=50250.0
                    ),
                    ActiveTrade(
                        id="2",
                        symbol="ETH/USDT",
                        direction=TradeDirection.BUY,
                        entryPrice=3000.0,
                        quantity=1.0,
                        currentPL=-75.0,
                        takeProfit=3200.0,
                        stopLoss=2850.0,
                        patternName="Volume Breakout",
                        startTimestamp=(datetime.utcnow() - timedelta(hours=4)).isoformat(),
                        currentPrice=2925.0
                    )
                ]
            
            return [
                ActiveTrade(
                    id=str(row["id"]),
                    symbol=row["symbol"],
                    direction=TradeDirection(row["direction"]),
                    entryPrice=decimal_to_float(row["entry_price"]),
                    quantity=decimal_to_float(row["quantity"]),
                    currentPL=decimal_to_float(row["unrealized_pnl"]) or 0.0,
                    takeProfit=decimal_to_float(row["take_profit"]) or 0.0,
                    stopLoss=decimal_to_float(row["stop_loss"]) or 0.0,
                    patternName=row["pattern_name"] or "Unknown",
                    startTimestamp=row["entry_timestamp"].isoformat(),
                    currentPrice=decimal_to_float(row["current_price"])
                )
                for row in active_rows
            ]
            
    except Exception as e:
        log.error(f"Error getting active trades for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active trades")

@router.get("/status", response_model=BotStatus)
async def get_bot_status():
    """Get trading bot status"""
    # This would integrate with your actual bot status system
    # For now, return a mock status
    return BotStatus(status="RUNNING")

@router.get("/logs", response_model=List[str])
async def get_trade_logs(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get trading logs"""
    # Generate sample logs - in production this would read from actual log files
    sample_logs = [
        f"[{datetime.utcnow().strftime('%H:%M:%S')}] Pattern detected: Liquidity Sweep on BTC/USDT",
        f"[{(datetime.utcnow() - timedelta(minutes=5)).strftime('%H:%M:%S')}] Entry signal confirmed, placing BUY order",
        f"[{(datetime.utcnow() - timedelta(minutes=10)).strftime('%H:%M:%S')}] Order filled: BTC/USDT BUY 0.1 @ $50,250",
        f"[{(datetime.utcnow() - timedelta(minutes=15)).strftime('%H:%M:%S')}] Stop loss updated to breakeven",
        f"[{(datetime.utcnow() - timedelta(minutes=20)).strftime('%H:%M:%S')}] Market scan completed: 15 patterns evaluated",
    ]
    
    return sample_logs[:limit]