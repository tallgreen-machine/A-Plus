#!/usr/bin/env python3
"""
Exchange Data Capabilities Checker
Tests what data types and timeframes are available from our connected exchanges
"""

import sys
import ccxt
from typing import Dict, List
from utils.logger import log as logger

# Add paths for imports
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

def check_exchange_capabilities():
    """Check what data is available from each exchange"""
    
    # Initialize exchanges (same as our collector)
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
            logger.info(f"✅ Initialized {name} exchange")
        except Exception as e:
            logger.error(f"❌ Failed to initialize {name}: {e}")
    
    print("\n" + "="*60)
    print("EXCHANGE DATA CAPABILITIES ANALYSIS")
    print("="*60)
    
    for name, exchange in exchanges.items():
        print(f"\n🏢 {name.upper()}")
        print("-" * 40)
        
        # Basic capabilities
        capabilities = [
            ('OHLCV Candles', 'fetchOHLCV'),
            ('Individual Trades', 'fetchTrades'),
            ('Order Book', 'fetchOrderBook'), 
            ('Single Ticker', 'fetchTicker'),
            ('All Tickers', 'fetchTickers'),
            ('Order Status', 'fetchOrder'),
            ('Open Orders', 'fetchOpenOrders'),
            ('Trading Balance', 'fetchBalance'),
            ('Trading History', 'fetchMyTrades'),
            ('Deposits/Withdrawals', 'fetchDeposits')
        ]
        
        print("📊 DATA TYPES AVAILABLE:")
        for desc, method in capabilities:
            available = exchange.has.get(method, False)
            status = "✅" if available else "❌"
            print(f"  {status} {desc}")
        
        # Timeframes (for OHLCV data)
        if exchange.has.get('fetchOHLCV', False):
            print("\n⏰ TIMEFRAMES SUPPORTED:")
            if hasattr(exchange, 'timeframes') and exchange.timeframes:
                timeframes = exchange.timeframes
                for tf_code, tf_desc in timeframes.items():
                    print(f"  ✅ {tf_code} ({tf_desc})")
            else:
                print("  📝 Standard timeframes (likely 1m, 5m, 15m, 1h, 4h, 1d)")
        
        # Rate limits
        print(f"\n⏱️  RATE LIMIT: {exchange.rateLimit}ms between requests")
        
        # Test actual data availability
        print("\n🧪 TESTING DATA ACCESS:")
        if exchange.has.get('fetchOHLCV', False):
            try:
                # Test different timeframes with BTC/USDT
                test_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
                working_timeframes = []
                
                for tf in test_timeframes:
                    try:
                        if hasattr(exchange, 'timeframes') and tf not in exchange.timeframes:
                            continue
                            
                        test_data = exchange.fetch_ohlcv('BTC/USDT', tf, limit=2)
                        if test_data and len(test_data) > 0:
                            working_timeframes.append(tf)
                            
                    except Exception as e:
                        continue
                
                if working_timeframes:
                    print(f"  ✅ Working timeframes: {', '.join(working_timeframes)}")
                else:
                    print("  ❌ No timeframes working for BTC/USDT")
                    
            except Exception as e:
                print(f"  ❌ OHLCV test failed: {str(e)[:100]}...")
        
        # Test ticker data
        if exchange.has.get('fetchTicker', False):
            try:
                ticker = exchange.fetch_ticker('BTC/USDT')
                print(f"  ✅ Ticker data: ${ticker['last']:.2f} (vol: {ticker['baseVolume']:.2f})")
            except Exception as e:
                print(f"  ❌ Ticker test failed: {str(e)[:50]}...")
        
        # Test trades data
        if exchange.has.get('fetchTrades', False):
            try:
                trades = exchange.fetch_trades('BTC/USDT', limit=5)
                if trades:
                    latest_trade = trades[-1]
                    print(f"  ✅ Trades data: Latest ${latest_trade['price']:.2f} ({latest_trade['amount']:.4f} BTC)")
            except Exception as e:
                print(f"  ❌ Trades test failed: {str(e)[:50]}...")

def analyze_current_data():
    """Analyze what we currently have in our database"""
    print("\n" + "="*60)
    print("CURRENT DATABASE DATA ANALYSIS")  
    print("="*60)
    
    try:
        from shared.db import get_db_conn
        conn = get_db_conn()
        cur = conn.cursor()
        
        # Check what we collected
        cur.execute("""
            SELECT 
                symbol,
                exchange, 
                COUNT(*) as records,
                MIN(timestamp) as first_timestamp,
                MAX(timestamp) as last_timestamp
            FROM market_data 
            GROUP BY symbol, exchange 
            ORDER BY records DESC
            LIMIT 15
        """)
        
        print("📈 COLLECTED DATA SUMMARY:")
        for row in cur.fetchall():
            symbol, exchange, records, first_ts, last_ts = row
            
            # Calculate time span and intervals
            if first_ts and last_ts and records > 1:
                duration_seconds = (last_ts - first_ts) / 1000  # Convert from ms
                avg_interval_minutes = (duration_seconds / 60) / (records - 1)
                duration_days = duration_seconds / (24 * 3600)
                
                print(f"  {symbol} on {exchange}: {records:,} records")
                print(f"    📅 Span: {duration_days:.1f} days")
                print(f"    ⏰ Avg interval: {avg_interval_minutes:.0f} minutes")
            else:
                print(f"  {symbol} on {exchange}: {records:,} records (insufficient data for analysis)")
        
        # Check data quality
        print("\n🔍 DATA QUALITY CHECK:")
        cur.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN open IS NULL THEN 1 END) as null_open,
                COUNT(CASE WHEN volume = 0 THEN 1 END) as zero_volume,
                AVG(volume) as avg_volume
            FROM market_data
        """)
        
        total, null_open, zero_vol, avg_vol = cur.fetchone()
        print(f"  📊 Total records: {total:,}")
        print(f"  ❌ Null opens: {null_open}")
        print(f"  📉 Zero volume: {zero_vol}")
        print(f"  📈 Avg volume: {avg_vol:.4f}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database analysis failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Exchange Data Capabilities Analysis...")
    
    try:
        check_exchange_capabilities()
        analyze_current_data()
        
        print("\n" + "="*60)
        print("✅ ANALYSIS COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()