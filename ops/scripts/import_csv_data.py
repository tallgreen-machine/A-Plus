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
    if os.path.exists("/etc/trad/trad.env"):
        load_dotenv("/etc/trad/trad.env", override=True)

    conn = get_db_conn()
    
    import_data_from_csv("/srv/trad/market_data.csv", conn)
    conn.close()
    print("Import complete.")
