from typing import List, Optional
import json
import psycopg2
import psycopg2.extras

from shared.db import get_db_conn


def save_reflection(strategy_text: str, embedding: list[float], tags: dict | None = None,
                    outcome_text: str | None = None, outcome_metrics: dict | None = None) -> int:
    tags = tags or {}
    outcome_metrics = outcome_metrics or {}
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_logs (strategy_text, strategy_embedding, tags, outcome_text, outcome_metrics)
                VALUES (%s, %s, %s::jsonb, %s, %s::jsonb)
                RETURNING id
                """,
                (strategy_text, embedding, json.dumps(tags), outcome_text, json.dumps(outcome_metrics)),
            )
            row = cur.fetchone()
            return int(row["id"]) if isinstance(row, dict) else int(row[0])


def retrieve_similar_reflections(query_embedding: list[float], k: int = 5):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ts, strategy_text, outcome_text, tags, outcome_metrics
                FROM memory_logs
                ORDER BY strategy_embedding <-> %s
                LIMIT %s
                """,
                (query_embedding, k),
            )
            return cur.fetchall()
