import os
from pathlib import Path
import psycopg2
import psycopg2.extras
try:
  from dotenv import load_dotenv  # type: ignore
except Exception:
  load_dotenv = None


# Attempt to load environment from config/.env once at import time
def _load_env():
  if load_dotenv is None:
    return
  # Look for config/.env relative to project root and this file's location
  candidates = [
    Path("config/.env"),
    Path(__file__).resolve().parent.parent / "config/.env",
  ]
  for c in candidates:
    if c.exists():
      # Do not override already-set env vars
      load_dotenv(dotenv_path=str(c), override=False)
      break


_load_env()


def get_db_conn():
    """Create a psycopg2 connection using env vars.

    Required env vars (with defaults for local dev):
      - DB_HOST (default: localhost)
      - DB_PORT (default: 5432)
      - DB_NAME (default: trad)
      - DB_USER (default: trad)
      - DB_PASSWORD (default: tradpassword)
    """
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    name = os.getenv("DB_NAME", "trad")
    user = os.getenv("DB_USER", "trad")
    password = os.getenv("DB_PASSWORD", "tradpassword")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=name,
        user=user,
        password=password,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = True
    return conn
