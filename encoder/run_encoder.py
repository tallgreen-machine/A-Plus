#!/usr/bin/env python3
"""
Stub encoder runner: loads last N candles per symbol, computes a dummy embedding,
then upserts into current_embeddings. Replace feature engineering and model inference.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import psycopg2

from shared.db import get_db_conn
from shared.logging import setup_logger

logger = setup_logger("encoder")

WINDOW = 200
FEATURES = ["open", "high", "low", "close", "volume"]  # extend with engineered features


def get_symbols(limit: int = 10):
    # Infer symbols from market_data
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT symbol FROM market_data LIMIT %s", (limit,))
            rows = cur.fetchall()
            return [r["symbol"] if isinstance(r, dict) else r[0] for r in rows]


def get_recent_candles(symbol: str, window: int = WINDOW):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts, open, high, low, close, volume
                FROM market_data
                WHERE symbol = %s
                ORDER BY ts DESC
                LIMIT %s
                """,
                (symbol, window),
            )
            rows = cur.fetchall()
            rows = list(reversed(rows))
            return rows


def compute_dummy_embedding(rows):
    # Very naive placeholder: use simple stats to build a fixed-size vector
    if not rows:
        return np.zeros(128, dtype=np.float32)
    closes = np.array([float(r["close"] if isinstance(r, dict) else r[5]) for r in rows], dtype=np.float32)
    vols = np.array([float(r["volume"] if isinstance(r, dict) else r[6]) for r in rows], dtype=np.float32)
    feat = np.concatenate([
        np.array([closes.mean(), closes.std() + 1e-6, closes[-1] - closes[0]], dtype=np.float32),
        np.array([vols.mean(), vols.std() + 1e-6], dtype=np.float32),
        np.zeros(123, dtype=np.float32),
    ])
    return feat


def upsert_embedding(symbol: str, ts: datetime, emb: np.ndarray):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO current_embeddings (symbol, ts, embedding, meta)
                VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (symbol, ts) DO UPDATE SET
                  embedding = EXCLUDED.embedding,
                  meta = EXCLUDED.meta
                """,
                (symbol, ts, emb.tolist(), json.dumps({"window": WINDOW, "timeframe": "5m"})),
            )


def main():
    symbols = get_symbols()
    if not symbols:
        logger.info("No symbols found in market_data; encoder did nothing")
        return
    for sym in symbols:
        rows = get_recent_candles(sym)
        if not rows:
            continue
        ts = rows[-1]["ts"] if isinstance(rows[-1], dict) else rows[-1][0]
        emb = compute_dummy_embedding(rows)
        upsert_embedding(sym, ts, emb)
        logger.info("embedding upserted", extra={"symbol": sym, "ts": str(ts)})


if __name__ == "__main__":
    main()
