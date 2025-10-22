"""
Exchange Management API endpoints
Enhanced with multi-exchange support and performance tracking
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
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

# Import enhanced exchange system
try:
    import ccxt
    from core.execution_core import ExecutionCore
    
    # Initialize system components
    execution_core = ExecutionCore()
    exchange_system_available = True
    log.info("Exchanges API: Enhanced system initialized")
    
except Exception as e:
    exchange_system_available = False
    execution_core = None
    log.warning(f"Exchanges API: Enhanced system not available: {e}")

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])

# Enhanced API endpoints

@router.get("/connections")
async def get_exchange_connections():
    """Get all configured exchange connections with status"""
    try:
        # Return sample exchange connections
        connections = [
            {
                "id": 1,
                "nickname": "Binance Main",
                "exchangeName": "binance",
                "status": "CONNECTED",
                "testnet": False,
                "lastPing": "2024-01-01T10:00:00Z",
                "latency": 45,
                "apiPermissions": ["spot", "futures"],
                "rateLimits": {
                    "orders": {"current": 5, "max": 100, "window": "1m"},
                    "requests": {"current": 12, "max": 1200, "window": "1m"}
                },
                "balanceUSD": 15000.0,
                "openOrders": 3
            },
            {
                "id": 2,
                "nickname": "Binance Testnet",
                "exchangeName": "binance",
                "status": "CONNECTED",
                "testnet": True,
                "lastPing": "2024-01-01T10:00:00Z",
                "latency": 52,
                "apiPermissions": ["spot"],
                "rateLimits": {
                    "orders": {"current": 2, "max": 100, "window": "1m"},
                    "requests": {"current": 8, "max": 1200, "window": "1m"}
                },
                "balanceUSD": 1000.0,
                "openOrders": 1
            },
            {
                "id": 3,
                "nickname": "Bybit Main",
                "exchangeName": "bybit",
                "status": "DISCONNECTED",
                "testnet": False,
                "lastPing": None,
                "latency": None,
                "apiPermissions": [],
                "rateLimits": {},
                "balanceUSD": 0.0,
                "openOrders": 0
            }
        ]
        
        return {
            "status": "success",
            "data": connections
        }
        
    except Exception as e:
        log.error(f"Error getting exchange connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-connection")
async def test_exchange_connection(connection_data: dict):
    """Test connection to an exchange with provided credentials"""
    try:
        exchange_name = connection_data.get("exchangeName")
        api_key = connection_data.get("apiKey")
        api_secret = connection_data.get("apiSecret")
        testnet = connection_data.get("testnet", False)
        
        if not exchange_system_available:
            # Return mock test result
            return {
                "status": "success" if api_key and api_secret else "error",
                "message": "Connection test completed (simulated)",
                "data": {
                    "exchangeName": exchange_name,
                    "connected": bool(api_key and api_secret),
                    "latency": 45 if api_key and api_secret else None,
                    "permissions": ["spot", "futures"] if api_key and api_secret else [],
                    "balance": {"USDT": 1000.0} if api_key and api_secret else {}
                }
            }
        
        # Test actual connection (would need real implementation)
        if not api_key or not api_secret:
            raise HTTPException(status_code=400, detail="API key and secret required")
        
        try:
            # Initialize exchange (this would be the real implementation)
            exchange_class = getattr(ccxt, exchange_name, None)
            if not exchange_class:
                raise HTTPException(status_code=400, detail=f"Exchange {exchange_name} not supported")
            
            exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': testnet,
                'enableRateLimit': True,
            })
            
            # Test connection
            start_time = datetime.now()
            balance = exchange.fetch_balance()
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": "success",
                "message": "Connection successful",
                "data": {
                    "exchangeName": exchange_name,
                    "connected": True,
                    "latency": round(latency, 2),
                    "permissions": ["spot"],  # Would check actual permissions
                    "balance": {k: v for k, v in balance['total'].items() if v > 0}
                }
            }
            
        except Exception as conn_error:
            return {
                "status": "error",
                "message": f"Connection failed: {str(conn_error)}",
                "data": {
                    "exchangeName": exchange_name,
                    "connected": False,
                    "latency": None,
                    "permissions": [],
                    "balance": {}
                }
            }
        
    except Exception as e:
        log.error(f"Error testing exchange connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_exchange_performance():
    """Get performance metrics for each exchange"""
    try:
        performance_data = [
            {
                "exchange": "binance",
                "nickname": "Binance Main",
                "status": "ACTIVE",
                "winRate": 68.5,
                "avgProfit": 125.30,
                "avgLoss": -65.20,
                "totalTrades": 45,
                "totalPL": 2500.0,
                "sharpeRatio": 1.85,
                "maxDrawdown": 8.5,
                "latency": {
                    "average": 45,
                    "p95": 85,
                    "p99": 150
                },
                "uptime": 99.2,
                "lastTrade": "2024-01-01T09:45:00Z"
            },
            {
                "exchange": "bybit",
                "nickname": "Bybit Main",
                "status": "PAUSED",
                "winRate": 62.3,
                "avgProfit": 98.75,
                "avgLoss": -58.30,
                "totalTrades": 32,
                "totalPL": 1200.0,
                "sharpeRatio": 1.65,
                "maxDrawdown": 12.1,
                "latency": {
                    "average": 62,
                    "p95": 120,
                    "p99": 200
                },
                "uptime": 97.8,
                "lastTrade": "2024-01-01T08:30:00Z"
            }
        ]
        
        return {
            "status": "success",
            "data": performance_data
        }
        
    except Exception as e:
        log.error(f"Error getting exchange performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-exchanges")
async def get_supported_exchanges():
    """Get list of supported exchanges and their features"""
    try:
        supported_exchanges = [
            {
                "id": "binance",
                "name": "Binance",
                "features": ["spot", "futures", "margin"],
                "supported": True,
                "testnet": True,
                "rateLimits": {
                    "orders": "100/min",
                    "requests": "1200/min"
                },
                "fees": {
                    "maker": 0.001,
                    "taker": 0.001
                },
                "regions": ["global"]
            },
            {
                "id": "bybit",
                "name": "Bybit", 
                "features": ["spot", "futures"],
                "supported": True,
                "testnet": True,
                "rateLimits": {
                    "orders": "50/min",
                    "requests": "600/min"
                },
                "fees": {
                    "maker": 0.001,
                    "taker": 0.001
                },
                "regions": ["global"]
            },
            {
                "id": "okx",
                "name": "OKX",
                "features": ["spot", "futures"],
                "supported": False,
                "testnet": True,
                "rateLimits": {
                    "orders": "60/min",
                    "requests": "300/min"
                },
                "fees": {
                    "maker": 0.0008,
                    "taker": 0.001
                },
                "regions": ["global"]
            }
        ]
        
        return {
            "status": "success",
            "data": {
                "exchanges": supported_exchanges,
                "total": len(supported_exchanges),
                "supported": len([ex for ex in supported_exchanges if ex["supported"]])
            }
        }
        
    except Exception as e:
        log.error(f"Error getting supported exchanges: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enums
class ExchangeConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"

class StrategyStatus(str, Enum):
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
    status: StrategyStatus
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
    status: StrategyStatus
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
                status=StrategyStatus.ACTIVE,
                exchangePerformance=[
                    ExchangePerformance(
                        exchange="binanceus",
                        status=StrategyStatus.ACTIVE,
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
                        status=StrategyStatus.ACTIVE,
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
                        status=StrategyStatus.PAUSED,
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
                status=StrategyStatus.ACTIVE,
                exchangePerformance=[
                    ExchangePerformance(
                        exchange="binanceus",
                        status=StrategyStatus.ACTIVE,
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
                        status=StrategyStatus.PAPER_TRADING,
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
                status=StrategyStatus.ACTIVE,
                exchangePerformance=[
                    ExchangePerformance(
                        exchange="binanceus",
                        status=StrategyStatus.ACTIVE,
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
                        status=StrategyStatus.ACTIVE,
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