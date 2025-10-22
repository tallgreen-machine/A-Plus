import pandas as pd
import pandas_ta as ta
import numpy as np
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent

class HTFSweep(BaseStrategy):
    """
    HTF Sweep Strategy - A+ Setup Implementation
    
    Exact A-Plus HTF Sweep Logic:
    - HTF Context (1H): Identifies significant swing low/high using programmatic local minima/maxima
    - Liquidity Sweep: 1H candle wicks beyond swing level but closes back inside
    - LTF Confirmation (5M): Market structure shift - break of minor swing in opposite direction
    - ML Enhancement: Uses trained asset parameters for optimal thresholds per symbol/exchange
    
    Philosophy: "Patience and Precision" - Only high-confluence liquidity engineering setups
    """
    def __init__(self, symbol: str, data: dict, trained_assets_manager=None):
        super().__init__(symbol, data)
        # A+ Specification: 1H → 5M timeframes
        self.htf = '1h'  # Higher timeframe for sweep identification
        self.ltf = '5m'  # Lower timeframe for entry confirmation
        self.trained_assets_manager = trained_assets_manager
        
        # Default A+ parameters (will be overridden by ML if available)
        self.default_params = {
            'swing_lookback_periods': 20,
            'risk_reward_ratio': 2.5,
            'min_sweep_percentage': 0.001,  # Minimum sweep beyond swing level
            'structure_shift_confirmation': True
        }

    
    def _get_ml_optimized_params(self, symbol: str, exchange: str = 'binanceus'):
        """
        Get ML-optimized parameters for this symbol/exchange combination
        
        Returns:
            dict: Optimized parameters for HTF Sweep setup
        """
        if not self.trained_assets_manager:
            return self.default_params
        
        try:
            # Get ML-optimized strategy parameters for HTF Sweep
            optimized_params = self.trained_assets_manager.get_strategy_parameters(
                symbol=symbol,
                exchange=exchange,
                strategy_id='htf_sweep'
            )
            
            if optimized_params:
                return {
                    'swing_lookback_periods': optimized_params.get('swing_lookback_periods', 20),
                    'risk_reward_ratio': optimized_params.get('risk_reward_ratio', 2.5),
                    'min_sweep_percentage': optimized_params.get('min_sweep_percentage', 0.001),
                    'structure_shift_confirmation': optimized_params.get('structure_shift_confirmation', True)
                }
        except Exception as e:
            print(f"Warning: Could not load ML parameters for {symbol}, using defaults: {e}")
        
        return self.default_params
    
    def _find_swing_low(self, df: pd.DataFrame, lookback: int) -> tuple:
        """
        Programmatic method to find local minima (swing lows) as per A+ specification
        
        Returns:
            tuple: (swing_low_price, swing_low_index) or (None, None)
        """
        if len(df) < lookback + 2:
            return None, None
            
        lows = df['low'].values
        swing_candidates = []
        
        # Find local minima: low[i-1] > low[i] < low[i+1]
        for i in range(1, len(lows) - 1):
            if lows[i-1] > lows[i] < lows[i+1]:
                swing_candidates.append((lows[i], i))
        
        if not swing_candidates:
            return None, None
            
        # Return most recent significant swing low
        return swing_candidates[-1]
    
    def _find_swing_high(self, df: pd.DataFrame, lookback: int) -> tuple:
        """
        Programmatic method to find local maxima (swing highs) as per A+ specification
        
        Returns:
            tuple: (swing_high_price, swing_high_index) or (None, None)
        """
        if len(df) < lookback + 2:
            return None, None
            
        highs = df['high'].values
        swing_candidates = []
        
        # Find local maxima: high[i-1] < high[i] > high[i+1]
        for i in range(1, len(highs) - 1):
            if highs[i-1] < highs[i] > highs[i+1]:
                swing_candidates.append((highs[i], i))
        
        if not swing_candidates:
            return None, None
            
        # Return most recent significant swing high
        return swing_candidates[-1]
    
    def check_signal_long(self):
        """
        A+ HTF Sweep Long Entry Logic (Exact specification implementation)
        
        1. HTF Context (1H): Identify most recent significant swing low
        2. Liquidity Sweep: 1H candle wicks below swing low but closes above
        3. LTF Confirmation (5M): Break above minor swing high formed during sweep
        4. Entry: LONG market order on 5M confirmation
        5. Stop-Loss: Below absolute low of 1H sweep candle wick
        6. Take-Profit: ML-optimized Risk-to-Reward ratio
        
        Returns:
            SignalEvent if A+ setup confirmed, otherwise None
        """
        df_htf = self._get_data(self.htf)
        df_ltf = self._get_data(self.ltf)
        
        if df_htf.empty or len(df_htf) < 25 or df_ltf.empty or len(df_ltf) < 10:
            return None
        
        # Get ML-optimized parameters for this symbol
        params = self._get_ml_optimized_params(self.symbol)
        
        # Step 1: HTF Context - Find most recent significant swing low
        swing_low_price, swing_low_idx = self._find_swing_low(
            df_htf[:-1], params['swing_lookback_periods']
        )
        
        if swing_low_price is None:
            return None
        
        # Step 2: Liquidity Sweep Condition
        htf_last_candle = df_htf.iloc[-1]
        
        # Sweep: wick trades below swing low BUT closes above it
        sweep_threshold = swing_low_price * (1 - params['min_sweep_percentage'])
        is_sweep = (htf_last_candle['low'] < sweep_threshold) and \
                   (htf_last_candle['close'] > swing_low_price)
        
        if not is_sweep:
            return None
        
        # Step 3: LTF Confirmation - Market Structure Shift
        if params['structure_shift_confirmation']:
            # Get 5M data during the 1H sweep candle period
            htf_candle_start = df_htf.index[-1] - pd.Timedelta(hours=1)
            htf_candle_end = df_htf.index[-1]
            
            sweep_period_mask = (df_ltf.index >= htf_candle_start) & (df_ltf.index <= htf_candle_end)
            ltf_sweep_period = df_ltf[sweep_period_mask]
            
            if ltf_sweep_period.empty:
                return None
            
            # Find minor swing high during sweep period
            minor_swing_high = ltf_sweep_period['high'].max()
            
            # Current 5M candle must close above minor swing high
            ltf_current_candle = df_ltf.iloc[-1]
            is_structure_shift = ltf_current_candle['close'] > minor_swing_high
            
            if not is_structure_shift:
                return None
        
        # Step 4: A+ Setup Confirmed - Generate Long Signal
        entry_price = df_ltf.iloc[-1]['close']
        stop_loss = htf_last_candle['low']
        
        # ML-optimized risk-reward calculation
        risk_amount = entry_price - stop_loss
        take_profit = entry_price + (risk_amount * params['risk_reward_ratio'])
        
        signal = SignalEvent(
            symbol=self.symbol,
            signal_type='BUY',
            strategy_id='HTF_SWEEP_LONG',
            price=entry_price,
            confidence=0.85,  # High confidence A+ setup
            price_target=take_profit,
            stop_loss=stop_loss
        )
        
        print(f"[{pd.Timestamp.now()}] 🎯 HTF SWEEP LONG: {self.symbol}")
        print(f"   Entry: ${entry_price:.4f} | SL: ${stop_loss:.4f} | TP: ${take_profit:.4f}")
        print(f"   R/R: 1:{params['risk_reward_ratio']} | Swing: ${swing_low_price:.4f}")
        
        return signal

    def check_signal_short(self):
        """
        A+ HTF Sweep Short Entry Logic (Mirror of long logic)
        """
        df_htf = self._get_data(self.htf)
        df_ltf = self._get_data(self.ltf)
        
        if df_htf.empty or len(df_htf) < 25 or df_ltf.empty or len(df_ltf) < 10:
            return None
        
        # Get ML-optimized parameters
        params = self._get_ml_optimized_params(self.symbol)
        
        # Find most recent significant swing high
        swing_high_price, swing_high_idx = self._find_swing_high(
            df_htf[:-1], params['swing_lookback_periods']
        )
        
        if swing_high_price is None:
            return None
        
        # Liquidity Sweep: wick above swing high but closes below
        htf_last_candle = df_htf.iloc[-1]
        sweep_threshold = swing_high_price * (1 + params['min_sweep_percentage'])
        is_sweep = (htf_last_candle['high'] > sweep_threshold) and \
                   (htf_last_candle['close'] < swing_high_price)
        
        if not is_sweep:
            return None
        
        # LTF Confirmation - Break below minor swing low
        if params['structure_shift_confirmation']:
            htf_candle_start = df_htf.index[-1] - pd.Timedelta(hours=1)
            htf_candle_end = df_htf.index[-1]
            
            sweep_period_mask = (df_ltf.index >= htf_candle_start) & (df_ltf.index <= htf_candle_end)
            ltf_sweep_period = df_ltf[sweep_period_mask]
            
            if ltf_sweep_period.empty:
                return None
            
            minor_swing_low = ltf_sweep_period['low'].min()
            ltf_current_candle = df_ltf.iloc[-1]
            is_structure_shift = ltf_current_candle['close'] < minor_swing_low
            
            if not is_structure_shift:
                return None
        
        # Generate Short Signal
        entry_price = df_ltf.iloc[-1]['close']
        stop_loss = htf_last_candle['high']
        
        risk_amount = stop_loss - entry_price
        take_profit = entry_price - (risk_amount * params['risk_reward_ratio'])
        
        signal = SignalEvent(
            symbol=self.symbol,
            signal_type='SELL',
            strategy_id='HTF_SWEEP_SHORT',
            price=entry_price,
            confidence=0.85,
            price_target=take_profit,
            stop_loss=stop_loss
        )
        
        print(f"[{pd.Timestamp.now()}] 🎯 HTF SWEEP SHORT: {self.symbol}")
        print(f"   Entry: ${entry_price:.4f} | SL: ${stop_loss:.4f} | TP: ${take_profit:.4f}")
        print(f"   R/R: 1:{params['risk_reward_ratio']} | Swing: ${swing_high_price:.4f}")
        
        return signal

    def check_signal(self):
        """
        Main signal checking method - checks both long and short opportunities
        Implements "Patience and Precision" philosophy
        
        Returns:
            SignalEvent if A+ setup found, otherwise None
        """
        # Check for long setup first
        long_signal = self.check_signal_long()
        if long_signal:
            return long_signal
        
        # Check for short setup
        short_signal = self.check_signal_short()
        if short_signal:
            return short_signal
        
        return None
