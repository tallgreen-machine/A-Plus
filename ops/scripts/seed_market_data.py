# ops/scripts/seed_market_data.py
import pandas as pd
import ccxt
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Explicitly load the server's environment file
if os.path.exists("/etc/trad/trad.env"):
    load_dotenv("/etc/trad/trad.env")

def fetch_historical_data(symbol='BTC/USD', timeframe='1h', limit=1000):
    """Fetches historical OHLCV data from Kraken."""
    exchange = ccxt.kraken()
    since = exchange.parse8601((datetime.utcnow() - timedelta(days=limit)).isoformat())
    data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
    df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df['symbol'] = symbol.replace('/', '') # Use consistent symbol format
    return df

def save_data_to_csv(df, filename="market_data.csv"):
    """Saves a DataFrame of market data to a CSV file."""
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} rows to {filename}")

if __name__ == "__main__":
    print("Fetching historical market data...")

    # This script is now only for local execution to generate the CSV.
    # It does not need database credentials.
    
    btc_data = fetch_historical_data(symbol='BTC/USD', timeframe='1h', limit=1000)
    save_data_to_csv(btc_data)
    print("Fetching complete.")
