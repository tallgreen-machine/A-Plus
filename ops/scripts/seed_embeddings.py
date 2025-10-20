#!/usr/bin/env python3
"""
Seeds the current_embeddings table with random historical data for testing purposes.
"""
import os
import json
import random
import psycopg2
from datetime import datetime, timedelta

from dotenv import load_dotenv

# Load environment variables from the parent directory's .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'trad.env')
load_dotenv(dotenv_path=dotenv_path)

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None

def seed_embeddings():
    """Generates and inserts random embedding data into the database."""
    conn = get_db_connection()
    if conn is None:
        print("Could not connect to the database. Aborting.")
        return

    symbols = ["BTC/USDT", "ETH/USDT"]
    embedding_dim = 128
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)
    current_time = start_time

    try:
        with conn.cursor() as cur:
            print("Deleting existing embedding data...")
            cur.execute("TRUNCATE TABLE current_embeddings RESTART IDENTITY;")
            print("Existing data deleted.")

            print("Seeding new embedding data...")
            while current_time < end_time:
                for symbol in symbols:
                    # Generate a random embedding vector
                    embedding = [random.uniform(-1, 1) for _ in range(embedding_dim)]
                    embedding_json = json.dumps(embedding)

                    cur.execute(
                        """
                        INSERT INTO current_embeddings (timestamp, symbol, embedding_json, model_id)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (current_time, symbol, embedding_json, 'test_seeder_v1')
                    )
                
                # Move to the next time step (e.g., every 4 hours)
                current_time += timedelta(hours=4)
            
            conn.commit()
            print(f"Successfully seeded embeddings for {len(symbols)} symbols from {start_time} to {end_time}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    seed_embeddings()
