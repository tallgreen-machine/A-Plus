import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent

class VolumeBreakout(BaseStrategy):
    """
    Volume-Confirmed Breakout Strategy
    
    Enters a trade when the price breaks through a key resistance or support level,
    but only if the breakout is accompanied by a significant increase in volume.
    """
    def __init__(self, symbol: str, data: dict):
        super().__init__(symbol, data)
        self.timeframe = '1h'
        self.resistance_lookback = 24 # N candles
        self.volume_sma_period = 20
        self.volume_multiplier = 2.0 # M times

    def check_signal(self):
        """
        Checks for a bullish volume-confirmed breakout.
        
        1.  **Identify Resistance**: Find the highest high over the last 24 candles.
        2.  **Breakout Condition**: The last candle's close must be above this resistance high.
        3.  **Volume Confirmation**: The breakout candle's volume must be > 2x the 20-period SMA of volume.
        
        :return: A SignalEvent if conditions are met, otherwise None.
        """
        df = self._get_data(self.timeframe)
        if df.empty or len(df) < self.resistance_lookback + 1:
            return None

        # Add indicators to the DataFrame
        df.ta.sma(close=df['volume'], length=self.volume_sma_period, append=True, col_names=(f'VOL_SMA_{self.volume_sma_period}',))

        # Resistance identification
        lookback_df = df.iloc[-(self.resistance_lookback + 1):-1]
        resistance_high = lookback_df['high'].max()

        last_candle = df.iloc[-1]

        # Condition 1: Breakout
        is_breakout = last_candle['close'] > resistance_high

        # Condition 2: Volume Confirmation
        is_volume_confirmed = last_candle['volume'] > (last_candle[f'VOL_SMA_{self.volume_sma_period}'] * self.volume_multiplier)

        if is_breakout and is_volume_confirmed:
            price = last_candle['close']
            stop_loss = resistance_high
            price_target = price + (price - stop_loss) * 2 # 1:2 Risk-to-Reward

            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='VOLUME_BREAKOUT_BULLISH',
                price=price,
                confidence=0.85,
                price_target=price_target,
                stop_loss=stop_loss
            )
            print(f"[{pd.Timestamp.now()}] BUY Signal generated for {self.symbol} by VOLUME_BREAKOUT_BULLISH")
            return signal

        return None
