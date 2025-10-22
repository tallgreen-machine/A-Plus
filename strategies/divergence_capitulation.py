import pandas as pd
import pandas_ta as ta
import numpy as np
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent

class DivergenceCapitulation(BaseStrategy):
    """
    Divergence-Confirmed Capitulation Strategy - A+ Setup Implementation
    
    Exact A-Plus Divergence Capitulation Logic:
    - Trend Context: 50 EMA below 200 EMA (confirmed downtrend)
    - Bullish Divergence: Price makes lower low, RSI makes higher low
    - Capitulation Volume: Volume spike ≥ 3x Volume SMA (institutional flush-out)
    - Entry Signal: First bullish candle after divergence + volume spike
    - ML Enhancement: Uses trained asset parameters for optimal thresholds per symbol/exchange
    
    Philosophy: "Patience and Precision" - Only exhaustion reversals with institutional volume
    """
    def __init__(self, symbol: str, data: dict, trained_assets_manager=None):
        super().__init__(symbol, data)
        self.timeframe = '1h'  # A+ specification timeframe
        self.trained_assets_manager = trained_assets_manager
        
        # Default A+ parameters (will be overridden by ML if available)
        self.default_params = {
            'rsi_period': 14,                # RSI calculation period
            'ema_fast_period': 50,           # Fast EMA for trend context
            'ema_slow_period': 200,          # Slow EMA for trend context
            'volume_spike_multiplier': 3.0,  # A+ spec: 3x Volume SMA
            'volume_sma_period': 20,         # Volume baseline period
            'divergence_lookback': 10,       # Period to look for divergence
            'take_profit_ema': 50            # Take profit at 50 EMA level
        }

    
    def _get_ml_optimized_params(self, symbol: str, exchange: str = 'binanceus'):
        """Get ML-optimized parameters for divergence capitulation setup"""
        if not self.trained_assets_manager:
            return self.default_params
        
        try:
            # Get ML-optimized strategy parameters for Divergence Capitulation
            optimized_params = self.trained_assets_manager.get_strategy_parameters(
                symbol=symbol,
                exchange=exchange,
                strategy_id='divergence_capitulation'
            )
            
            if optimized_params:
                return {
                    'rsi_period': optimized_params.get('rsi_period', 14),
                    'ema_fast_period': optimized_params.get('ema_fast_period', 50),
                    'ema_slow_period': optimized_params.get('ema_slow_period', 200),
                    'volume_spike_multiplier': optimized_params.get('volume_spike_multiplier', 3.0),
                    'volume_sma_period': 20,
                    'divergence_lookback': optimized_params.get('divergence_lookback', 10),
                    'take_profit_ema': optimized_params.get('ema_fast_period', 50)
                }
        except Exception as e:
            print(f"Warning: Could not load ML parameters for {symbol}, using defaults: {e}")
        
        return self.default_params
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _find_significant_lows(self, df: pd.DataFrame, lookback: int) -> list:
        """
        Find significant price lows in the lookback period
        
        Returns:
            list: List of (index, price, rsi) tuples for significant lows
        """
        significant_lows = []
        
        # Look for local minima in the lookback period
        for i in range(1, len(df) - 1):
            current_low = df.iloc[i]['low']
            prev_low = df.iloc[i-1]['low']
            next_low = df.iloc[i+1]['low']
            
            # Check if this is a local low
            if current_low < prev_low and current_low < next_low:
                significant_lows.append((
                    df.index[i],
                    current_low,
                    df.iloc[i]['rsi']
                ))
        
        return significant_lows
    
    def check_signal(self):
        """
        A+ Divergence Capitulation Logic (Exact specification implementation)
        
        1. Trend Context: Confirm downtrend (50 EMA < 200 EMA)
        2. Bullish Divergence: Price lower low + RSI higher low
        3. Capitulation Volume: Volume spike ≥ 3x Volume SMA on divergence low
        4. Entry Signal: First bullish candle after all conditions met
        5. Stop-Loss: Below absolute low of divergence pattern
        6. Take-Profit: At 50 EMA level (mean reversion target)
        
        Returns:
            SignalEvent if A+ setup confirmed, otherwise None
        """
        df = self._get_data(self.timeframe)
        if df.empty or len(df) < 250:  # Need sufficient data for EMAs and divergence
            return None
        
        # Get ML-optimized parameters
        params = self._get_ml_optimized_params(self.symbol)
        
        # Step 1: Add required indicators
        df['rsi'] = self._calculate_rsi(df['close'], params['rsi_period'])
        df['ema_fast'] = df['close'].ewm(span=params['ema_fast_period']).mean()
        df['ema_slow'] = df['close'].ewm(span=params['ema_slow_period']).mean()
        df['volume_sma'] = df['volume'].rolling(params['volume_sma_period']).mean()
        
        # Step 2: Trend Context - Confirm downtrend (A+ specification)
        current_candle = df.iloc[-1]
        is_downtrend = current_candle['ema_fast'] < current_candle['ema_slow']
        
        if not is_downtrend:
            return None
        
        # Step 3: Look for bullish divergence in recent period
        lookback_df = df.iloc[-params['divergence_lookback']:].copy()
        
        if len(lookback_df) < 5:
            return None
        
        # Find significant lows
        significant_lows = self._find_significant_lows(lookback_df, params['divergence_lookback'])
        
        if len(significant_lows) < 2:
            return None
        
        # Get the last two significant lows
        low_1_idx, low_1_price, low_1_rsi = significant_lows[-2]
        low_2_idx, low_2_price, low_2_rsi = significant_lows[-1]
        
        # Step 4: Bullish Divergence Condition (A+ specification)
        price_makes_lower_low = low_2_price < low_1_price
        rsi_makes_higher_low = low_2_rsi > low_1_rsi
        
        is_bullish_divergence = price_makes_lower_low and rsi_makes_higher_low
        
        if not is_bullish_divergence:
            return None
        
        # Step 5: Capitulation Volume Condition (A+ specification: 3x Volume SMA)
        low_2_candle = df.loc[low_2_idx]
        volume_threshold = low_2_candle['volume_sma'] * params['volume_spike_multiplier']
        is_volume_spike = low_2_candle['volume'] > volume_threshold
        
        if not is_volume_spike:
            return None
        
        # Step 6: Entry Signal - First bullish candle after divergence
        # Check if current candle is bullish (close > open)
        is_bullish_entry_candle = current_candle['close'] > current_candle['open']
        
        if not is_bullish_entry_candle:
            return None
        
        # Step 7: A+ Setup Confirmed - Generate Long Signal
        entry_price = current_candle['close']
        stop_loss = low_2_price * 0.99  # Just below divergence low
        take_profit = current_candle['ema_fast']  # A+ spec: Take profit at 50 EMA
        
        # Ensure valid risk-reward (minimum 1:1.5)
        risk_amount = entry_price - stop_loss
        reward_amount = take_profit - entry_price
        
        if reward_amount / risk_amount < 1.5:
            return None  # Skip if risk-reward is poor
        
        signal = SignalEvent(
            symbol=self.symbol,
            signal_type='BUY',
            strategy_id='DIVERGENCE_CAPITULATION_LONG',
            price=entry_price,
            confidence=0.85,  # High confidence A+ setup
            price_target=take_profit,
            stop_loss=stop_loss
        )
        
        print(f"[{pd.Timestamp.now()}] 🎯 DIVERGENCE CAPITULATION LONG: {self.symbol}")
        print(f"   Entry: ${entry_price:.4f} | SL: ${stop_loss:.4f} | TP: ${take_profit:.4f}")
        print(f"   Divergence: Price {low_1_price:.4f}→{low_2_price:.4f} | RSI {low_1_rsi:.1f}→{low_2_rsi:.1f}")
        print(f"   Volume Spike: {low_2_candle['volume']:.0f} vs {volume_threshold:.0f} ({params['volume_spike_multiplier']}x)")
        print(f"   R/R: 1:{reward_amount/risk_amount:.1f}")
        
        return signal
