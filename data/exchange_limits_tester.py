#!/usr/bin/env python3
"""
Exchange Capabilities and Limits Tester

Tests each exchange to discover:
- Maximum candles per request
- Rate limits (actual vs documented)
- Historical depth (how far back data goes)
- Timeframe availability
- Symbol support per timeframe

Output: JSON + Markdown reports with concrete limits for optimization
"""

import sys
import os
import ccxt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json

# Add paths for imports
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

from utils.logger import log as logger


class ExchangeLimitsTester:
    """
    Test exchange capabilities to optimize data collection.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Exchanges to test
        self.exchange_names = [
            'binanceus',
            'coinbase', 
            'kraken',
            'bitstamp',
            'gemini',
            'cryptocom'
        ]
        
        # Test symbols (pick most liquid)
        self.test_symbols = [
            'BTC/USDT',
            'ETH/USDT',
            'SOL/USDT'
        ]
        
        # Test timeframes
        self.test_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        # Results storage
        self.results = {}
        
    def initialize_exchange(self, exchange_name: str) -> Optional[ccxt.Exchange]:
        """Initialize a single exchange"""
        try:
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({
                'enableRateLimit': True,
                'timeout': 30000
            })
            exchange.load_markets()
            self.logger.info(f"✅ Initialized {exchange_name}")
            return exchange
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize {exchange_name}: {e}")
            return None
    
    def test_max_candles_per_request(self, exchange: ccxt.Exchange, 
                                     exchange_name: str, 
                                     symbol: str, 
                                     timeframe: str) -> Dict[str, Any]:
        """
        Test maximum candles we can fetch in a single request.
        Try: 100, 500, 1000, 5000, 10000
        """
        self.logger.info(f"  Testing max candles for {exchange_name} {symbol} {timeframe}")
        
        test_limits = [100, 500, 1000, 5000, 10000]
        max_working = 0
        
        # Use recent data (last 7 days) to avoid historical depth issues
        since = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
        
        for limit in test_limits:
            try:
                start_time = time.time()
                data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                elapsed = time.time() - start_time
                
                if data and len(data) > 0:
                    max_working = limit
                    self.logger.info(f"    ✅ {limit} candles: {len(data)} received in {elapsed:.2f}s")
                    time.sleep(0.5)  # Brief pause between tests
                else:
                    self.logger.warning(f"    ⚠️ {limit} candles: No data received")
                    break
                    
            except Exception as e:
                self.logger.warning(f"    ❌ {limit} candles failed: {str(e)[:100]}")
                break
        
        return {
            'max_candles_per_request': max_working,
            'tested_limits': test_limits[:test_limits.index(max_working)+1] if max_working > 0 else []
        }
    
    def test_rate_limit(self, exchange: ccxt.Exchange, 
                       exchange_name: str,
                       symbol: str,
                       timeframe: str) -> Dict[str, Any]:
        """
        Test actual rate limit by making rapid requests and measuring throttling.
        """
        self.logger.info(f"  Testing rate limit for {exchange_name} {symbol} {timeframe}")
        
        num_requests = 10
        since = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        
        start_time = time.time()
        successful_requests = 0
        errors = []
        
        for i in range(num_requests):
            try:
                exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=100)
                successful_requests += 1
            except Exception as e:
                error_msg = str(e)[:100]
                errors.append(error_msg)
                if 'rate limit' in error_msg.lower():
                    self.logger.info(f"    ⚠️ Hit rate limit at request {i+1}")
                    break
        
        elapsed = time.time() - start_time
        requests_per_second = successful_requests / elapsed if elapsed > 0 else 0
        avg_delay = elapsed / successful_requests if successful_requests > 0 else 0
        
        self.logger.info(f"    📊 {successful_requests}/{num_requests} successful")
        self.logger.info(f"    ⚡ {requests_per_second:.2f} requests/sec")
        self.logger.info(f"    ⏱️ {avg_delay:.3f}s avg delay between requests")
        
        return {
            'successful_requests': successful_requests,
            'total_attempts': num_requests,
            'total_time_seconds': elapsed,
            'requests_per_second': requests_per_second,
            'avg_delay_seconds': avg_delay,
            'rate_limit_errors': len([e for e in errors if 'rate limit' in e.lower()])
        }
    
    def test_historical_depth(self, exchange: ccxt.Exchange,
                             exchange_name: str,
                             symbol: str,
                             timeframe: str) -> Dict[str, Any]:
        """
        Test how far back we can fetch data.
        Binary search backwards from now until we hit the limit.
        """
        self.logger.info(f"  Testing historical depth for {exchange_name} {symbol} {timeframe}")
        
        # Start with reasonable bounds
        max_days_back = 3650  # 10 years
        min_days_back = 0
        
        oldest_data = None
        newest_data = None
        
        # First, get the newest data
        try:
            data = exchange.fetch_ohlcv(symbol, timeframe, limit=1)
            if data:
                newest_data = datetime.fromtimestamp(data[0][0] / 1000)
        except:
            pass
        
        # Binary search for oldest available data
        attempts = 0
        max_attempts = 10
        
        while min_days_back < max_days_back and attempts < max_attempts:
            attempts += 1
            test_days = (min_days_back + max_days_back) // 2
            test_date = datetime.now() - timedelta(days=test_days)
            since = int(test_date.timestamp() * 1000)
            
            try:
                data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=10)
                
                if data and len(data) > 0:
                    # We got data this far back, try going further
                    oldest_data = datetime.fromtimestamp(data[0][0] / 1000)
                    max_days_back = test_days + (max_days_back - test_days) // 2
                    self.logger.info(f"    ✅ Data available at {test_days} days back ({oldest_data.strftime('%Y-%m-%d')})")
                else:
                    # No data this far back, try more recent
                    min_days_back = test_days
                    self.logger.info(f"    ⚠️ No data at {test_days} days back")
                
                time.sleep(0.3)  # Brief pause between tests
                
            except Exception as e:
                self.logger.warning(f"    ❌ Error testing {test_days} days back: {str(e)[:100]}")
                min_days_back = test_days
                time.sleep(0.5)
        
        # Make one final request at the discovered limit
        if oldest_data:
            try:
                since = int(oldest_data.timestamp() * 1000)
                data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=100)
                if data:
                    oldest_data = datetime.fromtimestamp(data[0][0] / 1000)
            except:
                pass
        
        days_available = (datetime.now() - oldest_data).days if oldest_data else 0
        
        result = {
            'oldest_date': oldest_data.isoformat() if oldest_data else None,
            'newest_date': newest_data.isoformat() if newest_data else None,
            'days_available': days_available,
            'years_available': round(days_available / 365.25, 2),
            'search_attempts': attempts
        }
        
        if oldest_data:
            self.logger.info(f"    📅 Available from {oldest_data.strftime('%Y-%m-%d')} to {newest_data.strftime('%Y-%m-%d') if newest_data else 'now'}")
            self.logger.info(f"    📊 {days_available} days ({result['years_available']} years)")
        
        return result
    
    def test_timeframe_support(self, exchange: ccxt.Exchange,
                               exchange_name: str,
                               symbol: str) -> Dict[str, Any]:
        """
        Test which timeframes are actually supported for a symbol.
        """
        self.logger.info(f"  Testing timeframe support for {exchange_name} {symbol}")
        
        supported = []
        unsupported = []
        
        # Check exchange's declared timeframes
        declared_timeframes = []
        if hasattr(exchange, 'timeframes') and exchange.timeframes:
            declared_timeframes = list(exchange.timeframes.keys())
        
        # Test each timeframe
        for tf in self.test_timeframes:
            try:
                since = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
                data = exchange.fetch_ohlcv(symbol, tf, since=since, limit=10)
                
                if data and len(data) > 0:
                    supported.append(tf)
                    self.logger.info(f"    ✅ {tf}: Supported ({len(data)} candles)")
                else:
                    unsupported.append(tf)
                    self.logger.warning(f"    ⚠️ {tf}: No data")
                
                time.sleep(0.3)
                
            except Exception as e:
                unsupported.append(tf)
                self.logger.warning(f"    ❌ {tf}: {str(e)[:80]}")
                time.sleep(0.3)
        
        return {
            'declared_timeframes': declared_timeframes,
            'supported_timeframes': supported,
            'unsupported_timeframes': unsupported,
            'coverage_percent': len(supported) / len(self.test_timeframes) * 100
        }
    
    def test_symbol_availability(self, exchange: ccxt.Exchange,
                                 exchange_name: str) -> Dict[str, Any]:
        """
        Test which of our target symbols are available.
        """
        self.logger.info(f"  Testing symbol availability for {exchange_name}")
        
        available = []
        unavailable = []
        
        for symbol in self.test_symbols:
            if symbol in exchange.markets:
                available.append(symbol)
                self.logger.info(f"    ✅ {symbol}: Available")
            else:
                unavailable.append(symbol)
                self.logger.warning(f"    ⚠️ {symbol}: Not available")
        
        return {
            'available_symbols': available,
            'unavailable_symbols': unavailable,
            'coverage_percent': len(available) / len(self.test_symbols) * 100
        }
    
    def test_exchange(self, exchange_name: str) -> Dict[str, Any]:
        """
        Run full test suite on one exchange.
        """
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"🔍 TESTING {exchange_name.upper()}")
        self.logger.info(f"{'='*70}\n")
        
        exchange = self.initialize_exchange(exchange_name)
        if not exchange:
            return {'error': 'Failed to initialize exchange'}
        
        result = {
            'exchange': exchange_name,
            'test_timestamp': datetime.now().isoformat(),
            'symbol_availability': {},
            'timeframe_tests': {},
            'rate_limit_tests': {},
            'historical_depth_tests': {},
            'max_candles_tests': {}
        }
        
        # Test symbol availability
        result['symbol_availability'] = self.test_symbol_availability(exchange, exchange_name)
        available_symbols = result['symbol_availability']['available_symbols']
        
        if not available_symbols:
            self.logger.warning(f"⚠️ No test symbols available on {exchange_name}")
            return result
        
        # Use first available symbol for detailed tests
        test_symbol = available_symbols[0]
        
        # Test timeframe support
        result['timeframe_tests'] = self.test_timeframe_support(exchange, exchange_name, test_symbol)
        supported_timeframes = result['timeframe_tests']['supported_timeframes']
        
        if not supported_timeframes:
            self.logger.warning(f"⚠️ No timeframes supported for {test_symbol} on {exchange_name}")
            return result
        
        # Use first supported timeframe for rate and depth tests
        test_timeframe = supported_timeframes[0]
        
        # Test rate limit
        result['rate_limit_tests'] = self.test_rate_limit(
            exchange, exchange_name, test_symbol, test_timeframe
        )
        
        # Test max candles per request
        result['max_candles_tests'] = self.test_max_candles_per_request(
            exchange, exchange_name, test_symbol, test_timeframe
        )
        
        # Test historical depth for each supported timeframe
        result['historical_depth_tests'] = {}
        for tf in supported_timeframes[:3]:  # Test first 3 timeframes to save time
            result['historical_depth_tests'][tf] = self.test_historical_depth(
                exchange, exchange_name, test_symbol, tf
            )
            time.sleep(1)  # Pause between depth tests
        
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run tests on all exchanges.
        """
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 EXCHANGE CAPABILITIES TESTING SUITE")
        self.logger.info("="*70)
        self.logger.info(f"Testing {len(self.exchange_names)} exchanges")
        self.logger.info(f"Test symbols: {', '.join(self.test_symbols)}")
        self.logger.info(f"Test timeframes: {', '.join(self.test_timeframes)}")
        self.logger.info("="*70 + "\n")
        
        start_time = datetime.now()
        results = {
            'test_start': start_time.isoformat(),
            'exchanges': {}
        }
        
        for exchange_name in self.exchange_names:
            try:
                exchange_result = self.test_exchange(exchange_name)
                results['exchanges'][exchange_name] = exchange_result
                
                # Brief pause between exchanges
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"❌ Failed to test {exchange_name}: {e}")
                results['exchanges'][exchange_name] = {'error': str(e)}
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results['test_end'] = end_time.isoformat()
        results['duration_minutes'] = duration / 60
        
        self.logger.info("\n" + "="*70)
        self.logger.info("✅ TESTING COMPLETE")
        self.logger.info("="*70)
        self.logger.info(f"Duration: {duration/60:.1f} minutes")
        self.logger.info("="*70 + "\n")
        
        return results
    
    def generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """
        Generate a human-readable markdown report.
        """
        report = []
        report.append("# Exchange Capabilities Test Report")
        report.append(f"\n**Generated:** {results['test_start']}")
        report.append(f"**Duration:** {results['duration_minutes']:.1f} minutes\n")
        
        report.append("## Executive Summary\n")
        
        # Summary table
        report.append("| Exchange | Symbols | Timeframes | Max Candles | Rate (req/s) | Max History |")
        report.append("|----------|---------|------------|-------------|--------------|-------------|")
        
        for exchange_name, data in results['exchanges'].items():
            if 'error' in data:
                report.append(f"| {exchange_name} | ❌ ERROR | - | - | - | - |")
                continue
            
            symbols = f"{len(data['symbol_availability']['available_symbols'])}/{len(self.test_symbols)}"
            timeframes = f"{len(data['timeframe_tests']['supported_timeframes'])}/{len(self.test_timeframes)}"
            max_candles = data['max_candles_tests'].get('max_candles_per_request', 'N/A')
            rate = f"{data['rate_limit_tests'].get('requests_per_second', 0):.2f}"
            
            # Get max history from historical depth tests
            max_years = 0
            if 'historical_depth_tests' in data:
                for tf_data in data['historical_depth_tests'].values():
                    if tf_data.get('years_available', 0) > max_years:
                        max_years = tf_data['years_available']
            
            history = f"{max_years:.1f}y" if max_years > 0 else "N/A"
            
            report.append(f"| {exchange_name} | {symbols} | {timeframes} | {max_candles} | {rate} | {history} |")
        
        report.append("\n## Detailed Findings\n")
        
        for exchange_name, data in results['exchanges'].items():
            report.append(f"### {exchange_name.upper()}\n")
            
            if 'error' in data:
                report.append(f"❌ **Error:** {data['error']}\n")
                continue
            
            # Symbol availability
            report.append("**Symbol Availability:**")
            if data['symbol_availability']['available_symbols']:
                report.append(f"- ✅ Available: {', '.join(data['symbol_availability']['available_symbols'])}")
            if data['symbol_availability']['unavailable_symbols']:
                report.append(f"- ❌ Unavailable: {', '.join(data['symbol_availability']['unavailable_symbols'])}")
            report.append("")
            
            # Timeframe support
            report.append("**Timeframe Support:**")
            if data['timeframe_tests']['supported_timeframes']:
                report.append(f"- ✅ Supported: {', '.join(data['timeframe_tests']['supported_timeframes'])}")
            if data['timeframe_tests']['unsupported_timeframes']:
                report.append(f"- ❌ Unsupported: {', '.join(data['timeframe_tests']['unsupported_timeframes'])}")
            report.append("")
            
            # Rate limits
            report.append("**Rate Limits:**")
            rate_data = data['rate_limit_tests']
            report.append(f"- Requests per second: **{rate_data['requests_per_second']:.2f}**")
            report.append(f"- Average delay: {rate_data['avg_delay_seconds']:.3f}s")
            report.append(f"- Success rate: {rate_data['successful_requests']}/{rate_data['total_attempts']}")
            report.append("")
            
            # Max candles
            report.append("**Max Candles Per Request:**")
            max_candles = data['max_candles_tests']['max_candles_per_request']
            report.append(f"- **{max_candles}** candles per request")
            report.append("")
            
            # Historical depth
            report.append("**Historical Data Depth:**")
            if 'historical_depth_tests' in data:
                for tf, depth_data in data['historical_depth_tests'].items():
                    if depth_data.get('oldest_date'):
                        report.append(f"- {tf}: **{depth_data['years_available']:.1f} years** ({depth_data['days_available']} days)")
                        report.append(f"  - From {depth_data['oldest_date'][:10]} to {depth_data['newest_date'][:10] if depth_data['newest_date'] else 'now'}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Run the exchange capabilities tests"""
    print("\n" + "="*70)
    print("🔍 EXCHANGE CAPABILITIES TESTER")
    print("="*70)
    print("This will test each exchange to discover:")
    print("  - Maximum candles per request")
    print("  - Rate limits (requests per second)")
    print("  - Historical depth (how far back data goes)")
    print("  - Timeframe and symbol support")
    print("")
    print("Estimated time: 20-30 minutes")
    print("="*70 + "\n")
    
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    print("\n🚀 Starting tests...\n")
    
    tester = ExchangeLimitsTester()
    results = tester.run_all_tests()
    
    # Save JSON results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f'exchange_limits_test_{timestamp}.json'
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ JSON results saved to {json_file}")
    
    # Generate and save markdown report
    report = tester.generate_markdown_report(results)
    md_file = f'exchange_limits_report_{timestamp}.md'
    with open(md_file, 'w') as f:
        f.write(report)
    
    print(f"✅ Markdown report saved to {md_file}")
    print("\n📊 Quick Summary:")
    print(report.split("## Executive Summary")[1].split("## Detailed")[0])
    print("\n🎉 DONE! Check the reports for detailed findings.")


if __name__ == "__main__":
    main()
