#!/usr/bin/env python3
"""
Stub meta-controller: writes/updates policy_config and market_state with safe defaults.
Replace the decision logic with LLM + LangChain orchestration.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from shared.db import get_db_conn
from shared.logging import setup_logger

logger = setup_logger("meta_controller")


DEFAULT_REWARD_WEIGHTS = {"sharpe": 0.6, "pnl": 0.3, "drawdown": -0.1, "turnover": -0.1}
DEFAULT_RISK_PARAMS = {"max_pos": 0.15, "daily_loss_stop": -0.05, "pause": False}
DEFAULT_STRATEGIES = ["breakout", "mean_revert"]


def upsert_policy_config(reward_weights=None, risk_params=None, active_strategies=None):
    reward_weights = reward_weights or DEFAULT_REWARD_WEIGHTS
    risk_params = risk_params or DEFAULT_RISK_PARAMS
    active_strategies = active_strategies or DEFAULT_STRATEGIES
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO policy_config (id, reward_weights, risk_params, active_strategies, config_version, last_updated)
                VALUES (1, %s::jsonb, %s::jsonb, %s::jsonb, 1, now())
                ON CONFLICT (id) DO UPDATE SET
                  reward_weights = EXCLUDED.reward_weights,
                  risk_params = EXCLUDED.risk_params,
                  active_strategies = EXCLUDED.active_strategies,
                  config_version = policy_config.config_version + 1,
                  last_updated = now()
                RETURNING config_version
                """,
                (json.dumps(reward_weights), json.dumps(risk_params), json.dumps(active_strategies)),
            )
            row = cur.fetchone()
            version = row["config_version"] if isinstance(row, dict) else row[0]
            logger.info("policy_config updated", extra={"config_version": version})
            return version


def upsert_market_state(regime: str = "NEUTRAL", conviction: float = 0.0, details: dict | None = None):
    details = details or {}
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_state (id, current_regime, conviction, details, last_updated)
                VALUES (1, %s, %s, %s::jsonb, now())
                ON CONFLICT (id) DO UPDATE SET
                  current_regime = EXCLUDED.current_regime,
                  conviction = EXCLUDED.conviction,
                  details = EXCLUDED.details,
                  last_updated = now()
                RETURNING last_updated
                """,
                (regime, conviction, json.dumps(details)),
            )
            row = cur.fetchone()
            ts = row["last_updated"] if isinstance(row, dict) else row[0]
            logger.info("market_state updated", extra={"regime": regime, "conviction": conviction, "ts": str(ts)})
            return ts


def main():
    # Placeholder policy: if needed, could read recent performance to adjust knobs
    version = upsert_policy_config()
    upsert_market_state("NEUTRAL", 0.0, {"config_version": version, "note": "stub update"})


if __name__ == "__main__":
    main()
