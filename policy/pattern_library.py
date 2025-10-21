# policy/pattern_library.py
from shared.db import get_db_conn
import pandas as pd

PATTERN_REGISTRY = {}

def register_pattern(name):
    def decorator(cls):
        PATTERN_REGISTRY[name] = cls
        return cls
    return decorator


@register_pattern("Tier1")
class Tier1Patterns:
    """
    Library of proven, non-degrading, fundamental patterns.
    Each function takes market data and returns True/False if 
    the pattern is detected RIGHT NOW.
    """

    def __init__(self, symbol="BTC/USDT"):
        self.symbol = symbol
        self.db_conn = get_db_conn()

    def fetch_recent_data(self, limit=50, timeframe='5m'):
        """Fetches the most recent N candles for the symbol from enhanced database."""
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data_enhanced
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s;
        """
        with self.db_conn.cursor() as cur:
            cur.execute(query, (self.symbol, timeframe, limit))
            data = cur.fetchall()
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # Ensure numeric columns are of a numeric type
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        df = df.sort_values('timestamp', ascending=True).reset_index(drop=True)
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
            print(f"LIQUIDITY SWEEP DETECTED on {self.symbol} at {last_candle['timestamp']}")
            return {'pattern_name': 'Liquidity Sweep', 'confidence': 0.71, 'details': {'price': last_candle['close'], 'liquidity_level': liquidity_level}}
        
        return None

    def check_for_fair_value_gap(self):
        """
        Identifies a Fair Value Gap (FVG), which is a three-candle pattern indicating an imbalance.
        - A bullish FVG is when the low of the third candle is higher than the high of the first candle.
        - We look for a recent FVG that has not yet been filled.
        """
        df = self.fetch_recent_data(limit=20)
        if len(df) < 5:
            return None

        # Look for a bullish FVG in the last 15 candles
        for i in range(len(df) - 3, len(df) - 18, -1):
            if i < 2: continue
            
            c1, c2, c3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]

            # Check for a bullish FVG
            is_bullish_fvg = c3['low'] > c1['high']
            
            if is_bullish_fvg:
                fvg_top = c3['low']
                fvg_bottom = c1['high']
                
                # Check if the FVG has been filled by subsequent candles
                is_filled = False
                for j in range(i + 1, len(df)):
                    if df.iloc[j]['low'] <= fvg_bottom:
                        is_filled = True
                        break
                
                if not is_filled:
                    print(f"FAIR VALUE GAP DETECTED on {self.symbol} at {c3['ts']}")
                    return {
                        'pattern_name': 'Fair Value Gap',
                        'confidence': 0.65,
                        'details': {
                            'price': c3['close'],
                            'fvg_top': fvg_top,
                            'fvg_bottom': fvg_bottom
                        }
                    }
        return None

    def detect_fair_value_gap(self, df):
        """
        Scans the entire historical dataframe to find all occurrences of a Fair Value Gap (FVG).
        Returns a list of (timestamp, price) tuples for each bullish FVG occurrence.
        """
        occurrences = []
        if len(df) < 3:
            return occurrences

        for i in range(2, len(df)):
            c1, c2, c3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]

            # Bullish FVG: The low of candle 3 is higher than the high of candle 1
            is_bullish_fvg = c3['low'] > c1['high']

            if is_bullish_fvg:
                # We consider the pattern valid at the close of the 3rd candle
                # The entry price would be the closing price of that candle
                occurrences.append((c3['ts'], c3['close']))
        
        return occurrences

    def detect_liquidity_sweep(self, df):
        """
        Scans the entire historical dataframe to find all occurrences of the liquidity sweep pattern.
        This is used for backtesting by the Reliability Engine.
        Returns a list of (timestamp, price) tuples for each occurrence.
        """
        occurrences = []
        if len(df) < 50:
            return occurrences

        # Use a rolling window to check for the pattern across the dataset
        for i in range(40, len(df) - 1):
            # Window of 41 candles to check pattern at candle `i`. 
            # The last candle in the window is the one we're evaluating.
            window = df.iloc[i-41:i+1] 
            
            # 1. Find a liquidity pool in the 40 candles *before* the current one.
            analysis_window = window.iloc[:-1]
            min_low_val = analysis_window['low'].min()
            
            # Find lows that are very close to the minimum low
            liquidity_pool_lows = analysis_window['low'][abs(analysis_window['low'] - min_low_val) / min_low_val < 0.001]

            if len(liquidity_pool_lows) < 2:
                continue

            liquidity_level = liquidity_pool_lows.min() # This should be a float

            # 2. Check for a sharp move that takes the liquidity
            # The sweep candle is the last candle in our window.
            sweep_candle = window.iloc[-1]
            
            if sweep_candle['low'] > liquidity_level:
                continue

            # 3. Check for a strong reversal (bullish engulfing)
            # The candle before the sweep candle is used for engulfing check.
            reversal_candle = window.iloc[-2]
            is_engulfing = (reversal_candle['close'] > sweep_candle['open'] and
                            reversal_candle['open'] < sweep_candle['close'] and
                            reversal_candle['close'] > reversal_candle['open']) # Is a green candle

            if is_engulfing:
                # Pattern is confirmed at the close of the reversal candle.
                # This is the entry point for our simulated trade.
                entry_ts = reversal_candle['ts']
                entry_price = reversal_candle['close']
                occurrences.append((entry_ts, entry_price))
        
        return occurrences

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
