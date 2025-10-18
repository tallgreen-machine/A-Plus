from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from shared.db import get_db_conn


def get_recent_news(symbol: str | None = None, lookback_hours: int = 24) -> List[Dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            if symbol:
                cur.execute(
                    """
                    SELECT ts, source, symbol, sentiment_score, topic, summary
                    FROM news_sentiment
                    WHERE ts >= %s AND symbol = %s
                    ORDER BY ts DESC
                    LIMIT 200
                    """,
                    (cutoff, symbol),
                )
            else:
                cur.execute(
                    """
                    SELECT ts, source, symbol, sentiment_score, topic, summary
                    FROM news_sentiment
                    WHERE ts >= %s
                    ORDER BY ts DESC
                    LIMIT 200
                    """,
                    (cutoff,),
                )
            return cur.fetchall()


essential_metrics = (
    "active_addresses",
    "tx_count",
    "fees",
    "tvl",
)


def get_onchain_stats(chain: str, metrics: List[str] | None = None, lookback_hours: int = 24):
    metrics = metrics or list(essential_metrics)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chain, metric, ts, value
                FROM onchain_data
                WHERE chain = %s AND metric = ANY(%s) AND ts >= %s
                ORDER BY ts DESC
                LIMIT 1000
                """,
                (chain, metrics, cutoff),
            )
            return cur.fetchall()


def get_price_snapshot(symbols: List[str], window: int = 200, timeframe_minutes: int = 5):
    # timeframe is informational; table stores aggregated candles
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            results = {}
            for sym in symbols:
                cur.execute(
                    """
                    SELECT ts, open, high, low, close, volume
                    FROM market_data
                    WHERE symbol = %s
                    ORDER BY ts DESC
                    LIMIT %s
                    """,
                    (sym, window),
                )
                rows = cur.fetchall()
                results[sym] = list(reversed(rows))  # oldest first
            return results
