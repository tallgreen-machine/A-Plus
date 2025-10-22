import pandas as pd
import pandas_ta as ta
import numpy as np
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent

class VolumeBreakout(BaseStrategy):
    """
    Volume-Confirmed Breakout Strategy - A+ Setup Implementation
    
    Exact A-Plus Volume Breakout Logic:
    - Range Identification: ATR-based consolidation detection (10+ candles < 1.5x ATR)
    - Volume Baseline: 20-period Volume SMA for confirmation threshold
    - Breakout Signal: Price closes above consolidation high
    - Volume Confirmation: Breakout volume ≥ 2.5x Volume SMA (ML optimized)
    - ML Enhancement: Uses trained asset parameters for optimal thresholds per symbol/exchange
    
    Philosophy: "Patience and Precision" - Only institutional volume-backed breakouts
    """
    def __init__(self, symbol: str, data: dict, trained_assets_manager=None):
        super().__init__(symbol, data)
        self.timeframe = '1h'  # A+ specification timeframe
        self.trained_assets_manager = trained_assets_manager
        
        # Default A+ parameters (will be overridden by ML if available)
        self.default_params = {
            'consolidation_period': 10,      # Minimum candles for range
            'volume_sma_period': 20,         # Volume baseline period
            'volume_multiplier': 2.5,        # A+ specification: 2.5x Volume SMA
            'atr_multiplier': 1.5,           # ATR threshold for consolidation
            'atr_period': 20,                # ATR calculation period
            'risk_reward_ratio': 2.5         # Take-profit calculation
        }

    
    def _get_ml_optimized_params(self, symbol: str, exchange: str = 'binanceus'):
        """Get ML-optimized parameters for volume breakout setup"""
        if not self.trained_assets_manager:
            return self.default_params
        
        try:
            # Get ML-optimized strategy parameters for Volume Breakout
            optimized_params = self.trained_assets_manager.get_strategy_parameters(
                symbol=symbol,
                exchange=exchange,
                strategy_id='volume_breakout'
            )
            
            if optimized_params:
                return {
                    'consolidation_period': optimized_params.get('consolidation_period', 10),
                    'volume_sma_period': optimized_params.get('volume_sma_period', 20),
                    'volume_multiplier': optimized_params.get('volume_confirmation_multiplier', 2.5),
                    'atr_multiplier': optimized_params.get('atr_multiplier', 1.5),
                    'atr_period': 20,
                    'risk_reward_ratio': optimized_params.get('risk_reward_ratio', 2.5)
                }
        except Exception as e:
            print(f"Warning: Could not load ML parameters for {symbol}, using defaults: {e}")
        
        return self.default_params
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close_prev = abs(df['high'] - df['close'].shift(1))
        low_close_prev = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        return true_range.rolling(period).mean()
    
    def _identify_consolidation_range(self, df: pd.DataFrame, params: dict) -> tuple:
        """
        A+ Specification: Identify consolidation range using ATR-based detection
        
        A consolidation is 10+ consecutive candles where each candle's range < 1.5x ATR
        
        Returns:
            tuple: (range_high, range_low, is_valid_consolidation)
        """
        if len(df) < params['consolidation_period'] + params['atr_period']:
            return None, None, False
        
        # Calculate ATR
        df['atr'] = self._calculate_atr(df, params['atr_period'])
        
        # Check recent candles for consolidation
        recent_candles = df.iloc[-(params['consolidation_period'] + 5):-1]  # Extra buffer
        
        consolidation_sequences = []
        current_sequence = []
        
        for i, (idx, candle) in enumerate(recent_candles.iterrows()):
            candle_range = candle['high'] - candle['low']
            atr_threshold = candle['atr'] * params['atr_multiplier']
            
            if candle_range < atr_threshold:
                current_sequence.append(candle)
            else:
                if len(current_sequence) >= params['consolidation_period']:
                    consolidation_sequences.append(current_sequence)
                current_sequence = []
        
        # Check final sequence
        if len(current_sequence) >= params['consolidation_period']:
            consolidation_sequences.append(current_sequence)
        
        if not consolidation_sequences:
            return None, None, False
        
        # Use the most recent valid consolidation
        latest_consolidation = consolidation_sequences[-1]
        consolidation_df = pd.DataFrame(latest_consolidation)
        
        range_high = consolidation_df['high'].max()
        range_low = consolidation_df['low'].min()
        
        return range_high, range_low, True

    def check_signal(self):
        """
        A+ Volume Breakout Logic (Exact specification implementation)
        
        1. Range Identification: Find ATR-based consolidation (10+ candles < 1.5x ATR)
        2. Volume Baseline: Calculate 20-period Volume SMA
        3. Breakout Condition: Current candle closes above consolidation high
        4. Volume Confirmation: Breakout volume ≥ ML-optimized multiplier x Volume SMA
        5. Entry: LONG market order on confirmation
        6. Stop-Loss: Midpoint of consolidation range
        7. Take-Profit: ML-optimized Risk-to-Reward ratio
        
        Returns:
            SignalEvent if A+ setup confirmed, otherwise None
        """
        df = self._get_data(self.timeframe)
        if df.empty or len(df) < 50:  # Need sufficient data for ATR and consolidation
            return None
        
        # Get ML-optimized parameters
        params = self._get_ml_optimized_params(self.symbol)
        
        # Step 1: Identify consolidation range using ATR
        range_high, range_low, is_valid_consolidation = self._identify_consolidation_range(df, params)
        
        if not is_valid_consolidation:
            return None
        
        # Step 2: Calculate Volume SMA baseline
        df['volume_sma'] = df['volume'].rolling(params['volume_sma_period']).mean()
        
        current_candle = df.iloc[-1]
        
        # Step 3: Breakout condition
        is_breakout = current_candle['close'] > range_high
        
        if not is_breakout:
            return None
        
        # Step 4: Volume confirmation (A+ specification: 2.5x Volume SMA)
        volume_threshold = current_candle['volume_sma'] * params['volume_multiplier']
        is_volume_confirmed = current_candle['volume'] > volume_threshold
        
        if not is_volume_confirmed:
            return None
        
        # Step 5: A+ Setup Confirmed - Generate Long Signal
        entry_price = current_candle['close']
        stop_loss = (range_high + range_low) / 2  # Midpoint as per A+ spec
        
        # ML-optimized risk-reward calculation
        risk_amount = entry_price - stop_loss
        take_profit = entry_price + (risk_amount * params['risk_reward_ratio'])
        
        signal = SignalEvent(
            symbol=self.symbol,
            signal_type='BUY',
            strategy_id='VOLUME_BREAKOUT_LONG',
            price=entry_price,
            confidence=0.85,  # High confidence A+ setup
            price_target=take_profit,
            stop_loss=stop_loss
        )
        
        print(f"[{pd.Timestamp.now()}] 🎯 VOLUME BREAKOUT LONG: {self.symbol}")
        print(f"   Entry: ${entry_price:.4f} | SL: ${stop_loss:.4f} | TP: ${take_profit:.4f}")
        print(f"   Range: ${range_low:.4f} - ${range_high:.4f}")
        print(f"   Volume: {current_candle['volume']:.0f} vs {volume_threshold:.0f} ({params['volume_multiplier']}x)")
        print(f"   R/R: 1:{params['risk_reward_ratio']}")
        
        return signal
