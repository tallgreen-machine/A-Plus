#!/usr/bin/env python3
"""
Targeted Historical Data Backfill Script
For filling specific gaps in market data based on MARKET_DATA_INVENTORY analysis
"""

import sys
import os
import ccxt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse

sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

from utils.logger import log as logger
from shared.db import get_db_conn


class TargetedBackfill:
    """Focused backfill for specific symbols/timeframes/exchanges"""
    
    def __init__(self, exchange_name: str):
        self.logger = logger
        self.exchange_name = exchange_name
        self.exchange = self._initialize_exchange(exchange_name)
        
        # Optimized limits from exchange_limits_tester.py
        self.rate_limits = {
            'binanceus': 0.073,    # 13.71 req/sec
            'coinbase': 0.102,     # 9.82 req/sec
            'bitstamp': 0.185,     # 5.41 req/sec
            'gemini': 0.471,       # 2.12 req/sec
            'cryptocom': 0.183     # 5.46 req/sec
        }
        
        self.candle_limits = {
            'binanceus': 1000,
            'cryptocom': 300,
            'coinbase': 229,
            'bitstamp': 1000,
            'gemini': 1440
        }
        
        self.total_records = 0
        self.total_api_calls = 0
        self.total_errors = 0
        
    def _initialize_exchange(self, name: str):
        """Initialize single exchange"""
        exchange_map = {
            'binanceus': ccxt.binanceus,
            'coinbase': ccxt.coinbase,
            'bitstamp': ccxt.bitstamp,
            'gemini': ccxt.gemini,
            'cryptocom': ccxt.cryptocom
        }
        
        if name not in exchange_map:
            raise ValueError(f"Unknown exchange: {name}")
        
        exchange = exchange_map[name]({'enableRateLimit': True, 'timeout': 30000})
        exchange.load_markets()
        self.logger.info(f"✅ Initialized {name}")
        return exchange
    
    def _insert_ohlcv_batch(self, symbol: str, timeframe: str, ohlcv_data: List[List]) -> int:
        """Insert OHLCV data with conflict handling"""
        if not ohlcv_data:
            return 0
        
        conn = get_db_conn()
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO market_data (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (exchange, symbol, timeframe, timestamp) DO NOTHING
        """
        
        batch_data = []
        for candle in ohlcv_data:
            batch_data.append((
                self.exchange_name, symbol, timeframe, candle[0],
                float(candle[1]), float(candle[2]), float(candle[3]), 
                float(candle[4]), float(candle[5])
            ))
        
        try:
            cur.executemany(insert_query, batch_data)
            inserted = cur.rowcount
            conn.commit()
            return inserted
        except Exception as e:
            self.logger.error(f"Insert error: {e}")
            conn.rollback()
            return 0
        finally:
            cur.close()
            conn.close()
    
    def backfill_symbol(self, symbol: str, timeframes: List[str], months_back: int) -> Dict:
        """Backfill specific symbol across timeframes"""
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"📊 Backfilling {symbol} on {self.exchange_name}")
        self.logger.info(f"   Timeframes: {', '.join(timeframes)}")
        self.logger.info(f"   History: {months_back} months (~{months_back * 30} days)")
        self.logger.info(f"{'='*70}\n")
        
        results = {'symbol': symbol, 'timeframes': {}}
        
        # Check symbol availability
        if symbol not in self.exchange.markets:
            self.logger.error(f"❌ {symbol} not available on {self.exchange_name}")
            return results
        
        for timeframe in timeframes:
            self.logger.info(f"🔄 Processing {symbol} {timeframe}...")
            
            try:
                tf_results = self._backfill_timeframe(symbol, timeframe, months_back)
                results['timeframes'][timeframe] = tf_results
                
                self.logger.info(f"   ✅ {timeframe}: {tf_results['records']:,} records "
                               f"({tf_results['api_calls']} API calls, {tf_results['errors']} errors)")
                
            except Exception as e:
                self.logger.error(f"   ❌ {timeframe} failed: {e}")
                results['timeframes'][timeframe] = {'error': str(e), 'records': 0}
        
        return results
    
    def _backfill_timeframe(self, symbol: str, timeframe: str, months_back: int) -> Dict:
        """Backfill specific timeframe"""
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=months_back * 30)
        
        # Get limits for this exchange
        candles_per_request = self.candle_limits.get(self.exchange_name, 500)
        rate_limit = self.rate_limits.get(self.exchange_name, 0.1)
        
        # Timeframe to minutes
        tf_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440
        }
        minutes = tf_minutes.get(timeframe, 60)
        
        # Calculate chunk size
        chunk_duration = timedelta(minutes=candles_per_request * minutes)
        
        records_collected = 0
        api_calls = 0
        errors = 0
        
        current_time = start_time
        
        while current_time < end_time:
            try:
                since = int(current_time.timestamp() * 1000)
                
                # Fetch data
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=candles_per_request
                )
                api_calls += 1
                self.total_api_calls += 1
                
                if ohlcv:
                    inserted = self._insert_ohlcv_batch(symbol, timeframe, ohlcv)
                    records_collected += inserted
                    self.total_records += inserted
                    
                    # Move to next chunk based on last candle received
                    last_timestamp = ohlcv[-1][0]
                    current_time = datetime.fromtimestamp(last_timestamp / 1000) + timedelta(minutes=minutes)
                else:
                    # No data, skip forward
                    current_time += chunk_duration
                
                # Rate limiting
                time.sleep(rate_limit)
                
            except Exception as e:
                errors += 1
                self.total_errors += 1
                self.logger.warning(f"     ⚠️ Error at {current_time}: {str(e)[:80]}")
                current_time += chunk_duration
                time.sleep(rate_limit * 2)  # Extra delay after error
        
        return {
            'records': records_collected,
            'api_calls': api_calls,
            'errors': errors
        }


def main():
    parser = argparse.ArgumentParser(description='Targeted market data backfill')
    parser.add_argument('--exchange', required=True, help='Exchange name (binanceus, coinbase, etc)')
    parser.add_argument('--symbols', required=True, help='Comma-separated symbols (e.g., MATIC/USDT,ADA/USDT)')
    parser.add_argument('--timeframes', default='1m,5m,15m,1h,4h,1d', help='Comma-separated timeframes')
    parser.add_argument('--months', type=int, default=18, help='Months of history to backfill')
    parser.add_argument('--auto-confirm', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    symbols = [s.strip() for s in args.symbols.split(',')]
    timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    
    print(f"\n{'='*70}")
    print("🎯 TARGETED HISTORICAL DATA BACKFILL")
    print(f"{'='*70}")
    print(f"Exchange: {args.exchange}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"History: {args.months} months")
    print(f"{'='*70}\n")
    
    if not args.auto_confirm:
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return
    
    print("\n🚀 Starting backfill...\n")
    
    start_time = datetime.now()
    backfill = TargetedBackfill(args.exchange)
    
    all_results = {}
    for symbol in symbols:
        results = backfill.backfill_symbol(symbol, timeframes, args.months)
        all_results[symbol] = results
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*70}")
    print("🎉 BACKFILL COMPLETE")
    print(f"{'='*70}")
    print(f"📊 Total Records: {backfill.total_records:,}")
    print(f"📞 API Calls: {backfill.total_api_calls:,}")
    print(f"❌ Errors: {backfill.total_errors:,}")
    print(f"⏱️ Duration: {duration/60:.1f} minutes")
    print(f"⚡ Speed: {backfill.total_records/(duration/60):.0f} records/min")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
