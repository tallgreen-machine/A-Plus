import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent

class DivergenceCapitulation(BaseStrategy):
    """
    Divergence-Confirmed Capitulation Strategy
    
    Looks for bullish divergence between price and an oscillator (RSI) during
    a strong downtrend, followed by a capitulation candle, to signal a potential bottom.
    """
    def __init__(self, symbol: str, data: dict):
        super().__init__(symbol, data)
        self.timeframe = '1h'
        self.rsi_period = 14
        self.divergence_lookback = 10 # N candles to look for divergence

    def check_signal(self):
        """
        Checks for a bullish divergence and capitulation signal.
        
        1.  **Identify Divergence**: Over the last 10 candles, find two price lows.
            The second low must be lower than the first (`low_2` < `low_1`).
            The RSI values at these two points must show divergence (RSI at `low_2` > RSI at `low_1`).
        2.  **Identify Capitulation**: The candle corresponding to the second low (`low_2`)
            must be a "capitulation candle" - a strongly bearish candle with a large body.
        
        :return: A SignalEvent if conditions are met, otherwise None.
        """
        df = self._get_data(self.timeframe)
        if df.empty or len(df) < self.divergence_lookback + 2:
            return None

        # Add RSI to DataFrame
        df.ta.rsi(length=self.rsi_period, append=True, col_names=(f'RSI_{self.rsi_period}',))

        lookback_df = df.iloc[-self.divergence_lookback:]

        # Find the two most recent significant lows in the lookback period
        lows = lookback_df[
            (lookback_df['low'] < lookback_df['low'].shift(1)) & 
            (lookback_df['low'] < lookback_df['low'].shift(-1))
        ]

        if len(lows) < 2:
            return None

        # Get the last two lows
        last_low_1 = lows.iloc[-2]
        last_low_2 = lows.iloc[-1]

        # Condition 1: Bullish Divergence
        price_makes_lower_low = last_low_2['low'] < last_low_1['low']
        rsi_makes_higher_low = last_low_2[f'RSI_{self.rsi_period}'] > last_low_1[f'RSI_{self.rsi_period}']
        
        is_divergence = price_makes_lower_low and rsi_makes_higher_low

        if not is_divergence:
            return None

        # Condition 2: Capitulation Candle at the second low
        capitulation_candle = df.loc[last_low_2.name]
        body_size = abs(capitulation_candle['close'] - capitulation_candle['open'])
        candle_range = capitulation_candle['high'] - capitulation_candle['low']
        is_capitulation = (body_size / candle_range > 0.7) and (capitulation_candle['close'] < capitulation_candle['open'])

        if is_divergence and is_capitulation:
            price = capitulation_candle['close']
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='DIVERGENCE_CAPITULATION_BULLISH',
                price=price,
                confidence=0.75,
                price_target=price * 1.07, # 7% target
                stop_loss=capitulation_candle['low'] * 0.99 # Stop just below the low
            )
            print(f"[{pd.Timestamp.now()}] BUY Signal generated for {self.symbol} by DIVERGENCE_CAPITULATION_BULLISH")
            return signal

        return None
