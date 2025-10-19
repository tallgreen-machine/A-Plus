import pandas as pd
import pandas_ta as ta
import numpy as np

class Tier1Patterns:
    """
    A library of well-defined, high-probability trading patterns.
    Each method in this class should accept a DataFrame of OHLCV data
    and return a list of tuples, where each tuple contains the
    timestamp and price of a detected pattern occurrence.
    """
    def __init__(self, symbol="BTC/USDT"):
        self.symbol = symbol

    def detect_liquidity_sweep(self, df: pd.DataFrame, window=20) -> list:
        """
        Detects a liquidity sweep (also known as a stop hunt).
        This occurs when price briefly takes out a recent high or low
        and then quickly reverses.

        :param df: DataFrame with OHLCV data.
        :param window: The lookback period to identify recent highs/lows.
        :return: A list of (timestamp, price) tuples for each detected sweep.
        """
        occurrences = []
        df['rolling_low'] = df['low'].rolling(window=window).min()
        df = df.reset_index()
        
        for i in range(window, len(df)):
            current_candle = df.iloc[i]
            prev_candle = df.iloc[i-1]
            
            # Check if the previous candle's low was the rolling low
            if prev_candle['low'] <= df['rolling_low'].iloc[i-1]:
                # Check if the current candle swept that low and closed back above it
                if current_candle['low'] < prev_candle['low'] and current_candle['close'] > prev_candle['low']:
                    # Liquidity sweep detected
                    timestamp = current_candle['ts']
                    price = current_candle['low']
                    occurrences.append((timestamp, price))
        return occurrences

    def detect_fair_value_gap(self, df: pd.DataFrame) -> list:
        """
        Detects a Fair Value Gap (FVG) or imbalance.
        This is a three-candle pattern where there is a gap between the
        high of the first candle and the low of the third candle.

        :param df: DataFrame with OHLCV data.
        :return: A list of (timestamp, price) tuples for each detected FVG.
        """
        occurrences = []
        df = df.reset_index()
        for i in range(2, len(df)):
            candle1 = df.iloc[i-2]
            candle2 = df.iloc[i-1] # The gapping candle
            candle3 = df.iloc[i]

            # Bullish FVG: Gap between candle1 high and candle3 low
            if candle2['close'] > candle2['open']: # Bullish middle candle
                if candle3['low'] > candle1['high']:
                    # FVG detected. The "price" is the bottom of the gap.
                    timestamp = candle2['ts']
                    price = candle1['high']
                    occurrences.append((timestamp, price))
        return occurrences

    def detect_bullish_order_block(self, df: pd.DataFrame, lookahead=5) -> list:
        """
        Detects a Bullish Order Block (simplified).
        An order block is the last down candle before a strong bullish move
        that breaks the high of the candle prior to the order block.

        :param df: DataFrame with OHLCV data.
        :param lookahead: How many candles to look forward to for the break of structure.
        :return: A list of (timestamp, price) tuples for each detected order block.
        """
        occurrences = []
        df = df.reset_index()
        for i in range(1, len(df) - lookahead):
            # Potential Order Block: A down candle
            if df['close'].iloc[i] < df['open'].iloc[i]:
                
                order_block_candle = df.iloc[i]
                structure_high = df['high'].iloc[i-1] # The high to be broken

                # Look ahead for a break of structure
                for j in range(1, lookahead + 1):
                    future_candle = df.iloc[i+j]
                    if future_candle['high'] > structure_high:
                        # Structure broken. This is a valid order block.
                        # The "price" is the top of the order block candle's body.
                        timestamp = order_block_candle['ts']
                        price = order_block_candle['open']
                        occurrences.append((timestamp, price))
                        break # Move to the next potential order block
        return occurrences
