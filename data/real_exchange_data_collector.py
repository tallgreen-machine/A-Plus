#!/usr/bin/env python3
"""
Real Exchange Data Integration
Uses established CCXT-based exchange connections to populate market_data table
Integrates with existing ops/scripts/fetch_market_data.py infrastructure
"""

import os
import sys
import ccxt
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import time
import random

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from utils.logger import log

class RealExchangeDataCollector:
    """Uses established CCXT exchange connections for real market data"""
    
    def __init__(self):
        self.exchanges = self._initialize_exchanges()
        self.db_conn = None
        
    def _initialize_exchanges(self) -> Dict[str, ccxt.Exchange]:
        """Initialize the established exchange connections"""
        exchange_configs = {
            'binanceus': ccxt.binanceus(),
            'coinbase': ccxt.coinbase(),
            'kraken': ccxt.kraken(),
            'bitstamp': ccxt.bitstamp(),
            'gemini': ccxt.gemini(),
            'cryptocom': ccxt.cryptocom()
        }
        
        initialized_exchanges = {}
        for name, exchange in exchange_configs.items():
            try:
                exchange.load_markets()
                initialized_exchanges[name] = exchange
                log.info(f"✅ Initialized {name} exchange")
            except Exception as e:
                log.warning(f"⚠️ Could not initialize {name}: {e}")
                
        return initialized_exchanges
    
    def get_db_connection(self):
        """Get database connection using environment variables"""
        if not self.db_conn or self.db_conn.closed:
            self.db_conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                dbname=os.getenv("DB_NAME", "trad"),
                user=os.getenv("DB_USER", "traduser"),
                password=os.getenv("DB_PASSWORD", "TRAD123!")
            )
        return self.db_conn
    
    def insert_market_data_batch(self, market_data: List[Dict]) -> int:
        """Insert batch of market data into database"""
        if not market_data:
            return 0
            
        conn = self.get_db_connection()
        
        try:
            with conn.cursor() as cur:
                inserted_count = 0
                for data in market_data:
                    try:
                        cur.execute("""
                            INSERT INTO market_data (exchange, symbol, timestamp, open, high, low, close, volume)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (exchange, symbol, timestamp) DO NOTHING;
                        """, (
                            data['exchange'],
                            data['symbol'],
                            data['timestamp'],
                            data['open'],
                            data['high'],
                            data['low'],
                            data['close'],
                            data['volume']
                        ))
                        if cur.rowcount > 0:
                            inserted_count += 1
                    except Exception as e:
                        log.error(f"Error inserting candle data: {e}")
                        continue
                
                conn.commit()
                return inserted_count
                
        except Exception as e:
            log.error(f"Database batch insert error: {e}")
            conn.rollback()
            return 0
    
    def fetch_historical_data(self, symbol: str, exchange_name: str, timeframe: str = '1h', limit: int = 1000) -> List[Dict]:
        """Fetch historical OHLCV data from specific exchange"""
        if exchange_name not in self.exchanges:
            log.error(f"Exchange {exchange_name} not available")
            return []
            
        exchange = self.exchanges[exchange_name]
        
        # Convert symbol format if needed
        try:
            if not exchange.has['fetchOHLCV']:
                log.warning(f"{exchange_name} doesn't support OHLCV fetching")
                return []
                
            # Try the symbol as-is first, then try variations
            symbols_to_try = [symbol]
            if symbol.endswith('/USDT'):
                symbols_to_try.append(symbol.replace('/USDT', '/USD'))
            elif symbol.endswith('/USD'):
                symbols_to_try.append(symbol.replace('/USD', '/USDT'))
                
            for sym in symbols_to_try:
                try:
                    log.info(f"Fetching {sym} from {exchange_name}...")
                    ohlcv_data = exchange.fetch_ohlcv(sym, timeframe, limit=limit)
                    
                    market_data = []
                    for candle in ohlcv_data:
                        timestamp, open_price, high, low, close, volume = candle
                        
                        market_data.append({
                            'exchange': exchange_name,
                            'symbol': symbol,  # Use original symbol format
                            'timestamp': int(timestamp // 1000),  # Convert ms to seconds
                            'open': float(open_price),
                            'high': float(high),
                            'low': float(low),
                            'close': float(close),
                            'volume': float(volume) if volume else 0.0
                        })
                    
                    log.info(f"✅ Fetched {len(market_data)} candles for {sym} from {exchange_name}")
                    return market_data
                    
                except ccxt.BadSymbol:
                    continue
                except Exception as e:
                    log.error(f"Error fetching {sym} from {exchange_name}: {e}")
                    continue
                    
            log.warning(f"Could not find {symbol} on {exchange_name}")
            return []
            
        except Exception as e:
            log.error(f"Error with {exchange_name} for {symbol}: {e}")
            return []
    
    def collect_multi_exchange_data(self, symbols: List[str], limit: int = 1000) -> Dict[str, int]:
        """Collect data from multiple exchanges for training diversity"""
        results = {'total_inserted': 0, 'exchanges_used': 0, 'symbols_collected': 0}
        
        # Priority order for exchanges (most reliable first)
        exchange_priority = ['kraken', 'coinbase', 'bitstamp', 'binanceus', 'gemini', 'cryptocom']
        available_exchanges = [ex for ex in exchange_priority if ex in self.exchanges]
        
        log.info(f"🚀 Collecting data for {len(symbols)} symbols from {len(available_exchanges)} exchanges")
        
        for symbol in symbols:
            symbol_collected = False
            
            # Try to get data from at least 2 exchanges per symbol for diversity
            exchanges_used_for_symbol = 0
            target_exchanges_per_symbol = min(2, len(available_exchanges))
            
            for exchange_name in available_exchanges:
                if exchanges_used_for_symbol >= target_exchanges_per_symbol:
                    break
                    
                try:
                    log.info(f"📊 Fetching {symbol} from {exchange_name}")
                    market_data = self.fetch_historical_data(symbol, exchange_name, limit=limit)
                    
                    if market_data:
                        inserted = self.insert_market_data_batch(market_data)
                        results['total_inserted'] += inserted
                        
                        if inserted > 0:
                            exchanges_used_for_symbol += 1
                            symbol_collected = True
                            log.info(f"✅ Inserted {inserted} candles for {symbol} from {exchange_name}")
                        
                    # Rate limiting - be respectful
                    time.sleep(1)
                    
                except Exception as e:
                    log.error(f"Error collecting {symbol} from {exchange_name}: {e}")
                    continue
            
            if symbol_collected:
                results['symbols_collected'] += 1
                
        results['exchanges_used'] = len(available_exchanges)
        return results
    
    def verify_data_collection(self) -> Dict[str, any]:
        """Verify the collected data and return statistics"""
        conn = self.get_db_connection()
        
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Get overall statistics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(DISTINCT symbol) as unique_symbols,
                        COUNT(DISTINCT exchange) as unique_exchanges,
                        MIN(timestamp) as earliest_timestamp,
                        MAX(timestamp) as latest_timestamp
                    FROM market_data
                """)
                overall_stats = cur.fetchone()
                
                # Get per-symbol statistics
                cur.execute("""
                    SELECT 
                        symbol,
                        COUNT(*) as record_count,
                        COUNT(DISTINCT exchange) as exchange_count,
                        MIN(close) as min_price,
                        MAX(close) as max_price,
                        AVG(volume) as avg_volume
                    FROM market_data 
                    GROUP BY symbol 
                    ORDER BY record_count DESC
                """)
                symbol_stats = cur.fetchall()
                
                # Get per-exchange statistics
                cur.execute("""
                    SELECT 
                        exchange,
                        COUNT(*) as record_count,
                        COUNT(DISTINCT symbol) as symbol_count
                    FROM market_data 
                    GROUP BY exchange 
                    ORDER BY record_count DESC
                """)
                exchange_stats = cur.fetchall()
                
                return {
                    'overall': dict(overall_stats),
                    'by_symbol': [dict(row) for row in symbol_stats],
                    'by_exchange': [dict(row) for row in exchange_stats]
                }
                
        except Exception as e:
            log.error(f"Error verifying data collection: {e}")
            return {'error': str(e)}

def main():
    """Main function to collect real exchange data for training"""
    log.info("🚀 Starting Real Exchange Data Collection")
    
    # High-priority symbols for training
    training_symbols = [
        'BTC/USDT',
        'ETH/USDT',
        'SOL/USDT',
        'ADA/USDT',
        'DOT/USDT',
        'MATIC/USDT',
        'AVAX/USDT'
    ]
    
    collector = RealExchangeDataCollector()
    
    # Collect historical data (last 1000 hours ~ 41 days per exchange)
    results = collector.collect_multi_exchange_data(training_symbols, limit=1000)
    
    log.info(f"""
📈 Data Collection Complete!
- Total records inserted: {results['total_inserted']:,}
- Symbols collected: {results['symbols_collected']}/{len(training_symbols)}
- Exchanges used: {results['exchanges_used']}
    """)
    
    # Verify the collection
    verification = collector.verify_data_collection()
    
    if 'error' not in verification:
        overall = verification['overall']
        earliest = datetime.fromtimestamp(overall['earliest_timestamp']) if overall['earliest_timestamp'] else 'N/A'
        latest = datetime.fromtimestamp(overall['latest_timestamp']) if overall['latest_timestamp'] else 'N/A'
        
        log.info(f"""
🔍 Data Verification:
- Total records: {overall['total_records']:,}
- Unique symbols: {overall['unique_symbols']}
- Unique exchanges: {overall['unique_exchanges']}
- Time range: {earliest} to {latest}
        """)
        
        log.info("\n📊 Top symbols by record count:")
        for symbol_stat in verification['by_symbol'][:5]:
            log.info(f"  {symbol_stat['symbol']}: {symbol_stat['record_count']:,} records from {symbol_stat['exchange_count']} exchanges")
        
        log.info("\n🏛️ Exchange contributions:")
        for exchange_stat in verification['by_exchange']:
            log.info(f"  {exchange_stat['exchange']}: {exchange_stat['record_count']:,} records for {exchange_stat['symbol_count']} symbols")
    
    log.info("✅ Real exchange data collection completed!")

if __name__ == "__main__":
    main()