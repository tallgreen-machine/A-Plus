import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any
import psycopg2
import psycopg2.extras

from shared.db import get_db_conn


class CryptoTradingEnv(gym.Env):
    metadata = {"render.modes": ["human"]}

    def __init__(self, symbols: list[str], window: int = 200):
        super().__init__()
        self.symbols = symbols
        self.window = window
        self.n_assets = len(symbols)
        self._active_patterns = self._load_active_patterns()
        self.known_patterns = ['Liquidity Sweep']  # A registry of all possible patterns

        # Observations: embeddings, weights, cash, regime, conviction, active_patterns
        emb_dim = 128
        patterns_dim = len(self.known_patterns)
        obs_dim = self.n_assets * emb_dim + self.n_assets + 1 + 3 + 1 + patterns_dim
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)

        # Action: target weights per asset in [0,1]; residual goes to cash (long-only)
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(self.n_assets,), dtype=np.float32)

        # State buffers
        self._weights = np.zeros(self.n_assets, dtype=np.float32)
        self._cash = 1.0
        self._last_obs = None

    def _load_active_patterns(self):
        """Loads the active patterns from the JSON file."""
        active_patterns_path = Path('active_patterns.json')
        if not active_patterns_path.exists():
            print("Warning: active_patterns.json not found. No patterns will be used.")
            return []
        try:
            with open(active_patterns_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: active_patterns.json is empty or malformed. No patterns will be used.")
            return []

    def _get_pattern_features(self) -> np.ndarray:
        """Creates a binary vector indicating which known patterns are active."""
        active_pattern_names = {p['name'] for p in self._active_patterns}
        return np.array([1.0 if name in active_pattern_names else 0.0 for name in self.known_patterns], dtype=np.float32)

    def _fetch_latest_embedding(self, symbol: str):
        def _coerce_embedding(x):
            try:
                # Already a sequence of numbers
                if isinstance(x, (list, tuple, np.ndarray)):
                    arr = np.array(x, dtype=np.float32)
                elif isinstance(x, str):
                    s = x.strip()
                    # Try JSON first
                    try:
                        arr = np.array(json.loads(s), dtype=np.float32)
                    except Exception:
                        # Fallback: parse bracketed vector like "[1,2,3]" or pgvector text
                        s = s.strip("[]{}()")
                        parts = [p.strip() for p in s.split(",") if p.strip()]
                        arr = np.array([float(p) for p in parts], dtype=np.float32) if parts else np.zeros(0, dtype=np.float32)
                else:
                    arr = np.zeros(0, dtype=np.float32)
            except Exception:
                arr = np.zeros(0, dtype=np.float32)

            # Ensure fixed size 128
            emb_dim = 128
            if arr.size < emb_dim:
                pad = np.zeros(emb_dim - arr.size, dtype=np.float32)
                arr = np.concatenate([arr, pad]).astype(np.float32)
            elif arr.size > emb_dim:
                arr = arr[:emb_dim].astype(np.float32)
            return arr

        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT embedding_json FROM current_embeddings
                    WHERE symbol = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (symbol,),
                )
                row = cur.fetchone()
                if not row:
                    return np.zeros(128, dtype=np.float32)
                emb = row["embedding"] if isinstance(row, dict) else row[0]
                return _coerce_embedding(emb)

    def _fetch_market_state(self):
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_regime, conviction FROM market_state WHERE id = 1")
                row = cur.fetchone()
                if not row:
                    return np.array([0, 1, 0], dtype=np.float32), 0.0  # default NEUTRAL
                regime = row["current_regime"] if isinstance(row, dict) else row[0]
                conviction = float(row["conviction"] if isinstance(row, dict) else row[1])
        one_hot = np.array(
            [1, 0, 0] if regime == "BEARISH" else ([0, 0, 1] if regime == "BULLISH" else [0, 1, 0]),
            dtype=np.float32,
        )
        return one_hot, conviction

    def _fetch_policy_config(self):
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT reward_weights, risk_params FROM policy_config WHERE id = 1")
                row = cur.fetchone()
                if not row:
                    # Return default dictionaries
                    return {"sharpe": 0.6, "pnl": 0.3, "drawdown": -0.1, "turnover": -0.1}, {"max_pos": 0.15}
                
                rw_raw = row["reward_weights"]
                rp_raw = row["risk_params"]

                # Ensure the data is parsed into a dictionary
                rw = json.loads(rw_raw) if isinstance(rw_raw, str) else rw_raw
                rp = json.loads(rp_raw) if isinstance(rp_raw, str) else rp_raw
                
                return rw, rp

    def reset(self, *, seed: int | None = None, options: Dict[str, Any] | None = None):
        super().reset(seed=seed)
        self._weights[:] = 0.0
        self._cash = 1.0
        obs = self._build_observation()
        self._last_obs = obs
        return obs, {}

    def step(self, action):
        action = np.clip(action, self.action_space.low, self.action_space.high)
        # Normalize weights to <=1 total; residual to cash
        w = action.astype(np.float32)
        w = w / max(1.0, w.sum())

        # Apply risk cap per asset
        _, risk_params = self._fetch_policy_config()
        max_pos = float(risk_params.get("max_pos", 0.15))
        w = np.minimum(w, max_pos)
        w = w / max(1.0, w.sum())

        # Compute simple PnL proxy: dot(weights, pseudo-returns)
        # This is a placeholder: replace with real price-based returns from market_data.
        pseudo_returns = np.zeros(self.n_assets, dtype=np.float32)
        reward_weights, _ = self._fetch_policy_config()

        pnl = float(np.dot(w - self._weights, pseudo_returns))
        turnover = float(np.abs(w - self._weights).sum())
        drawdown_penalty = 0.0  # placeholder

        reward = (
            reward_weights.get("pnl", 0.3) * pnl
            + reward_weights.get("turnover", -0.1) * (-turnover)
            + reward_weights.get("drawdown", -0.1) * (-drawdown_penalty)
        )

        self._weights = w
        self._cash = 1.0 - w.sum()

        obs = self._build_observation()
        self._last_obs = obs
        terminated = False
        truncated = False
        info = {"pnl": pnl, "turnover": turnover}
        return obs, reward, terminated, truncated, info

    def _build_observation(self):
        embs = []
        for sym in self.symbols:
            embs.append(self._fetch_latest_embedding(sym))
        embs_vec = np.concatenate(embs, dtype=np.float32) if embs else np.zeros(128, dtype=np.float32)
        
        regime_one_hot, conviction = self._fetch_market_state()

        pattern_features = self._get_pattern_features()

        obs = np.concatenate([
            embs_vec,
            self._weights.astype(np.float32),
            np.array([self._cash], dtype=np.float32),
            regime_one_hot.astype(np.float32),
            np.array([conviction], dtype=np.float32),
            pattern_features.astype(np.float32),
        ], dtype=np.float32)
        return obs

    def render(self):
        pass
