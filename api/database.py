import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

def get_database():
    """Get database connection with proper error handling"""
    try:
        # Use the same configuration as the existing shared/db.py
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'trad'),
            user=os.getenv('DB_USER', 'traduser'),
            password=os.getenv('DB_PASSWORD', 'TRAD123!'),
            cursor_factory=RealDictCursor
        )
        connection.autocommit = True
        return connection
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise