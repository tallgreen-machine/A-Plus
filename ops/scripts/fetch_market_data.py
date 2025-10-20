import os
import ccxt
import psycopg2
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='config/trad.env')

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )

def insert_market_data(conn, exchange_id, symbol, ohlcv):
    """Inserts OHLCV data into the market_data table."""
    with conn.cursor() as cur:
        for candle in ohlcv:
            timestamp, open_price, high, low, close, volume = candle
            cur.execute(
                """
                INSERT INTO market_data (exchange, symbol, timestamp, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exchange, symbol, timestamp) DO NOTHING;
                """,
                (exchange_id, symbol, timestamp, open_price, high, low, close, volume)
            )
    conn.commit()

def fetch_and_store_data(exchange_id, symbol='BTC/USDT', timeframe='1h', limit=100):
    """Fetches historical OHLCV data and stores it in the database."""
    print(f"Fetching data for {symbol} from {exchange_id}...")
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()
        if exchange.has['fetchOHLCV']:
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Connect to DB and insert data
            with get_db_connection() as conn:
                insert_market_data(conn, exchange_id, symbol, ohlcv)
            
            print(f"✅ Successfully fetched and stored {len(ohlcv)} candles for {symbol} from {exchange_id}.")
        else:
            print(f"⚠️ {exchange_id} does not support fetchOHLCV.")
    except (ccxt.BadSymbol, ccxt.NetworkError, ccxt.ExchangeError) as e:
        print(f"❌ Could not fetch {symbol} from {exchange_id}: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred with {exchange_id}: {e}")


def main():
    """Main function to orchestrate data fetching."""
    exchanges = [
        'binanceus',
        'bitstamp',
        'coinbase',
        'cryptocom',
        'gemini',
        'kraken',
    ]
    
    for exchange in exchanges:
        # Most exchanges use BTC/USDT, but some might use BTC/USD
        try:
            fetch_and_store_data(exchange, symbol='BTC/USDT')
        except ccxt.BadSymbol:
            print(f"BTC/USDT not found on {exchange}, trying BTC/USD...")
            fetch_and_store_data(exchange, symbol='BTC/USD')
        time.sleep(1) # Be respectful of API rate limits

if __name__ == "__main__":
    main()
