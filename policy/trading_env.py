import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any
import psycopg2
import psycopg2.extras

from shared.db import get_db_conn
from utils.logger import log


class CryptoTradingEnv(gym.Env):
    metadata = {"render.modes": ["human"]}

    def __init__(self, symbols: list[str], window: int = 200, total_timesteps: int = 100):
        super().__init__()
        log.info(f"Initializing CryptoTradingEnv for symbols: {symbols}")
        self.symbols = symbols
        self.window = window
        self.total_timesteps = total_timesteps
        self.n_assets = len(symbols)
        self._active_patterns = self._load_active_patterns()
        self.known_patterns = ['Liquidity Sweep']  # A registry of all possible patterns

        # State buffers
        self._weights = np.zeros(self.n_assets, dtype=np.float32)
        self._cash = 1.0
        self._last_obs = None
        
        # Data buffers for market prices
        self._prices = {}
        self._timestamps = []
        self._current_step = 0
        self._load_market_data()

        # Observations: embeddings, weights, cash, regime, conviction, active_patterns
        emb_dim = 128
        patterns_dim = len(self.known_patterns)
        obs_dim = self.n_assets * emb_dim + self.n_assets + 1 + 3 + 1 + patterns_dim
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)

        # Action: target weights per asset in [-1,1] for rescaling
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(self.n_assets,), dtype=np.float32)

        log.info("CryptoTradingEnv initialized.")

    def _load_market_data(self):
        """Loads historical price data from the enhanced database."""
        log.info("Loading market data from enhanced database...")
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Use 5m timeframe as default for training (good balance of detail and speed)
                timeframe = getattr(self, 'timeframe', '5m')
                
                # Get all timestamps for the first symbol to establish the timeline
                cur.execute(
                    """
                    SELECT DISTINCT timestamp FROM market_data_enhanced
                    WHERE symbol = %s AND timeframe = %s ORDER BY timestamp
                    """,
                    (self.symbols[0], timeframe)
                )
                self._timestamps = [row['timestamp'] for row in cur.fetchall()]

                if not self._timestamps:
                    log.error(f"No market data found for the primary symbol with timeframe {timeframe}. Cannot proceed.")
                    return

                # Load close prices for all symbols
                for symbol in self.symbols:
                    cur.execute(
                        """
                        SELECT timestamp, close FROM market_data_enhanced
                        WHERE symbol = %s AND timeframe = %s ORDER BY timestamp
                        """,
                        (symbol, timeframe)
                    )
                    # Store prices in a dictionary for quick lookup by timestamp
                    self._prices[symbol] = {row['timestamp']: float(row['close']) for row in cur.fetchall()}
        log.info(f"Loaded {len(self._timestamps)} timestamps and price data for {len(self.symbols)} symbols using {timeframe} timeframe.")

    def _load_active_patterns(self):
        """Loads the active patterns from the JSON file."""
        active_patterns_path = Path('active_patterns.json')
        if not active_patterns_path.exists():
            log.warning("active_patterns.json not found. No patterns will be used.")
            return []
        try:
            with open(active_patterns_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            log.warning("active_patterns.json is empty or malformed. No patterns will be used.")
            return []

    def _get_pattern_features(self) -> np.ndarray:
        """Creates a binary vector indicating which known patterns are active."""
        active_pattern_names = {p['name'] for p in self._active_patterns}
        return np.array([1.0 if name in active_pattern_names else 0.0 for name in self.known_patterns], dtype=np.float32)

    def _fetch_latest_embedding(self, symbol: str):
        log.debug(f"Fetching latest embedding for {symbol}...")
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
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
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
                    log.warning(f"No embedding found for {symbol}. Returning zeros.")
                    return np.zeros(128, dtype=np.float32)
                emb = row["embedding_json"]
                result = _coerce_embedding(emb)
                log.debug(f"Successfully fetched embedding for {symbol}.")
                return result

    def _fetch_market_state(self):
        log.debug("Fetching market state...")
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT current_regime, conviction FROM market_state WHERE id = 1")
                row = cur.fetchone()
                if not row:
                    log.warning("No market state found. Using default (NEUTRAL).")
                    return np.array([0, 1, 0], dtype=np.float32), 0.0  # default NEUTRAL
                regime = row["current_regime"]
                conviction = float(row["conviction"])
        one_hot = np.array(
            [1, 0, 0] if regime == "BEARISH" else ([0, 0, 1] if regime == "BULLISH" else [0, 1, 0]),
            dtype=np.float32,
        )
        log.debug(f"Successfully fetched market state: {regime}, {conviction}")
        return one_hot, conviction

    def _fetch_policy_config(self):
        log.debug("Fetching policy config...")
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT reward_weights, risk_params FROM policy_config WHERE id = 1")
                row = cur.fetchone()
                if not row:
                    log.warning("No policy config found. Using default values.")
                    # Return default dictionaries
                    return {"sharpe": 0.6, "pnl": 0.3, "drawdown": -0.1, "turnover": -0.1}, {"max_pos": 0.15}
                
                rw_raw = row["reward_weights"]
                rp_raw = row["risk_params"]

                # Ensure the data is parsed into a dictionary
                rw = json.loads(rw_raw) if isinstance(rw_raw, str) else rw_raw
                rp = json.loads(rp_raw) if isinstance(rp_raw, str) else rp_raw
                
                log.debug("Successfully fetched policy config.")
                return rw, rp

    def reset(self, *, seed: int | None = None, options: Dict[str, Any] | None = None):
        log.info("Resetting environment.")
        super().reset(seed=seed)
        self._weights[:] = 0.0
        self._cash = 1.0
        self._current_step = 0
        obs = self._build_observation()
        self._last_obs = obs
        log.info("Environment reset complete.")
        return obs, {}

    def step(self, action):
        log.debug(f"Executing step with action: {action}")
        
        # Check if we are at the end of the dataset
        if self._current_step >= len(self._timestamps) - 1:
            obs = self._build_observation()
            return obs, 0, True, False, {"msg": "End of dataset reached."}

        # Rescale action from [-1, 1] to [0, 1] for long-only portfolio
        action = (action + 1) / 2.0
        action = np.clip(action, 0.0, 1.0)

        # Normalize weights to <=1 total; residual to cash
        w = action.astype(np.float32)
        w = w / max(1.0, w.sum())

        # Apply risk cap per asset
        _, risk_params = self._fetch_policy_config()
        max_pos = float(risk_params.get("max_pos", 0.15))
        w = np.minimum(w, max_pos)
        w = w / max(1.0, w.sum())

        # Calculate returns from real market data
        current_ts = self._timestamps[self._current_step]
        next_ts = self._timestamps[self._current_step + 1]
        
        returns = np.zeros(self.n_assets, dtype=np.float32)
        for i, symbol in enumerate(self.symbols):
            current_price = self._prices[symbol].get(current_ts)
            next_price = self._prices[symbol].get(next_ts)
            
            if current_price is not None and next_price is not None and current_price > 0:
                returns[i] = (next_price - current_price) / current_price
            else:
                log.warning(f"Missing price for {symbol} at step {self._current_step}. Return will be 0.")

        # Compute PnL and other reward components
        reward_weights, _ = self._fetch_policy_config()
        pnl = float(np.dot(w - self._weights, returns))
        turnover = float(np.abs(w - self._weights).sum())
        drawdown_penalty = 0.0  # placeholder

        reward = (
            reward_weights.get("pnl", 0.3) * pnl
            + reward_weights.get("turnover", -0.1) * (-turnover)
            + reward_weights.get("drawdown", -0.1) * (-drawdown_penalty)
        )

        self._weights = w
        self._cash = 1.0 - w.sum()
        self._current_step += 1

        obs = self._build_observation()
        self._last_obs = obs
        terminated = False
        truncated = False
        info = {"pnl": pnl, "turnover": turnover}
        log.debug("Step execution complete.")
        return obs, reward, terminated, truncated, info

    def _build_observation(self):
        log.debug("Building observation...")
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
            pattern_features,
        ], dtype=np.float32)
        log.debug(f"Observation built with shape: {obs.shape}")
        log.debug("Observation built successfully.")
        return obs

    def render(self):
        pass
