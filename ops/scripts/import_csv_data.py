import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ops/scripts/import_csv_data.py
import pandas as pd
from shared.db import get_db_conn
import os
from dotenv import load_dotenv

def import_data_from_csv(filename, conn):
    """Imports market data from a CSV file into the database."""
    df = pd.read_csv(filename)
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO market_data (symbol, ts, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, ts) DO NOTHING;
            """, (row['symbol'], row['ts'], row['open'], row['high'], row['low'], row['close'], row['volume']))
    print(f"Imported {len(df)} rows into market_data.")

if __name__ == "__main__":
    print("Importing market data from CSV...")
    
    # Load environment variables from the server's config file
    if os.path.exists("/etc/aplus/aplus.env"):
        load_dotenv("/etc/aplus/aplus.env", override=True)

    conn = get_db_conn()
    
    import_data_from_csv("/srv/aplus/market_data.csv", conn)
    conn.close()
    print("Import complete.")
