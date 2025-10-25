#!/usr/bin/env python3
"""
Massive Historical Data Backfill Script
Collects 18 months of OHLCV data across all exchanges, symbols, and timeframes

This script will run for 6-12 hours to collect ~3 million records.
Run in background: nohup python3 data/massive_historical_backfill.py > backfill.log 2>&1 &
"""

import sys
import os
import ccxt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import psycopg2
import psycopg2.extras

# Add paths for imports
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

from utils.logger import log as logger
from shared.db import get_db_conn


class MassiveHistoricalBackfill:
    """
    Comprehensive historical data collector for ML training.
    
    Target: 3+ million records across:
    - 6 exchanges (BinanceUS, Coinbase, Kraken, Bitstamp, Gemini, Crypto.com)
    - 12 symbols (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM)
    - 6 timeframes (1m, 5m, 15m, 1h, 4h, 1d)
    - 18 months of history
    """
    
    def __init__(self):
        self.logger = logger
        self.exchanges = self._initialize_exchanges()
        
        # Tier 1: Highest priority symbols (most liquid)
        self.tier1_symbols = [
            'BTC/USDT',  # Bitcoin - highest priority
            'ETH/USDT',  # Ethereum
            'SOL/USDT',  # Solana - high volatility
        ]
        
        # Tier 2: High priority symbols
        self.tier2_symbols = [
            'BNB/USDT',   # Binance Coin
            'XRP/USDT',   # Ripple
            'ADA/USDT',   # Cardano
            'AVAX/USDT',  # Avalanche
            'DOT/USDT',   # Polkadot
        ]
        
        # Tier 3: Medium priority symbols
        self.tier3_symbols = [
            'MATIC/USDT',  # Polygon
            'LINK/USDT',   # Chainlink
            'UNI/USDT',    # Uniswap
            'ATOM/USDT',   # Cosmos
        ]
        
        # All timeframes (from smallest to largest)
        self.all_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        # Priority timeframes for ML training (most important first)
        self.priority_timeframes = ['1h', '4h', '1d', '15m', '5m', '1m']
        
        # Rate limits per exchange (seconds between requests)
        self.rate_limits = {
            'binanceus': 0.05,     # 50ms (most lenient)
            'coinbase': 0.167,     # 167ms (3 req/sec)
            'kraken': 1.0,         # 1000ms (most strict)
            'bitstamp': 0.1,       # 100ms
            'gemini': 0.2,         # 200ms
            'cryptocom': 0.05      # 50ms
        }
        
        # Exchange priority order (most reliable first)
        self.exchange_priority = [
            'binanceus',   # Best data availability
            'coinbase',    # Second best
            'kraken',      # Good historical depth
            'bitstamp',    # European but reliable
            'gemini',      # US regulated
            'cryptocom'    # Growing exchange
        ]
        
        # Progress tracking
        self.total_records_collected = 0
        self.total_api_calls = 0
        self.total_errors = 0
        self.start_time = datetime.now()
        
    def _initialize_exchanges(self) -> Dict[str, ccxt.Exchange]:
        """Initialize all US-accessible exchanges"""
        exchanges = {}
        
        exchange_configs = {
            'binanceus': ccxt.binanceus({'enableRateLimit': True, 'timeout': 30000}),
            'coinbase': ccxt.coinbase({'enableRateLimit': True, 'timeout': 30000}),
            'kraken': ccxt.kraken({'enableRateLimit': True, 'timeout': 30000}),
            'bitstamp': ccxt.bitstamp({'enableRateLimit': True, 'timeout': 30000}),
            'gemini': ccxt.gemini({'enableRateLimit': True, 'timeout': 30000}),
            'cryptocom': ccxt.cryptocom({'enableRateLimit': True, 'timeout': 30000})
        }
        
        for name, exchange in exchange_configs.items():
            try:
                exchange.load_markets()
                exchanges[name] = exchange
                self.logger.info(f"✅ Initialized {name} exchange")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not initialize {name}: {e}")
                
        return exchanges
    
    def get_db_connection(self):
        """Get database connection"""
        return get_db_conn()
    
    def calculate_time_chunks(self, timeframe: str, months_back: int) -> List[Tuple[datetime, datetime]]:
        """
        Calculate optimal time chunks to avoid rate limits and maximize data collection.
        
        Strategy: Fetch maximum candles per request, then chunk by that size.
        """
        # Timeframe in minutes
        tf_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '6h': 360, '12h': 720, '1d': 1440
        }
        
        minutes_per_candle = tf_minutes.get(timeframe, 60)
        
        # Most exchanges limit to 500-1000 candles per request
        # Use conservative 500 to be safe
        candles_per_chunk = 500
        chunk_duration_minutes = candles_per_chunk * minutes_per_candle
        chunk_duration = timedelta(minutes=chunk_duration_minutes)
        
        # Calculate date range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=months_back * 30)
        
        # Create chunks going backwards from now
        chunks = []
        current_end = end_time
        
        while current_end > start_time:
            current_start = max(current_end - chunk_duration, start_time)
            chunks.append((current_start, current_end))
            current_end = current_start
        
        return chunks
    
    def _insert_ohlcv_batch(self, exchange: str, symbol: str, timeframe: str, 
                           ohlcv_data: List[List]) -> int:
        """
        Insert OHLCV data into market_data table with conflict handling.
        Returns number of records inserted.
        """
        if not ohlcv_data:
            return 0
        
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        # Prepare insert with ON CONFLICT DO NOTHING
        insert_query = """
            INSERT INTO market_data (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (exchange, symbol, timeframe, timestamp) DO NOTHING
        """
        
        inserted = 0
        batch_data = []
        
        for candle in ohlcv_data:
            timestamp_ms = candle[0]
            open_price = float(candle[1])
            high_price = float(candle[2])
            low_price = float(candle[3])
            close_price = float(candle[4])
            volume = float(candle[5])
            
            batch_data.append((
                exchange, symbol, timeframe, timestamp_ms,
                open_price, high_price, low_price, close_price, volume
            ))
        
        try:
            cur.executemany(insert_query, batch_data)
            inserted = cur.rowcount
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database insert error: {e}")
            inserted = 0
        finally:
            cur.close()
            conn.close()
        
        return inserted
    
    def backfill_symbol_timeframe_exchange(self, symbol: str, timeframe: str, 
                                          exchange_name: str, months_back: int = 18) -> Dict[str, Any]:
        """
        Backfill historical data for a specific symbol/timeframe/exchange combination.
        
        Returns dict with collection statistics.
        """
        if exchange_name not in self.exchanges:
            return {'error': f'Exchange {exchange_name} not available', 'records': 0}
        
        exchange = self.exchanges[exchange_name]
        
        # Check if symbol is available on this exchange
        if symbol not in exchange.markets:
            self.logger.debug(f"⏭️ {symbol} not available on {exchange_name}")
            return {'error': 'Symbol not available', 'records': 0}
        
        # Check if timeframe is supported
        if hasattr(exchange, 'timeframes') and exchange.timeframes:
            if timeframe not in exchange.timeframes:
                self.logger.debug(f"⏭️ {timeframe} not supported on {exchange_name}")
                return {'error': 'Timeframe not supported', 'records': 0}
        
        self.logger.info(f"📊 Collecting {symbol} {timeframe} from {exchange_name} ({months_back} months)")
        
        # Calculate time chunks
        chunks = self.calculate_time_chunks(timeframe, months_back)
        
        total_collected = 0
        total_errors = 0
        
        for i, (start_time, end_time) in enumerate(chunks):
            try:
                # Convert to milliseconds
                since = int(start_time.timestamp() * 1000)
                limit = 500
                
                # Fetch OHLCV data
                ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                self.total_api_calls += 1
                
                if ohlcv_data:
                    # Insert into database
                    inserted = self._insert_ohlcv_batch(
                        exchange_name, symbol, timeframe, ohlcv_data
                    )
                    
                    total_collected += inserted
                    self.total_records_collected += inserted
                    
                    if inserted > 0:
                        self.logger.debug(f"  ✅ Chunk {i+1}/{len(chunks)}: {inserted} records")
                
                # Rate limiting
                time.sleep(self.rate_limits.get(exchange_name, 0.1))
                
            except Exception as e:
                total_errors += 1
                self.total_errors += 1
                self.logger.warning(f"  ❌ Chunk {i+1}/{len(chunks)} failed: {str(e)[:100]}")
                time.sleep(self.rate_limits.get(exchange_name, 0.1) * 2)  # Double wait on error
        
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'exchange': exchange_name,
            'months': months_back,
            'records': total_collected,
            'errors': total_errors,
            'chunks': len(chunks),
            'success_rate': (len(chunks) - total_errors) / len(chunks) * 100 if chunks else 0
        }
        
        if total_collected > 0:
            self.logger.info(f"✅ {exchange_name} {symbol} {timeframe}: {total_collected:,} records")
        
        return result
    
    def backfill_symbol_all_exchanges(self, symbol: str, timeframe: str, months_back: int = 18) -> List[Dict]:
        """Backfill a symbol/timeframe across ALL exchanges"""
        results = []
        
        for exchange_name in self.exchange_priority:
            if exchange_name in self.exchanges:
                result = self.backfill_symbol_timeframe_exchange(
                    symbol, timeframe, exchange_name, months_back
                )
                results.append(result)
                
                # Brief pause between exchanges
                time.sleep(1)
        
        return results
    
    def run_comprehensive_backfill(self) -> Dict[str, Any]:
        """
        Run the full comprehensive backfill across all tiers.
        
        Estimated time: 6-12 hours
        Estimated records: 3+ million
        """
        self.logger.info("🚀 STARTING MASSIVE HISTORICAL BACKFILL")
        self.logger.info("=" * 70)
        self.logger.info("Target: 3+ million records across 6 exchanges, 12 symbols, 6 timeframes")
        self.logger.info("Estimated time: 6-12 hours")
        self.logger.info("=" * 70)
        
        results = {
            'start_time': self.start_time.isoformat(),
            'tiers': {}
        }
        
        # Tier 1: Highest priority (BTC, ETH, SOL) - 18 months, all timeframes, all exchanges
        self.logger.info("\n📊 TIER 1: Core Assets (18 months, all timeframes, all exchanges)")
        tier1_results = []
        for symbol in self.tier1_symbols:
            self.logger.info(f"\n🔹 Processing {symbol}")
            for timeframe in self.priority_timeframes:
                exchange_results = self.backfill_symbol_all_exchanges(symbol, timeframe, months_back=18)
                tier1_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'exchanges': exchange_results
                })
                self._log_progress()
        
        results['tiers']['tier1'] = tier1_results
        
        # Tier 2: High priority (BNB, XRP, ADA, AVAX, DOT) - 12 months, all timeframes, all exchanges
        self.logger.info("\n📊 TIER 2: Major Altcoins (12 months, all timeframes, all exchanges)")
        tier2_results = []
        for symbol in self.tier2_symbols:
            self.logger.info(f"\n🔹 Processing {symbol}")
            for timeframe in self.priority_timeframes:
                exchange_results = self.backfill_symbol_all_exchanges(symbol, timeframe, months_back=12)
                tier2_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'exchanges': exchange_results
                })
                self._log_progress()
        
        results['tiers']['tier2'] = tier2_results
        
        # Tier 3: Medium priority (MATIC, LINK, UNI, ATOM) - 12 months, selected timeframes, 3 exchanges
        self.logger.info("\n📊 TIER 3: Secondary Altcoins (12 months, selected timeframes, top 3 exchanges)")
        tier3_results = []
        selected_timeframes = ['1h', '4h', '1d']  # Only most important timeframes
        for symbol in self.tier3_symbols:
            self.logger.info(f"\n🔹 Processing {symbol}")
            for timeframe in selected_timeframes:
                # Only top 3 exchanges for tier 3
                exchange_results = []
                for exchange_name in self.exchange_priority[:3]:
                    if exchange_name in self.exchanges:
                        result = self.backfill_symbol_timeframe_exchange(
                            symbol, timeframe, exchange_name, months_back=12
                        )
                        exchange_results.append(result)
                        time.sleep(1)
                
                tier3_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'exchanges': exchange_results
                })
                self._log_progress()
        
        results['tiers']['tier3'] = tier3_results
        
        # Final summary
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        results['end_time'] = end_time.isoformat()
        results['duration_hours'] = duration / 3600
        results['total_records'] = self.total_records_collected
        results['total_api_calls'] = self.total_api_calls
        results['total_errors'] = self.total_errors
        results['success_rate'] = ((self.total_api_calls - self.total_errors) / self.total_api_calls * 100) if self.total_api_calls > 0 else 0
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info("🎉 MASSIVE BACKFILL COMPLETE!")
        self.logger.info("=" * 70)
        self.logger.info(f"📊 Total Records: {self.total_records_collected:,}")
        self.logger.info(f"📞 Total API Calls: {self.total_api_calls:,}")
        self.logger.info(f"❌ Total Errors: {self.total_errors:,}")
        self.logger.info(f"✅ Success Rate: {results['success_rate']:.1f}%")
        self.logger.info(f"⏱️ Duration: {duration/3600:.1f} hours")
        self.logger.info(f"⚡ Avg Speed: {self.total_records_collected/(duration/60):.0f} records/minute")
        self.logger.info("=" * 70)
        
        return results
    
    def _log_progress(self):
        """Log current progress"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > 0:
            records_per_min = self.total_records_collected / (elapsed / 60)
            self.logger.info(f"📈 Progress: {self.total_records_collected:,} records | {records_per_min:.0f}/min | {self.total_errors} errors")


def main():
    """Run the massive historical backfill"""
    print("\n" + "=" * 70)
    print("🚀 MASSIVE HISTORICAL DATA BACKFILL")
    print("=" * 70)
    print("This will collect 18 months of data for comprehensive ML training")
    print("")
    print("Target:")
    print("  - 6 exchanges: BinanceUS, Coinbase, Kraken, Bitstamp, Gemini, Crypto.com")
    print("  - 12 symbols: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM")
    print("  - 6 timeframes: 1m, 5m, 15m, 1h, 4h, 1d")
    print("  - 18 months history (Tier 1), 12 months (Tier 2 & 3)")
    print("")
    print("Estimated:")
    print("  - Records: 3,000,000+")
    print("  - Duration: 6-12 hours")
    print("  - Storage: ~2 GB")
    print("=" * 70)
    
    # Check for --auto-confirm flag to skip interactive prompt
    import sys
    if '--auto-confirm' not in sys.argv:
        response = input("\n⚠️  This will run for many hours. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return
    else:
        print("\n✅ Auto-confirmed (--auto-confirm flag)")
    
    print("\n🚀 Starting backfill...\n")
    
    backfill = MassiveHistoricalBackfill()
    results = backfill.run_comprehensive_backfill()
    
    # Save results to file
    results_file = f'massive_backfill_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {results_file}")
    print(f"📊 Total records collected: {results['total_records']:,}")
    print(f"⏱️ Total time: {results['duration_hours']:.1f} hours")
    print("\n🎉 DONE! Your database is now ready for ML training!")


if __name__ == "__main__":
    main()
