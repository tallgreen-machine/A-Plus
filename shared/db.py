import os
from pathlib import Path
import psycopg2
import psycopg2.extras
try:
  from dotenv import load_dotenv  # type: ignore
except Exception:
  load_dotenv = None


# Attempt to load environment from common locations once at import time
def _load_env():
  if load_dotenv is None:
    return
  # Look for config/.env relative to project root and this file's location
  candidates = [
    Path("config/.env"),
    Path(__file__).resolve().parent.parent / "config/.env",
    Path("/etc/aplus/.env"),
    Path("/etc/aplus/aplus.env"),
  ]
  for c in candidates:
    if c.exists():
      # Do not override already-set env vars
      load_dotenv(dotenv_path=str(c), override=False)
      break


_load_env()


def get_db_conn(host=None, port=None, name=None, user=None, password=None):
    """Create a psycopg2 connection using env vars or provided arguments."""
    host = host or os.getenv("DB_HOST", "127.0.0.1") # Default to IPv4 loopback
    port = port or int(os.getenv("DB_PORT", "5432"))
    name = name or os.getenv("DB_NAME", "aplus")
    user = user or os.getenv("DB_USER", "aplususer")
    password = password or os.getenv("DB_PASSWORD", "APLUS123!")

    if not password:
        raise ValueError("DB_PASSWORD is not set.")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=name,
        user=user,
        password=password,
        cursor_factory=psycopg2.extras.DictCursor,
        connect_timeout=5  # Add a 5-second timeout
    )
    conn.autocommit = True
    return conn
        password=password,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = True
    return conn
