#!/usr/bin/env python3
"""
Enhanced Multi-Timeframe Data Collector
Collects OHLCV, trades, order book, and ticker data for comprehensive ML training
"""

import sys
import os
import ccxt
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import psycopg2
import psycopg2.extras

# Add paths for imports
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

from utils.logger import log as logger
from shared.db import get_db_conn


class EnhancedDataCollector:
    """Enhanced data collector for multi-timeframe, multi-data-type collection"""
    
    def __init__(self):
        self.logger = logger
        self.exchanges = self._initialize_exchanges()
        
        # Configuration
        self.symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 
            'DOT/USDT', 'AVAX/USDT', 'MATIC/USDT', 'LINK/USDT',
            'UNI/USDT', 'ATOM/USDT'  # Added more symbols
        ]
        
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        # Rate limiting
        self.rate_limits = {
            'binanceus': 0.05,    # 50ms
            'coinbase': 0.034,    # 34ms  
            'kraken': 1.0,        # 1000ms
            'bitstamp': 0.075,    # 75ms
            'gemini': 0.1,        # 100ms
            'cryptocom': 0.01     # 10ms
        }
        
    def _initialize_exchanges(self) -> Dict[str, ccxt.Exchange]:
        """Initialize all available exchanges"""
        exchanges = {}
        
        exchange_configs = {
            'binanceus': ccxt.binanceus({'sandbox': False, 'enableRateLimit': True}),
            'coinbase': ccxt.coinbase({'sandbox': False, 'enableRateLimit': True}),
            'kraken': ccxt.kraken({'sandbox': False, 'enableRateLimit': True}),
            'bitstamp': ccxt.bitstamp({'sandbox': False, 'enableRateLimit': True}),
            'gemini': ccxt.gemini({'sandbox': False, 'enableRateLimit': True}),
            'cryptocom': ccxt.cryptocom({'sandbox': False, 'enableRateLimit': True})
        }
        
        for name, exchange in exchange_configs.items():
            try:
                exchanges[name] = exchange
                self.logger.info(f"✅ Initialized {name} exchange")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize {name}: {e}")
                
        return exchanges
    
    def get_db_connection(self):
        """Get database connection"""
        return get_db_conn()
    
    def start_collection_run(self, run_type: str, exchange: str, symbols: List[str], 
                           timeframes: Optional[List[str]] = None) -> int:
        """Start a new collection run and return the run ID"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO collection_runs (run_type, exchange, symbols, timeframes, start_time)
            VALUES (%s, %s, %s, %s, NOW())
            RETURNING id
        """, (run_type, exchange, symbols, timeframes))
        
        run_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return run_id
    
    def update_collection_run(self, run_id: int, status: str, records_collected: int = 0, 
                            errors_count: int = 0, error_details: str = None):
        """Update collection run status"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE collection_runs 
            SET status = %s, end_time = NOW(), records_collected = %s, 
                errors_count = %s, error_details = %s
            WHERE id = %s
        """, (status, records_collected, errors_count, error_details, run_id))
        
        conn.commit()
        conn.close()
    
    # =====================================================
    # MULTI-TIMEFRAME OHLCV COLLECTION
    # =====================================================
    
    def collect_ohlcv_data(self, symbols: List[str] = None, 
                          timeframes: List[str] = None,
                          exchanges: List[str] = None,
                          lookback_days: int = 30) -> Dict[str, Any]:
        """Collect OHLCV data across multiple timeframes"""
        
        symbols = symbols or self.symbols
        timeframes = timeframes or self.timeframes
        exchanges = exchanges or list(self.exchanges.keys())
        
        self.logger.info(f"🚀 Starting OHLCV collection for {len(symbols)} symbols, "
                        f"{len(timeframes)} timeframes, {len(exchanges)} exchanges")
        
        total_collected = 0
        total_errors = 0
        collection_summary = {}
        
        for exchange_name in exchanges:
            if exchange_name not in self.exchanges:
                continue
                
            exchange = self.exchanges[exchange_name]
            
            # Start collection run
            run_id = self.start_collection_run('ohlcv', exchange_name, symbols, timeframes)
            
            exchange_collected = 0
            exchange_errors = 0
            
            self.logger.info(f"📊 Collecting from {exchange_name}...")
            
            for symbol in symbols:
                for timeframe in timeframes:
                    try:
                        # Check if this timeframe is supported
                        if hasattr(exchange, 'timeframes') and exchange.timeframes:
                            if timeframe not in exchange.timeframes:
                                continue
                        
                        # Calculate how many candles to fetch
                        limit = self._calculate_limit_for_timeframe(timeframe, lookback_days)
                        
                        # Fetch OHLCV data
                        ohlcv_data = self._fetch_ohlcv_with_retry(
                            exchange, exchange_name, symbol, timeframe, limit
                        )
                        
                        if ohlcv_data:
                            # Insert into enhanced table
                            inserted = self._insert_ohlcv_enhanced(
                                exchange_name, symbol, timeframe, ohlcv_data
                            )
                            
                            exchange_collected += inserted
                            self.logger.info(f"✅ {symbol} {timeframe} on {exchange_name}: {inserted} candles")
                        
                        # Rate limiting
                        time.sleep(self.rate_limits.get(exchange_name, 0.1))
                        
                    except Exception as e:
                        exchange_errors += 1
                        self.logger.error(f"❌ {symbol} {timeframe} on {exchange_name}: {str(e)}")
            
            # Update collection run
            self.update_collection_run(run_id, 'completed', exchange_collected, exchange_errors)
            
            total_collected += exchange_collected
            total_errors += exchange_errors
            collection_summary[exchange_name] = {
                'collected': exchange_collected,
                'errors': exchange_errors
            }
        
        self.logger.info(f"🎉 OHLCV Collection Complete! Total: {total_collected:,} records, {total_errors} errors")
        
        return {
            'total_collected': total_collected,
            'total_errors': total_errors,
            'summary': collection_summary
        }
    
    def _calculate_limit_for_timeframe(self, timeframe: str, lookback_days: int) -> int:
        """Calculate how many candles to fetch for given timeframe and lookback period"""
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        minutes = timeframe_minutes.get(timeframe, 60)
        total_minutes = lookback_days * 24 * 60
        limit = min(total_minutes // minutes, 1000)  # Max 1000 per request
        
        return max(limit, 100)  # Minimum 100 candles
    
    def _fetch_ohlcv_with_retry(self, exchange: ccxt.Exchange, exchange_name: str,
                               symbol: str, timeframe: str, limit: int,
                               max_retries: int = 3) -> List[List]:
        """Fetch OHLCV with retry logic and symbol variations"""
        
        # Try different symbol formats
        symbols_to_try = [symbol]
        if symbol.endswith('/USDT'):
            symbols_to_try.append(symbol.replace('/USDT', '/USD'))
        elif symbol.endswith('/USD'):
            symbols_to_try.append(symbol.replace('/USD', '/USDT'))
        
        for attempt in range(max_retries):
            for sym in symbols_to_try:
                try:
                    self.logger.info(f"Fetching {sym} {timeframe} from {exchange_name} (attempt {attempt + 1})")
                    ohlcv_data = exchange.fetch_ohlcv(sym, timeframe, limit=limit)
                    
                    if ohlcv_data:
                        return ohlcv_data
                        
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.logger.warning(f"Failed {sym} {timeframe} on {exchange_name}: {str(e)}")
                    else:
                        time.sleep(1)  # Brief pause before retry
        
        return []
    
    def _insert_ohlcv_enhanced(self, exchange: str, symbol: str, timeframe: str, 
                              ohlcv_data: List[List]) -> int:
        """Insert OHLCV data into enhanced market_data table"""
        if not ohlcv_data:
            return 0
        
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        insert_data = []
        for candle in ohlcv_data:
            timestamp, open_price, high, low, close, volume = candle[:6]
            
            # Additional fields if available
            quote_volume = candle[6] if len(candle) > 6 else None
            trade_count = candle[7] if len(candle) > 7 else None
            
            insert_data.append((
                exchange, symbol, timeframe, timestamp,
                open_price, high, low, close, volume,
                quote_volume, trade_count
            ))
        
        # Bulk insert with conflict resolution
        try:
            cur.executemany("""
                INSERT INTO market_data_enhanced 
                (exchange, symbol, timeframe, timestamp, open, high, low, close, volume, quote_volume, trade_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exchange, symbol, timeframe, timestamp) DO NOTHING
            """, insert_data)
            
            inserted_count = cur.rowcount
            conn.commit()
            conn.close()
            
            return inserted_count
            
        except Exception as e:
            self.logger.error(f"Database insert error: {e}")
            conn.rollback()
            conn.close()
            return 0
    
    # =====================================================
    # INDIVIDUAL TRADES COLLECTION
    # =====================================================
    
    def collect_trades_data(self, symbols: List[str] = None, 
                           exchanges: List[str] = None,
                           limit_per_symbol: int = 1000) -> Dict[str, Any]:
        """Collect individual trade data"""
        
        symbols = symbols or self.symbols[:5]  # Limit symbols for trades
        exchanges = exchanges or list(self.exchanges.keys())
        
        self.logger.info(f"💸 Starting trades collection for {len(symbols)} symbols")
        
        total_collected = 0
        total_errors = 0
        
        for exchange_name in exchanges:
            if exchange_name not in self.exchanges:
                continue
                
            exchange = self.exchanges[exchange_name]
            
            if not exchange.has.get('fetchTrades', False):
                self.logger.info(f"⏭️ {exchange_name} doesn't support fetchTrades")
                continue
            
            run_id = self.start_collection_run('trades', exchange_name, symbols)
            exchange_collected = 0
            exchange_errors = 0
            
            for symbol in symbols:
                try:
                    trades = self._fetch_trades_with_retry(exchange, exchange_name, symbol, limit_per_symbol)
                    
                    if trades:
                        inserted = self._insert_trades_data(exchange_name, symbol, trades)
                        exchange_collected += inserted
                        self.logger.info(f"✅ {symbol} trades on {exchange_name}: {inserted} records")
                    
                    time.sleep(self.rate_limits.get(exchange_name, 0.1))
                    
                except Exception as e:
                    exchange_errors += 1
                    self.logger.error(f"❌ {symbol} trades on {exchange_name}: {str(e)}")
            
            self.update_collection_run(run_id, 'completed', exchange_collected, exchange_errors)
            total_collected += exchange_collected
            total_errors += exchange_errors
        
        self.logger.info(f"🎉 Trades Collection Complete! Total: {total_collected:,} records")
        return {'total_collected': total_collected, 'total_errors': total_errors}
    
    def _fetch_trades_with_retry(self, exchange: ccxt.Exchange, exchange_name: str,
                                symbol: str, limit: int) -> List[Dict]:
        """Fetch trades with retry logic"""
        try:
            trades = exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            self.logger.warning(f"Failed to fetch trades for {symbol} on {exchange_name}: {str(e)}")
            return []
    
    def _insert_trades_data(self, exchange: str, symbol: str, trades: List[Dict]) -> int:
        """Insert trades data into database"""
        if not trades:
            return 0
        
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        insert_data = []
        for trade in trades:
            insert_data.append((
                exchange, symbol, trade.get('id'),
                int(trade['timestamp']), trade['price'], trade['amount'],
                trade.get('cost', trade['price'] * trade['amount']),
                trade.get('side'), trade.get('takerOrMaker')
            ))
        
        try:
            cur.executemany("""
                INSERT INTO trade_data 
                (exchange, symbol, trade_id, timestamp, price, amount, cost, side, taker_or_maker)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exchange, symbol, trade_id) DO NOTHING
            """, insert_data)
            
            inserted_count = cur.rowcount
            conn.commit()
            conn.close()
            return inserted_count
            
        except Exception as e:
            self.logger.error(f"Trades insert error: {e}")
            conn.rollback()
            conn.close()
            return 0
    
    # =====================================================
    # ORDER BOOK SNAPSHOTS
    # =====================================================
    
    def collect_orderbook_snapshots(self, symbols: List[str] = None,
                                   exchanges: List[str] = None) -> Dict[str, Any]:
        """Collect order book snapshots"""
        
        symbols = symbols or self.symbols[:3]  # Limit for order books
        exchanges = exchanges or list(self.exchanges.keys())
        
        self.logger.info(f"📖 Starting order book collection for {len(symbols)} symbols")
        
        total_collected = 0
        
        for exchange_name in exchanges:
            if exchange_name not in self.exchanges:
                continue
                
            exchange = self.exchanges[exchange_name]
            
            if not exchange.has.get('fetchOrderBook', False):
                continue
            
            for symbol in symbols:
                try:
                    orderbook = exchange.fetch_order_book(symbol, limit=10)
                    
                    if orderbook:
                        inserted = self._insert_orderbook_snapshot(exchange_name, symbol, orderbook)
                        total_collected += inserted
                        self.logger.info(f"✅ {symbol} orderbook on {exchange_name}")
                    
                    time.sleep(self.rate_limits.get(exchange_name, 0.1))
                    
                except Exception as e:
                    self.logger.error(f"❌ {symbol} orderbook on {exchange_name}: {str(e)}")
        
        return {'total_collected': total_collected}
    
    def _insert_orderbook_snapshot(self, exchange: str, symbol: str, orderbook: Dict) -> int:
        """Insert order book snapshot"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        bids = orderbook.get('bids', [])[:10]  # Top 10 bids
        asks = orderbook.get('asks', [])[:10]  # Top 10 asks
        
        # Calculate metrics
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None
        spread = (best_ask - best_bid) if (best_bid and best_ask) else None
        mid_price = ((best_bid + best_ask) / 2) if (best_bid and best_ask) else None
        spread_pct = (spread / mid_price * 100) if (spread and mid_price) else None
        
        bid_depth = sum(bid[1] for bid in bids) if bids else None
        ask_depth = sum(ask[1] for ask in asks) if asks else None
        
        try:
            cur.execute("""
                INSERT INTO order_book_snapshots 
                (exchange, symbol, timestamp, bids, asks, best_bid, best_ask, 
                 spread, spread_pct, mid_price, bid_depth, ask_depth)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                exchange, symbol, int(time.time() * 1000),
                json.dumps(bids), json.dumps(asks),
                best_bid, best_ask, spread, spread_pct, mid_price,
                bid_depth, ask_depth
            ))
            
            conn.commit()
            conn.close()
            return 1
            
        except Exception as e:
            self.logger.error(f"Order book insert error: {e}")
            conn.rollback()
            conn.close()
            return 0
    
    # =====================================================
    # COMPREHENSIVE COLLECTION RUNNER
    # =====================================================
    
    def run_comprehensive_collection(self, lookback_days: int = 90) -> Dict[str, Any]:
        """Run comprehensive data collection across all data types"""
        
        self.logger.info(f"🚀 Starting comprehensive data collection ({lookback_days} days history)")
        
        results = {}
        
        # 1. Multi-timeframe OHLCV data
        self.logger.info("📊 Phase 1: Multi-timeframe OHLCV data")
        results['ohlcv'] = self.collect_ohlcv_data(lookback_days=lookback_days)
        
        # 2. Individual trades
        self.logger.info("💸 Phase 2: Individual trades data")
        results['trades'] = self.collect_trades_data()
        
        # 3. Order book snapshots
        self.logger.info("📖 Phase 3: Order book snapshots")
        results['orderbook'] = self.collect_orderbook_snapshots()
        
        # 4. Summary
        total_records = (
            results['ohlcv'].get('total_collected', 0) +
            results['trades'].get('total_collected', 0) +
            results['orderbook'].get('total_collected', 0)
        )
        
        self.logger.info(f"🎉 Comprehensive collection complete! Total records: {total_records:,}")
        
        return {
            'total_records': total_records,
            'results': results,
            'completion_time': datetime.now().isoformat()
        }


def main():
    """Run the enhanced data collector"""
    collector = EnhancedDataCollector()
    
    print("🚀 Enhanced Multi-Timeframe Data Collector")
    print("==========================================")
    
    # Run comprehensive collection
    results = collector.run_comprehensive_collection(lookback_days=60)
    
    print(f"\n✅ Collection Complete!")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()