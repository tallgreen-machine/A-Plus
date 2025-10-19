import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent

class HTFSweep(BaseStrategy):
    """
    HTF Sweep Strategy
    
    Identifies a sweep of a significant high/low on a higher timeframe (e.g., 4h)
    and looks for a confirmation on a lower timeframe (e.g., 1h) to enter a trade.
    """
    def __init__(self, symbol: str, data: dict):
        super().__init__(symbol, data)
        self.htf = '4h'
        self.ltf = '1h'

    def check_signal(self):
        """
        Checks for a bearish HTF sweep signal.
        
        1.  **HTF (4h):** Identify the high of the second to last closed candle (`htf_high`).
        2.  **HTF (4h):** Check if the last closed candle "swept" that high (last high > `htf_high`) 
            but closed below it (last close < `htf_high`). This is the "sweep".
        3.  **LTF (1h):** Check if the most recent `ltf` candle also closed bearishly 
            (close < open) to confirm the downward momentum.
        
        :return: A SignalEvent if conditions are met, otherwise None.
        """
        df_htf = self._get_data(self.htf)
        df_ltf = self._get_data(self.ltf)

        if df_htf.empty or len(df_htf) < 3 or df_ltf.empty:
            return None

        # HTF analysis
        htf_prev_candle = df_htf.iloc[-2]
        htf_last_candle = df_htf.iloc[-1]
        
        htf_high_to_sweep = htf_prev_candle['high']

        # Condition 1: Last HTF candle swept the previous high but closed below it
        is_sweep = (htf_last_candle['high'] > htf_high_to_sweep) and \
                   (htf_last_candle['close'] < htf_high_to_sweep)

        if not is_sweep:
            return None
            
        # Condition 2: LTF confirmation with a bearish close
        ltf_last_candle = df_ltf.iloc[-1]
        is_ltf_confirmation = ltf_last_candle['close'] < ltf_last_candle['open']

        if is_sweep and is_ltf_confirmation:
            price = ltf_last_candle['close']
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='SELL',
                strategy_id='HTF_SWEEP_BEARISH',
                price=price,
                confidence=0.8,
                price_target=price * 0.95, # 5% target
                stop_loss=htf_last_candle['high'] # Stop loss above the sweep high
            )
            print(f"[{pd.Timestamp.now()}] SELL Signal generated for {self.symbol} by HTF_SWEEP_BEARISH")
            return signal
            
        return None
