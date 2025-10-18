#!/usr/bin/env python3
"""
Backfill OHLCV candles from Kraken into market_data via ccxt.
Run multiple times to extend history. Uses 1m or 5m timeframe.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import ccxt

from shared.db import get_db_conn
from dotenv import load_dotenv


def get_exchange():
    # Load config/.env if present
    load_dotenv(os.getenv("ENV_FILE", os.path.join(os.path.dirname(__file__), "..", "config", ".env")))
    api_key = os.getenv("KRAKEN_API_KEY", "")
    api_secret = os.getenv("KRAKEN_API_SECRET", "")
    exchange = ccxt.kraken({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
    })
    return exchange


def resolve_symbol(ex: ccxt.Exchange, desired: str) -> str:
    ex.load_markets()
    if desired in ex.symbols:
        return desired
    # Try common Kraken aliases
    candidates = []
    base, quote = desired.split('/') if '/' in desired else (desired, 'USDT')
    base_alts = [base, base.replace('BTC', 'XBT'), base.replace('XBT', 'BTC'), base.upper()]
    quote_alts = [quote, quote.replace('USDT', 'USD'), quote.upper()]
    for b in base_alts:
        for q in quote_alts:
            candidates.append(f"{b}/{q}")
    for c in candidates:
        if c in ex.symbols:
            return c
    # Fallback to a close match by base token
    for s in ex.symbols:
        if base in s or base.replace('BTC', 'XBT') in s:
            return s
    raise ccxt.BadSymbol(f"No suitable symbol found for {desired} on {ex.id}")


def store_ohlcv(symbol: str, candles, timeframe: str):
    # ccxt ohlcv: [timestamp, open, high, low, close, volume]
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            for c in candles:
                ts = datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc)
                cur.execute(
                    """
                    INSERT INTO market_data (symbol, ts, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, ts) DO UPDATE SET
                      open = EXCLUDED.open,
                      high = EXCLUDED.high,
                      low = EXCLUDED.low,
                      close = EXCLUDED.close,
                      volume = EXCLUDED.volume
                    """,
                    (symbol, ts, c[1], c[2], c[3], c[4], c[5]),
                )


def get_last_ts(symbol: str):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ts FROM market_data WHERE symbol = %s ORDER BY ts DESC LIMIT 1", (symbol,))
            row = cur.fetchone()
            if not row:
                return None
            return row["ts"] if isinstance(row, dict) else row[0]


def backfill(symbol: str, timeframe: str = "5m", limit: int = 500):
    ex = get_exchange()
    resolved = resolve_symbol(ex, symbol)
    print(f"Backfilling {symbol} as {resolved} on {ex.id}")
    since_dt = get_last_ts(symbol)
    since_ms = int(since_dt.timestamp() * 1000) if since_dt else None

    while True:
        candles = ex.fetch_ohlcv(resolved, timeframe=timeframe, since=since_ms, limit=limit)
        if not candles:
            break
        store_ohlcv(symbol, candles, timeframe)
        if len(candles) < limit:
            break
        since_ms = candles[-1][0] + 1
        time.sleep(ex.rateLimit / 1000.0)


if __name__ == "__main__":
    # Kraken symbols example: 'BTC/USDT', 'ETH/USDT'
    for sym in ("BTC/USDT", "ETH/USDT"):
        backfill(sym, timeframe="5m", limit=500)
    print("Backfill complete")
