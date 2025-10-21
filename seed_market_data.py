#!/usr/bin/env python3
"""
Market Data Seeder for ML Training
Populates the market_data table with realistic OHLCV data for training
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import random
import math

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "trad"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password")
    )

def generate_realistic_ohlcv(symbol, start_price, num_candles=2000):
    """Generate realistic OHLCV data for a symbol"""
    data = []
    current_price = start_price
    current_time = datetime.now() - timedelta(hours=num_candles)
    
    # Symbol-specific parameters
    if "BTC" in symbol:
        volatility = 0.02  # 2% average movement
        volume_base = 1000000
    elif "ETH" in symbol:
        volatility = 0.025  # 2.5% average movement
        volume_base = 800000
    elif "SOL" in symbol:
        volatility = 0.035  # 3.5% average movement
        volume_base = 500000
    else:
        volatility = 0.03
        volume_base = 300000
    
    for i in range(num_candles):
        # Generate price movement (random walk with drift)
        price_change = random.gauss(0, volatility)
        drift = 0.0001  # Slight upward drift
        
        # Apply change
        new_price = current_price * (1 + price_change + drift)
        
        # Generate OHLC for this candle
        price_range = abs(new_price - current_price)
        
        if new_price > current_price:  # Bullish candle
            open_price = current_price
            close_price = new_price
            high_price = close_price + random.uniform(0, price_range * 0.3)
            low_price = open_price - random.uniform(0, price_range * 0.2)
        else:  # Bearish candle
            open_price = current_price
            close_price = new_price
            high_price = open_price + random.uniform(0, price_range * 0.2)
            low_price = close_price - random.uniform(0, price_range * 0.3)
        
        # Ensure prices are positive and logical
        low_price = max(0.01, low_price)
        high_price = max(high_price, max(open_price, close_price))
        
        # Generate volume (higher volume on bigger moves)
        volume_multiplier = 1 + abs(price_change) * 10
        volume = int(volume_base * volume_multiplier * random.uniform(0.5, 2.0))
        
        data.append({
            'timestamp': int((current_time + timedelta(hours=i)).timestamp()),
            'symbol': symbol,
            'exchange': 'binance',  # Default exchange
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
        current_price = close_price
    
    return data

def seed_market_data():
    """Seed the database with market data for training"""
    print("🚀 Starting market data seeding...")
    
    conn = get_db_connection()
    
    # Symbols to generate data for
    symbols_data = {
        'BTC/USDT': 45000,  # Starting price
        'ETH/USDT': 3100,
        'SOL/USDT': 110,
        'ADA/USDT': 0.45,
        'DOT/USDT': 6.50
    }
    
    try:
        with conn.cursor() as cur:
            # Clear existing data
            print("🧹 Clearing existing market data...")
            cur.execute("DELETE FROM market_data")
            
            total_records = 0
            
            for symbol, start_price in symbols_data.items():
                print(f"📊 Generating data for {symbol}...")
                
                # Generate 2000 hourly candles (about 83 days)
                candle_data = generate_realistic_ohlcv(symbol, start_price, 2000)
                
                # Insert data
                for candle in candle_data:
                    cur.execute("""
                        INSERT INTO market_data (timestamp, symbol, exchange, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        candle['timestamp'],
                        candle['symbol'],
                        candle['exchange'],
                        candle['open'],
                        candle['high'],
                        candle['low'],
                        candle['close'],
                        candle['volume']
                    ))
                
                total_records += len(candle_data)
                print(f"✅ Generated {len(candle_data)} candles for {symbol}")
            
            # Commit all data
            conn.commit()
            
            # Verify the data
            cur.execute("SELECT symbol, COUNT(*) as count FROM market_data GROUP BY symbol")
            results = cur.fetchall()
            
            print("\n📈 Market Data Summary:")
            for symbol, count in results:
                cur.execute("""
                    SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest, 
                           MIN(close) as min_price, MAX(close) as max_price
                    FROM market_data WHERE symbol = %s
                """, (symbol,))
                stats = cur.fetchone()
                earliest = datetime.fromtimestamp(stats[0]).strftime('%Y-%m-%d %H:%M')
                latest = datetime.fromtimestamp(stats[1]).strftime('%Y-%m-%d %H:%M')
                print(f"  {symbol}: {count:,} records ({earliest} to {latest})")
                print(f"    Price range: ${stats[2]:.2f} - ${stats[3]:.2f}")
            
            print(f"\n🎉 Successfully seeded {total_records:,} market data records!")
            
    except Exception as e:
        print(f"❌ Error seeding market data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    seed_market_data()