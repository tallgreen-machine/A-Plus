#!/usr/bin/env python3
"""
Exchange Data Collector
Real-time and historical data collection from major crypto exchanges
Replaces the synthetic data seeding with actual market data
"""

import os
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2
import psycopg2.extras
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class CandleData:
    timestamp: int
    symbol: str
    exchange: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class ExchangeDataCollector:
    """Base class for exchange data collection"""
    
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.session = None
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = 0
        
    async def __aenter__(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    async def get_historical_data(self, symbol: str, interval: str = '1h', limit: int = 1000) -> List[CandleData]:
        """Get historical OHLCV data - implemented by subclasses"""
        raise NotImplementedError
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol - implemented by subclasses"""
        raise NotImplementedError

class BinanceCollector(ExchangeDataCollector):
    """Binance data collector using public API"""
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        super().__init__("binance")
        self.rate_limit_delay = 0.1  # Binance allows 1200 requests/min
    
    def _convert_symbol(self, symbol: str) -> str:
        """Convert symbol format (BTC/USDT -> BTCUSDT)"""
        return symbol.replace('/', '')
    
    async def get_historical_data(self, symbol: str, interval: str = '1h', limit: int = 1000) -> List[CandleData]:
        """Get historical klines data from Binance"""
        await self._rate_limit()
        
        binance_symbol = self._convert_symbol(symbol)
        url = f"{self.BASE_URL}/klines"
        
        params = {
            'symbol': binance_symbol,
            'interval': interval,
            'limit': min(limit, 1000)  # Binance max is 1000
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    candles = []
                    
                    for kline in data:
                        candles.append(CandleData(
                            timestamp=int(kline[0] // 1000),  # Convert ms to seconds
                            symbol=symbol,
                            exchange=self.exchange_name,
                            open=float(kline[1]),
                            high=float(kline[2]),
                            low=float(kline[3]),
                            close=float(kline[4]),
                            volume=float(kline[5])
                        ))
                    
                    log.info(f"✅ Fetched {len(candles)} candles for {symbol} from Binance")
                    return candles
                else:
                    log.error(f"❌ Binance API error {response.status} for {symbol}")
                    return []
                    
        except Exception as e:
            log.error(f"❌ Error fetching Binance data for {symbol}: {e}")
            return []
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current ticker price"""
        await self._rate_limit()
        
        binance_symbol = self._convert_symbol(symbol)
        url = f"{self.BASE_URL}/ticker/price"
        
        try:
            async with self.session.get(url, params={'symbol': binance_symbol}) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
                else:
                    log.error(f"❌ Binance price API error {response.status} for {symbol}")
                    return 0.0
        except Exception as e:
            log.error(f"❌ Error fetching Binance price for {symbol}: {e}")
            return 0.0

class CoinGeckoCollector(ExchangeDataCollector):
    """CoinGecko data collector (free tier, reliable)"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        super().__init__("coingecko")
        self.rate_limit_delay = 1.2  # CoinGecko free tier: 50 calls/minute
        
        # Symbol mapping for CoinGecko
        self.symbol_map = {
            'BTC/USDT': 'bitcoin',
            'ETH/USDT': 'ethereum',
            'SOL/USDT': 'solana',
            'ADA/USDT': 'cardano',
            'DOT/USDT': 'polkadot'
        }
    
    async def get_historical_data(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[CandleData]:
        """Get historical data from CoinGecko"""
        await self._rate_limit()
        
        if symbol not in self.symbol_map:
            log.error(f"❌ Symbol {symbol} not supported by CoinGecko collector")
            return []
        
        coin_id = self.symbol_map[symbol]
        
        # CoinGecko only supports daily data for free tier
        days = min(limit // 24 if interval == '1h' else limit, 90)  # Max 90 days free
        
        url = f"{self.BASE_URL}/coins/{coin_id}/ohlc"
        params = {
            'vs_currency': 'usd',
            'days': days
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    candles = []
                    
                    for ohlc in data:
                        timestamp = int(ohlc[0] // 1000)  # Convert ms to seconds
                        candles.append(CandleData(
                            timestamp=timestamp,
                            symbol=symbol,
                            exchange=self.exchange_name,
                            open=float(ohlc[1]),
                            high=float(ohlc[2]),
                            low=float(ohlc[3]),
                            close=float(ohlc[4]),
                            volume=1000000.0  # CoinGecko doesn't provide volume in OHLC
                        ))
                    
                    log.info(f"✅ Fetched {len(candles)} daily candles for {symbol} from CoinGecko")
                    return candles
                else:
                    log.error(f"❌ CoinGecko API error {response.status} for {symbol}")
                    return []
                    
        except Exception as e:
            log.error(f"❌ Error fetching CoinGecko data for {symbol}: {e}")
            return []
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price from CoinGecko"""
        await self._rate_limit()
        
        if symbol not in self.symbol_map:
            return 0.0
        
        coin_id = self.symbol_map[symbol]
        url = f"{self.BASE_URL}/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data[coin_id]['usd'])
                else:
                    log.error(f"❌ CoinGecko price API error {response.status} for {symbol}")
                    return 0.0
        except Exception as e:
            log.error(f"❌ Error fetching CoinGecko price for {symbol}: {e}")
            return 0.0

class CoinbaseCollector(ExchangeDataCollector):
    """Coinbase Pro data collector"""
    
    BASE_URL = "https://api.exchange.coinbase.com"
    
    def __init__(self):
        super().__init__("coinbase")
        self.rate_limit_delay = 0.1  # Coinbase allows 10 requests/second
    
    def _convert_symbol(self, symbol: str) -> str:
        """Convert symbol format (BTC/USDT -> BTC-USD)"""
        return symbol.replace('USDT', 'USD').replace('/', '-')
    
    async def get_historical_data(self, symbol: str, interval: str = '1h', limit: int = 300) -> List[CandleData]:
        """Get historical candles from Coinbase"""
        await self._rate_limit()
        
        coinbase_symbol = self._convert_symbol(symbol)
        
        # Calculate start/end times
        end_time = datetime.utcnow()
        hours = limit if interval == '1h' else limit * 24
        start_time = end_time - timedelta(hours=hours)
        
        url = f"{self.BASE_URL}/products/{coinbase_symbol}/candles"
        params = {
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'granularity': 3600 if interval == '1h' else 86400  # 1h or 1d in seconds
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    candles = []
                    
                    for candle in data:
                        candles.append(CandleData(
                            timestamp=int(candle[0]),  # Already in seconds
                            symbol=symbol,
                            exchange=self.exchange_name,
                            open=float(candle[3]),
                            high=float(candle[2]),
                            low=float(candle[1]),
                            close=float(candle[4]),
                            volume=float(candle[5])
                        ))
                    
                    # Sort by timestamp (Coinbase returns descending)
                    candles.sort(key=lambda x: x.timestamp)
                    
                    log.info(f"✅ Fetched {len(candles)} candles for {symbol} from Coinbase")
                    return candles
                else:
                    log.error(f"❌ Coinbase API error {response.status} for {symbol}")
                    return []
                    
        except Exception as e:
            log.error(f"❌ Error fetching Coinbase data for {symbol}: {e}")
            return []
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current ticker price"""
        await self._rate_limit()
        
        coinbase_symbol = self._convert_symbol(symbol)
        url = f"{self.BASE_URL}/products/{coinbase_symbol}/ticker"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
                else:
                    log.error(f"❌ Coinbase price API error {response.status} for {symbol}")
                    return 0.0
        except Exception as e:
            log.error(f"❌ Error fetching Coinbase price for {symbol}: {e}")
            return 0.0

class MarketDataManager:
    """Manages market data collection and storage"""
    
    def __init__(self):
        self.collectors = {
            'binance': BinanceCollector(),
            'coinbase': CoinbaseCollector(),
            'coingecko': CoinGeckoCollector()
        }
        self.db_conn = None
    
    def get_db_connection(self):
        """Get database connection"""
        if not self.db_conn:
            self.db_conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                dbname=os.getenv("DB_NAME", "trad"),
                user=os.getenv("DB_USER", "traduser"),
                password=os.getenv("DB_PASSWORD", "TRAD123!")
            )
        return self.db_conn
    
    async def collect_historical_data(self, symbols: List[str], exchanges: List[str] = None):
        """Collect historical data for symbols from specified exchanges"""
        if exchanges is None:
            exchanges = ['binance']  # Default to Binance
        
        log.info(f"🚀 Starting historical data collection for {symbols} from {exchanges}")
        
        conn = self.get_db_connection()
        
        try:
            with conn.cursor() as cur:
                # Clear existing data
                log.info("🧹 Clearing existing market data...")
                cur.execute("DELETE FROM market_data")
                
                total_records = 0
                
                for exchange_name in exchanges:
                    if exchange_name not in self.collectors:
                        log.warning(f"⚠️  Unknown exchange: {exchange_name}")
                        continue
                    
                    collector = self.collectors[exchange_name]
                    
                    async with collector:
                        for symbol in symbols:
                            log.info(f"📊 Collecting {symbol} data from {exchange_name}...")
                            
                            # Get historical data
                            candles = await collector.get_historical_data(symbol, '1h', 1000)
                            
                            if candles:
                                # Insert into database
                                for candle in candles:
                                    cur.execute("""
                                        INSERT INTO market_data (timestamp, symbol, exchange, open, high, low, close, volume)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (timestamp, symbol, exchange) DO UPDATE SET
                                        open = EXCLUDED.open,
                                        high = EXCLUDED.high,
                                        low = EXCLUDED.low,
                                        close = EXCLUDED.close,
                                        volume = EXCLUDED.volume
                                    """, (
                                        candle.timestamp,
                                        candle.symbol,
                                        candle.exchange,
                                        candle.open,
                                        candle.high,
                                        candle.low,
                                        candle.close,
                                        candle.volume
                                    ))
                                
                                total_records += len(candles)
                                log.info(f"✅ Stored {len(candles)} candles for {symbol} from {exchange_name}")
                            
                            # Rate limiting between symbols
                            await asyncio.sleep(0.2)
                
                # Commit all data
                conn.commit()
                
                # Verify the data
                cur.execute("SELECT symbol, exchange, COUNT(*) as count FROM market_data GROUP BY symbol, exchange")
                results = cur.fetchall()
                
                log.info("\n📈 Real Market Data Summary:")
                for symbol, exchange, count in results:
                    cur.execute("""
                        SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest, 
                               MIN(close) as min_price, MAX(close) as max_price
                        FROM market_data WHERE symbol = %s AND exchange = %s
                    """, (symbol, exchange))
                    stats = cur.fetchone()
                    earliest = datetime.fromtimestamp(stats[0]).strftime('%Y-%m-%d %H:%M')
                    latest = datetime.fromtimestamp(stats[1]).strftime('%Y-%m-%d %H:%M')
                    log.info(f"  {symbol} ({exchange}): {count:,} records ({earliest} to {latest})")
                    log.info(f"    Price range: ${stats[2]:.2f} - ${stats[3]:.2f}")
                
                log.info(f"\n🎉 Successfully collected {total_records:,} real market data records!")
                
        except Exception as e:
            log.error(f"❌ Error collecting market data: {e}")
            conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    async def get_current_prices(self, symbols: List[str], exchange: str = 'binance') -> Dict[str, float]:
        """Get current prices for symbols"""
        if exchange not in self.collectors:
            log.error(f"❌ Unknown exchange: {exchange}")
            return {}
        
        collector = self.collectors[exchange]
        prices = {}
        
        async with collector:
            for symbol in symbols:
                price = await collector.get_current_price(symbol)
                if price > 0:
                    prices[symbol] = price
                await asyncio.sleep(0.1)  # Rate limiting
        
        return prices

async def main():
    """Main function to collect real market data"""
    
    # Symbols to collect (focusing on liquid pairs)
    symbols = [
        'BTC/USDT',
        'ETH/USDT', 
        'SOL/USDT',
        'ADA/USDT',
        'DOT/USDT'
    ]
    
    # Exchanges to use (fallback to CoinGecko if Binance is blocked)
    exchanges = ['coingecko']  # Using CoinGecko for reliable data
    
    manager = MarketDataManager()
    
    # Collect historical data
    await manager.collect_historical_data(symbols, exchanges)
    
    # Test current prices
    log.info("\n💰 Current Prices:")
    current_prices = await manager.get_current_prices(symbols)
    for symbol, price in current_prices.items():
        log.info(f"  {symbol}: ${price:.2f}")

if __name__ == "__main__":
    asyncio.run(main())