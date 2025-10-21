"""
Exchange Management API endpoints
Handles exchange connections, configuration, and performance monitoring
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2.extras
from decimal import Decimal
from enum import Enum
import ccxt

from database import get_database
from auth_utils import get_current_user
import logging

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])

# Enums
class ExchangeConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"

class PatternStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    PAPER_TRADING = "PAPER_TRADING"

# Pydantic models
class ExchangeConnection(BaseModel):
    id: Optional[int] = None
    nickname: str
    exchangeName: str
    apiKey: str
    apiSecret: str = Field(..., description="API Secret (will be encrypted)")
    testnet: bool = False
    status: ExchangeConnectionStatus = ExchangeConnectionStatus.DISCONNECTED

class ExchangePerformance(BaseModel):
    exchange: str
    status: PatternStatus
    winRate: float
    avgProfit: float
    avgLoss: float
    totalTrades: int
    totalPL: float
    avgSlippage: float  # as percentage
    avgFees: float  # as percentage
    avgLatencyMs: int

class RegimePerformance(BaseModel):
    regime: str
    status: PatternStatus
    exchangePerformance: List[ExchangePerformance]

def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

# Exchange connections table schema would need to be added to migrations
# For now, we'll simulate with in-memory storage
exchange_connections = {}

@router.get("/connections", response_model=List[ExchangeConnection])
async def get_exchange_connections(current_user: dict = Depends(get_current_user)):
    """Get all exchange connections for current user"""
    # In production, this would query the database
    # For now, return sample connections
    sample_connections = [
        ExchangeConnection(
            id=1,
            nickname="Main Binance",
            exchangeName="binanceus",
            apiKey="BNAPI_1234567890ABCDEF",
            apiSecret="***encrypted***",
            testnet=False,
            status=ExchangeConnectionStatus.CONNECTED
        ),
        ExchangeConnection(
            id=2,
            nickname="Coinbase Pro",
            exchangeName="coinbase",
            apiKey="CBAPI_ABCDEF1234567890",
            apiSecret="***encrypted***",
            testnet=False,
            status=ExchangeConnectionStatus.CONNECTED
        ),
        ExchangeConnection(
            id=3,
            nickname="Kraken Test",
            exchangeName="kraken",
            apiKey="KRAPI_TEST1234567890",
            apiSecret="***encrypted***",
            testnet=True,
            status=ExchangeConnectionStatus.ERROR
        )
    ]
    
    return sample_connections

@router.post("/connections", response_model=ExchangeConnection)
async def create_exchange_connection(
    connection: ExchangeConnection,
    current_user: dict = Depends(get_current_user)
):
    """Create a new exchange connection"""
    try:
        # Test the connection
        exchange_class = getattr(ccxt, connection.exchangeName)
        exchange = exchange_class({
            'apiKey': connection.apiKey,
            'secret': connection.apiSecret,
            'sandbox': connection.testnet,
        })
        
        # Try to load markets to test connection
        exchange.load_markets()
        connection.status = ExchangeConnectionStatus.CONNECTED
        
        # In production, encrypt API secret and store in database
        connection.id = len(exchange_connections) + 1
        exchange_connections[connection.id] = connection
        
        log.info(f"Created exchange connection {connection.nickname} for user {current_user['id']}")
        
        return connection
        
    except Exception as e:
        log.error(f"Failed to create exchange connection: {e}")
        connection.status = ExchangeConnectionStatus.ERROR
        raise HTTPException(status_code=400, detail=f"Failed to connect to exchange: {str(e)}")

@router.put("/connections/{connection_id}", response_model=ExchangeConnection)
async def update_exchange_connection(
    connection_id: int,
    connection: ExchangeConnection,
    current_user: dict = Depends(get_current_user)
):
    """Update an exchange connection"""
    if connection_id not in exchange_connections:
        raise HTTPException(status_code=404, detail="Exchange connection not found")
    
    try:
        # Test the updated connection
        exchange_class = getattr(ccxt, connection.exchangeName)
        exchange = exchange_class({
            'apiKey': connection.apiKey,
            'secret': connection.apiSecret,
            'sandbox': connection.testnet,
        })
        
        exchange.load_markets()
        connection.status = ExchangeConnectionStatus.CONNECTED
        connection.id = connection_id
        
        exchange_connections[connection_id] = connection
        
        log.info(f"Updated exchange connection {connection_id} for user {current_user['id']}")
        
        return connection
        
    except Exception as e:
        log.error(f"Failed to update exchange connection: {e}")
        connection.status = ExchangeConnectionStatus.ERROR
        raise HTTPException(status_code=400, detail=f"Failed to connect to exchange: {str(e)}")

@router.delete("/connections/{connection_id}")
async def delete_exchange_connection(
    connection_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete an exchange connection"""
    if connection_id not in exchange_connections:
        raise HTTPException(status_code=404, detail="Exchange connection not found")
    
    del exchange_connections[connection_id]
    
    log.info(f"Deleted exchange connection {connection_id} for user {current_user['id']}")
    
    return {"message": "Exchange connection deleted successfully"}

@router.get("/performance", response_model=List[RegimePerformance])
async def get_exchange_performance(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get exchange performance across different market regimes"""
    try:
        # Generate sample performance data
        # In production, this would query pattern_exchange_performance and pattern_regime_performance tables
        
        sample_performance = [
            RegimePerformance(
                regime="Bull Market",
                status=PatternStatus.ACTIVE,
                exchangePerformance=[
                    ExchangePerformance(
                        exchange="binanceus",
                        status=PatternStatus.ACTIVE,
                        winRate=0.72,
                        avgProfit=145.50,
                        avgLoss=-68.25,
                        totalTrades=89,
                        totalPL=2340.75,
                        avgSlippage=0.08,
                        avgFees=0.12,
                        avgLatencyMs=45
                    ),
                    ExchangePerformance(
                        exchange="coinbase",
                        status=PatternStatus.ACTIVE,
                        winRate=0.68,
                        avgProfit=132.25,
                        avgLoss=-71.50,
                        totalTrades=67,
                        totalPL=1856.30,
                        avgSlippage=0.12,
                        avgFees=0.15,
                        avgLatencyMs=78
                    ),
                    ExchangePerformance(
                        exchange="kraken",
                        status=PatternStatus.PAUSED,
                        winRate=0.61,
                        avgProfit=121.75,
                        avgLoss=-78.90,
                        totalTrades=43,
                        totalPL=892.15,
                        avgSlippage=0.15,
                        avgFees=0.18,
                        avgLatencyMs=120
                    )
                ]
            ),
            RegimePerformance(
                regime="Bear Market",
                status=PatternStatus.ACTIVE,
                exchangePerformance=[
                    ExchangePerformance(
                        exchange="binanceus",
                        status=PatternStatus.ACTIVE,
                        winRate=0.58,
                        avgProfit=98.30,
                        avgLoss=-85.75,
                        totalTrades=76,
                        totalPL=-456.20,
                        avgSlippage=0.18,
                        avgFees=0.12,
                        avgLatencyMs=52
                    ),
                    ExchangePerformance(
                        exchange="coinbase",
                        status=PatternStatus.PAPER_TRADING,
                        winRate=0.55,
                        avgProfit=87.65,
                        avgLoss=-92.40,
                        totalTrades=54,
                        totalPL=-789.45,
                        avgSlippage=0.22,
                        avgFees=0.15,
                        avgLatencyMs=89
                    )
                ]
            ),
            RegimePerformance(
                regime="Sideways",
                status=PatternStatus.ACTIVE,
                exchangePerformance=[
                    ExchangePerformance(
                        exchange="binanceus",
                        status=PatternStatus.ACTIVE,
                        winRate=0.64,
                        avgProfit=76.80,
                        avgLoss=-54.30,
                        totalTrades=128,
                        totalPL=678.90,
                        avgSlippage=0.10,
                        avgFees=0.12,
                        avgLatencyMs=48
                    ),
                    ExchangePerformance(
                        exchange="coinbase",
                        status=PatternStatus.ACTIVE,
                        winRate=0.62,
                        avgProfit=71.25,
                        avgLoss=-58.75,
                        totalTrades=95,
                        totalPL=445.60,
                        avgSlippage=0.14,
                        avgFees=0.15,
                        avgLatencyMs=72
                    )
                ]
            )
        ]
        
        return sample_performance
        
    except Exception as e:
        log.error(f"Error getting exchange performance for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve exchange performance")

@router.get("/supported")
async def get_supported_exchanges():
    """Get list of supported exchanges"""
    supported_exchanges = [
        {"id": "binanceus", "name": "Binance US", "supported": True},
        {"id": "coinbase", "name": "Coinbase Pro", "supported": True},
        {"id": "kraken", "name": "Kraken", "supported": True},
        {"id": "bitstamp", "name": "Bitstamp", "supported": True},
        {"id": "cryptocom", "name": "Crypto.com", "supported": True},
        {"id": "gemini", "name": "Gemini", "supported": True},
        {"id": "uphold", "name": "Uphold", "supported": False},
        {"id": "tradeogre", "name": "TradeOgre", "supported": False}
    ]
    
    return supported_exchanges

@router.post("/test-connection")
async def test_exchange_connection(connection: ExchangeConnection):
    """Test an exchange connection without saving"""
    try:
        exchange_class = getattr(ccxt, connection.exchangeName)
        exchange = exchange_class({
            'apiKey': connection.apiKey,
            'secret': connection.apiSecret,
            'sandbox': connection.testnet,
        })
        
        # Test connection by loading markets
        markets = exchange.load_markets()
        
        return {
            "status": "success",
            "message": f"Successfully connected to {connection.exchangeName}",
            "marketCount": len(markets),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Exchange connection test failed: {e}")
        return {
            "status": "error",
            "message": f"Failed to connect: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }