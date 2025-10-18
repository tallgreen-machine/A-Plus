# policy/pattern_library.py
from shared.db import get_db_conn
import pandas as pd

class Tier1Patterns:
    """
    Library of proven, non-degrading, fundamental patterns.
    Each function takes market data and returns True/False if 
    the pattern is detected RIGHT NOW.
    """

    def __init__(self, symbol="BTC/USD"):
        self.symbol = symbol
        self.db_conn = get_db_conn()

    def fetch_recent_data(self, limit=50):
        """Fetches the most recent N candles for the symbol."""
        query = """
            SELECT ts, open, high, low, close, volume
            FROM market_data
            WHERE symbol = %s
            ORDER BY ts DESC
            LIMIT %s;
        """
        with self.db_conn.cursor() as cur:
            cur.execute(query, (self.symbol, limit))
            data = cur.fetchall()
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        # Ensure numeric columns are of a numeric type
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        df = df.sort_values('ts', ascending=True).reset_index(drop=True)
        return df

    def check_for_liquidity_sweep(self):
        """
        Looks for:
        1. A clear 'liquidity pool' (e.g., recent equal lows).
        2. A sharp, high-volume move that *takes* that liquidity.
        3. An immediate, strong reversal (e.g., engulfing candle) 
           back into the range.
        """
        df = self.fetch_recent_data(limit=50)
        if len(df) < 20:
            return None # Not enough data to analyze

        # 1. Find a liquidity pool (e.g., two nearby lows)
        # Look for two lows in the last 40 candles that are very close to each other
        recent_lows = df['low'].iloc[-40:-2]
        min_low_val = recent_lows.min()
        liquidity_pool_lows = recent_lows[abs(recent_lows - min_low_val) / min_low_val < 0.001] # Within 0.1%

        if len(liquidity_pool_lows) < 2:
            return None # No clear liquidity pool found

        liquidity_level = liquidity_pool_lows.min()

        # 2. Check for a sharp move that takes the liquidity
        # The most recent candle's low should be below the liquidity level
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        if last_candle['low'] > liquidity_level:
            return None # Liquidity not taken

        # 3. Check for a strong reversal (bullish engulfing)
        # Last candle closes above previous candle's open, and opened below its close
        is_engulfing = (last_candle['close'] > prev_candle['open'] and 
                        last_candle['open'] < prev_candle['close'] and
                        last_candle['close'] > last_candle['open']) # Is a green candle

        if is_engulfing:
            print(f"LIQUIDITY SWEEP DETECTED on {self.symbol} at {last_candle['ts']}")
            return {'pattern_name': 'Liquidity Sweep', 'confidence': 0.71, 'details': {'price': last_candle['close'], 'liquidity_level': liquidity_level}}
        
        return None

    def check_for_capitulation_volume(self):
        """
        Looks for:
        1. A sustained, multi-day downtrend.
        2. A massive spike in volume (e.g., > 4x 20-day avg).
        3. A sharp price drop followed by an immediate bounce.
        """
        # ... (Specific detection logic for this pattern)
        pattern_detected = False # Placeholder
        if pattern_detected:
            return {'pattern_name': 'Capitulation', 'confidence': 0.69}
        return None

    def check_for_funding_rate_extreme(self):
        """
        Looks for:
        1. Funding rate > 0.1% or < -0.1% for 12+ hours.
        2. Price action showing signs of a squeeze.
        """
        # ... (Specific detection logic for this pattern)
        pattern_detected = False # Placeholder
        if pattern_detected:
            return {'pattern_name': 'Funding Extreme', 'confidence': 0.67}
        return None
    
    # ... functions for Supply Shock, BoS, etc. ...
