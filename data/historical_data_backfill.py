#!/usr/bin/env python3
"""
Historical Data Backfill Script
Gets 1-2 years of historical data across all timeframes for comprehensive ML training
"""

import sys
import os
import ccxt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Add paths for imports
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

from utils.logger import log as logger
from data.enhanced_data_collector import EnhancedDataCollector


class HistoricalDataBackfill:
    """Specialized collector for gathering large amounts of historical data"""
    
    def __init__(self):
        self.logger = logger
        self.collector = EnhancedDataCollector()
        
        # High-priority symbols for ML training
        self.priority_symbols = [
            'BTC/USDT',   # Most liquid and stable
            'ETH/USDT',   # Second largest market cap
            'SOL/USDT',   # High volatility, good for training
            'ADA/USDT',   # Different price range
            'DOT/USDT',   # Alternative architecture
        ]
        
        # All timeframes for comprehensive analysis
        self.all_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '6h', '12h', '1d']
        
        # Exchanges with best data availability
        self.reliable_exchanges = ['binanceus', 'coinbase', 'kraken']
        
    def calculate_optimal_chunks(self, timeframe: str, months_back: int) -> List[Tuple[datetime, datetime]]:
        """Calculate optimal time chunks to avoid rate limits"""
        
        # Maximum candles per request by exchange
        max_limits = {
            'binanceus': 1000,
            'coinbase': 300,
            'kraken': 720,
            'bitstamp': 1000,
            'gemini': 500,
            'cryptocom': 1000
        }
        
        # Calculate timeframe in minutes
        tf_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '6h': 360, '12h': 720, '1d': 1440
        }
        
        minutes_per_candle = tf_minutes.get(timeframe, 60)
        
        # Calculate chunks based on smallest exchange limit
        min_limit = min(max_limits.values()) - 50  # Safety margin
        chunk_duration_minutes = min_limit * minutes_per_candle
        chunk_duration = timedelta(minutes=chunk_duration_minutes)
        
        # Create chunks going backwards from now
        end_time = datetime.now()
        start_time = end_time - timedelta(days=months_back * 30)
        
        chunks = []
        current_end = end_time
        
        while current_end > start_time:
            current_start = max(current_end - chunk_duration, start_time)
            chunks.append((current_start, current_end))
            current_end = current_start
        
        return chunks
    
    def backfill_symbol_timeframe(self, symbol: str, timeframe: str, 
                                 exchange_name: str, months_back: int = 12) -> Dict[str, Any]:
        """Backfill historical data for specific symbol/timeframe combination"""
        
        self.logger.info(f"📊 Backfilling {symbol} {timeframe} on {exchange_name} ({months_back} months)")
        
        if exchange_name not in self.collector.exchanges:
            return {'error': f'Exchange {exchange_name} not available'}
        
        exchange = self.collector.exchanges[exchange_name]
        
        # Check if timeframe is supported
        if hasattr(exchange, 'timeframes') and exchange.timeframes:
            if timeframe not in exchange.timeframes:
                self.logger.warning(f"{timeframe} not supported on {exchange_name}")
                return {'error': f'Timeframe {timeframe} not supported'}
        
        # Calculate time chunks
        chunks = self.calculate_optimal_chunks(timeframe, months_back)
        
        total_collected = 0
        total_errors = 0
        chunk_results = []
        
        for i, (start_time, end_time) in enumerate(chunks):
            try:
                self.logger.info(f"Chunk {i+1}/{len(chunks)}: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
                
                # Convert to milliseconds
                since = int(start_time.timestamp() * 1000)
                limit = min(1000, int((end_time - start_time).total_seconds() / 60 / 
                                    {'1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, 
                                     '4h': 240, '6h': 360, '12h': 720, '1d': 1440}.get(timeframe, 60)))
                
                # Fetch data with since parameter
                try:
                    ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                    
                    if ohlcv_data:
                        # Insert into database
                        inserted = self.collector._insert_ohlcv_enhanced(
                            exchange_name, symbol, timeframe, ohlcv_data
                        )
                        
                        total_collected += inserted
                        chunk_results.append({
                            'period': f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
                            'records': inserted
                        })
                        
                        self.logger.info(f"✅ Chunk {i+1}: {inserted} records collected")
                    else:
                        self.logger.warning(f"⚠️ Chunk {i+1}: No data returned")
                
                except Exception as e:
                    total_errors += 1
                    self.logger.error(f"❌ Chunk {i+1} failed: {str(e)}")
                
                # Rate limiting between chunks
                time.sleep(self.collector.rate_limits.get(exchange_name, 0.1) * 2)
                
            except Exception as e:
                total_errors += 1
                self.logger.error(f"❌ Chunk {i+1} processing failed: {str(e)}")
        
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'exchange': exchange_name,
            'months_requested': months_back,
            'total_collected': total_collected,
            'total_errors': total_errors,
            'chunks_processed': len(chunks),
            'chunk_results': chunk_results[-5:]  # Last 5 chunks for brevity
        }
        
        self.logger.info(f"🎉 Backfill complete for {symbol} {timeframe} on {exchange_name}: {total_collected:,} records")
        
        return result
    
    def backfill_priority_data(self, months_back: int = 18) -> Dict[str, Any]:
        """Backfill priority symbols and timeframes for ML training"""
        
        self.logger.info(f"🚀 Starting priority data backfill ({months_back} months)")
        
        # Priority timeframes for ML (most important first)
        priority_timeframes = ['1h', '4h', '1d', '15m', '5m']
        
        results = {
            'total_records': 0,
            'total_errors': 0,
            'symbol_results': {},
            'start_time': datetime.now().isoformat()
        }
        
        for symbol in self.priority_symbols:
            symbol_results = {}
            
            for timeframe in priority_timeframes:
                # Use the most reliable exchange for each symbol
                best_exchange = self._get_best_exchange_for_symbol(symbol)
                
                if best_exchange:
                    backfill_result = self.backfill_symbol_timeframe(
                        symbol, timeframe, best_exchange, months_back
                    )
                    
                    symbol_results[timeframe] = backfill_result
                    results['total_records'] += backfill_result.get('total_collected', 0)
                    results['total_errors'] += backfill_result.get('total_errors', 0)
                    
                    # Brief pause between timeframes
                    time.sleep(2)
            
            results['symbol_results'][symbol] = symbol_results
            
            # Longer pause between symbols
            time.sleep(5)
        
        results['end_time'] = datetime.now().isoformat()
        results['duration_minutes'] = (datetime.fromisoformat(results['end_time']) - 
                                     datetime.fromisoformat(results['start_time'])).total_seconds() / 60
        
        self.logger.info(f"🎉 Priority backfill complete! {results['total_records']:,} records collected")
        
        return results
    
    def backfill_extended_data(self, months_back: int = 12) -> Dict[str, Any]:
        """Backfill extended symbols and timeframes"""
        
        extended_symbols = [
            'AVAX/USDT', 'MATIC/USDT', 'LINK/USDT', 'UNI/USDT', 
            'ATOM/USDT', 'ALGO/USDT', 'FTM/USDT'
        ]
        
        extended_timeframes = ['1m', '30m', '6h', '12h']
        
        self.logger.info(f"🔄 Starting extended data backfill ({months_back} months)")
        
        results = {
            'total_records': 0,
            'total_errors': 0,
            'symbol_results': {}
        }
        
        for symbol in extended_symbols:
            symbol_results = {}
            
            for timeframe in extended_timeframes:
                best_exchange = self._get_best_exchange_for_symbol(symbol)
                
                if best_exchange:
                    backfill_result = self.backfill_symbol_timeframe(
                        symbol, timeframe, best_exchange, months_back
                    )
                    
                    symbol_results[timeframe] = backfill_result
                    results['total_records'] += backfill_result.get('total_collected', 0)
                    results['total_errors'] += backfill_result.get('total_errors', 0)
                    
                    time.sleep(1)
            
            results['symbol_results'][symbol] = symbol_results
            time.sleep(3)
        
        return results
    
    def _get_best_exchange_for_symbol(self, symbol: str) -> Optional[str]:
        """Get the best exchange for a specific symbol based on reliability and data availability"""
        
        # Priority order: binanceus (most data) -> coinbase -> kraken
        for exchange_name in ['binanceus', 'coinbase', 'kraken']:
            if exchange_name in self.collector.exchanges:
                exchange = self.collector.exchanges[exchange_name]
                
                # Test if symbol is available
                try:
                    # Quick test fetch
                    test_data = exchange.fetch_ohlcv(symbol, '1h', limit=1)
                    if test_data:
                        return exchange_name
                except:
                    continue
        
        # Fallback to any available exchange
        for exchange_name in self.collector.exchanges.keys():
            try:
                exchange = self.collector.exchanges[exchange_name]
                test_data = exchange.fetch_ohlcv(symbol, '1h', limit=1)
                if test_data:
                    return exchange_name
            except:
                continue
        
        return None
    
    def run_comprehensive_backfill(self) -> Dict[str, Any]:
        """Run comprehensive historical data backfill"""
        
        self.logger.info("🚀 Starting comprehensive historical data backfill")
        
        comprehensive_results = {
            'start_time': datetime.now().isoformat(),
            'phases': {}
        }
        
        # Phase 1: Priority data (18 months)
        self.logger.info("📊 Phase 1: Priority symbols and timeframes (18 months)")
        comprehensive_results['phases']['priority'] = self.backfill_priority_data(months_back=18)
        
        # Phase 2: Extended data (12 months)  
        self.logger.info("📊 Phase 2: Extended symbols and timeframes (12 months)")
        comprehensive_results['phases']['extended'] = self.backfill_extended_data(months_back=12)
        
        # Calculate totals
        total_records = sum(phase.get('total_records', 0) for phase in comprehensive_results['phases'].values())
        total_errors = sum(phase.get('total_errors', 0) for phase in comprehensive_results['phases'].values())
        
        comprehensive_results.update({
            'end_time': datetime.now().isoformat(),
            'total_records': total_records,
            'total_errors': total_errors,
            'success_rate': ((total_records / (total_records + total_errors)) * 100) if (total_records + total_errors) > 0 else 0
        })
        
        self.logger.info(f"🎉 COMPREHENSIVE BACKFILL COMPLETE!")
        self.logger.info(f"📊 Total records collected: {total_records:,}")
        self.logger.info(f"❌ Total errors: {total_errors}")
        self.logger.info(f"✅ Success rate: {comprehensive_results['success_rate']:.1f}%")
        
        return comprehensive_results


def main():
    """Run historical data backfill"""
    backfill = HistoricalDataBackfill()
    
    print("🚀 Historical Data Backfill System")
    print("=" * 50)
    print("This will collect 1-2 years of historical data")
    print("across multiple timeframes and symbols for ML training")
    print("=" * 50)
    
    # Run the comprehensive backfill
    results = backfill.run_comprehensive_backfill()
    
    # Save results to file
    with open('backfill_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Backfill Complete!")
    print(f"📊 Results saved to backfill_results.json")
    print(f"📈 Total records: {results['total_records']:,}")


if __name__ == "__main__":
    main()