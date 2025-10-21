#!/usr/bin/env python3
"""
Enhanced Strategy Framework - Uses ML-trained assets to enhance traditional strategies
Provides per-token, per-exchange optimization for improved signal accuracy
"""

import sys
import os
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent
from ml.enhanced_pattern_library import EnhancedPatterns
from ml.pattern_ml_engine import PatternMLEngine
from utils.logger import log as logger
from typing import Optional, Dict, Any

class EnhancedDivergenceCapitulation(BaseStrategy):
    """
    Enhanced Divergence-Confirmed Capitulation Strategy
    Uses ML-trained pattern confidence for specific symbol-exchange combinations
    """
    
    def __init__(self, symbol: str, data: dict, exchange: str = "binanceus"):
        super().__init__(symbol, data)
        self.exchange = exchange
        self.timeframe = '1h'
        self.rsi_period = 14
        self.divergence_lookback = 10
        
        # Initialize enhanced pattern detection
        self.enhanced_patterns = EnhancedPatterns(symbol=symbol, exchange=exchange)
        self.ml_engine = PatternMLEngine()
        
    def check_signal(self) -> Optional[SignalEvent]:
        """
        Enhanced signal detection using ML-trained confidence weights
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

        if not is_capitulation:
            return None
            
        # ML Enhancement: Check for supporting patterns
        pattern_scan = self.enhanced_patterns.scan_all_patterns_enhanced(self.timeframe)
        
        # Base confidence
        base_confidence = 0.75
        
        # Enhance confidence based on detected patterns
        enhanced_confidence = base_confidence
        pattern_boost = 0.0
        
        if pattern_scan['total_patterns'] > 0:
            # Average confidence of all detected patterns
            avg_pattern_confidence = pattern_scan['average_confidence']
            pattern_boost = (avg_pattern_confidence - 0.5) * 0.3  # Up to 30% boost
            enhanced_confidence = min(0.95, base_confidence + pattern_boost)
            
            logger.info(f"🤖 Pattern boost for {self.symbol}/{self.exchange}: "
                       f"+{pattern_boost:.2f} (patterns: {pattern_scan['total_patterns']})")
        
        # ML-enhanced confidence based on trained asset
        final_confidence = self.ml_engine.get_pattern_confidence(
            symbol=self.symbol,
            exchange=self.exchange,
            pattern_name='divergence_capitulation',
            base_confidence=enhanced_confidence,
            timeframe=self.timeframe
        )
        
        price = capitulation_candle['close']
        signal = SignalEvent(
            symbol=self.symbol,
            signal_type='BUY',
            strategy_id='ENHANCED_DIVERGENCE_CAPITULATION',
            price=price,
            confidence=final_confidence,
            price_target=price * 1.07,  # 7% target
            stop_loss=capitulation_candle['low'] * 0.99,
            metadata={
                'base_confidence': base_confidence,
                'pattern_boost': pattern_boost,
                'final_confidence': final_confidence,
                'exchange': self.exchange,
                'detected_patterns': pattern_scan['total_patterns'],
                'enhancement': 'ML_TRAINED'
            }
        )
        
        logger.info(f"[{pd.Timestamp.now()}] 🤖 ENHANCED BUY Signal: {self.symbol} "
                   f"confidence {base_confidence:.2f} -> {final_confidence:.2f}")
        return signal

class EnhancedHTFSweep(BaseStrategy):
    """
    Enhanced HTF Sweep Strategy with ML pattern recognition
    """
    
    def __init__(self, symbol: str, data: dict, exchange: str = "binanceus"):
        super().__init__(symbol, data)
        self.exchange = exchange
        self.htf = '4h'
        self.ltf = '1h'
        
        # Initialize enhanced pattern detection
        self.enhanced_patterns = EnhancedPatterns(symbol=symbol, exchange=exchange)
        self.ml_engine = PatternMLEngine()
        
    def check_signal(self) -> Optional[SignalEvent]:
        """
        Enhanced HTF sweep detection with ML confidence optimization
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

        if not is_ltf_confirmation:
            return None
            
        # ML Enhancement: Check for liquidity sweep patterns
        pattern_scan = self.enhanced_patterns.scan_all_patterns_enhanced(self.ltf)
        
        # Base confidence
        base_confidence = 0.8
        
        # Boost confidence if liquidity sweep pattern detected
        enhanced_confidence = base_confidence
        if 'liquidity_sweep' in pattern_scan.get('patterns', {}):
            liquidity_confidence = pattern_scan['patterns']['liquidity_sweep']['confidence']
            sweep_boost = (liquidity_confidence - 0.5) * 0.4  # Up to 40% boost for liquidity sweeps
            enhanced_confidence = min(0.95, base_confidence + sweep_boost)
            
            logger.info(f"🤖 Liquidity sweep boost for {self.symbol}/{self.exchange}: "
                       f"+{sweep_boost:.2f}")
        
        # ML-enhanced confidence based on trained asset
        final_confidence = self.ml_engine.get_pattern_confidence(
            symbol=self.symbol,
            exchange=self.exchange,
            pattern_name='htf_sweep',
            base_confidence=enhanced_confidence,
            timeframe=self.ltf
        )
        
        price = ltf_last_candle['close']
        signal = SignalEvent(
            symbol=self.symbol,
            signal_type='SELL',
            strategy_id='ENHANCED_HTF_SWEEP',
            price=price,
            confidence=final_confidence,
            price_target=price * 0.95,  # 5% target
            stop_loss=htf_last_candle['high'],  # Stop loss above the sweep high
            metadata={
                'base_confidence': base_confidence,
                'final_confidence': final_confidence,
                'exchange': self.exchange,
                'sweep_high': htf_high_to_sweep,
                'detected_patterns': pattern_scan.get('total_patterns', 0),
                'enhancement': 'ML_TRAINED'
            }
        )
        
        logger.info(f"[{pd.Timestamp.now()}] 🤖 ENHANCED SELL Signal: {self.symbol} "
                   f"confidence {base_confidence:.2f} -> {final_confidence:.2f}")
        return signal

class EnhancedVolumeBreakout(BaseStrategy):
    """
    Enhanced Volume-Confirmed Breakout Strategy with ML volume pattern analysis
    """
    
    def __init__(self, symbol: str, data: dict, exchange: str = "binanceus"):
        super().__init__(symbol, data)
        self.exchange = exchange
        self.timeframe = '1h'
        self.resistance_lookback = 24
        self.volume_sma_period = 20
        self.volume_multiplier = 2.0
        
        # Initialize enhanced pattern detection
        self.enhanced_patterns = EnhancedPatterns(symbol=symbol, exchange=exchange)
        self.ml_engine = PatternMLEngine()
        
    def check_signal(self) -> Optional[SignalEvent]:
        """
        Enhanced volume breakout with ML-optimized volume pattern recognition
        """
        df = self._get_data(self.timeframe)
        if df.empty or len(df) < self.resistance_lookback + 1:
            return None

        # Add indicators to the DataFrame
        df.ta.sma(close=df['volume'], length=self.volume_sma_period, append=True, 
                  col_names=(f'VOL_SMA_{self.volume_sma_period}',))

        # Resistance identification
        lookback_df = df.iloc[-(self.resistance_lookback + 1):-1]
        resistance_high = lookback_df['high'].max()

        last_candle = df.iloc[-1]

        # Condition 1: Breakout
        is_breakout = last_candle['close'] > resistance_high

        # Condition 2: Volume Confirmation
        is_volume_confirmed = last_candle['volume'] > (
            last_candle[f'VOL_SMA_{self.volume_sma_period}'] * self.volume_multiplier
        )

        if not (is_breakout and is_volume_confirmed):
            return None
            
        # ML Enhancement: Check for volume spike patterns
        pattern_scan = self.enhanced_patterns.scan_all_patterns_enhanced(self.timeframe)
        
        # Base confidence
        base_confidence = 0.85
        
        # Boost confidence if volume spike pattern detected
        enhanced_confidence = base_confidence
        volume_boost = 0.0
        
        if 'volume_spike' in pattern_scan.get('patterns', {}):
            volume_pattern = pattern_scan['patterns']['volume_spike']
            volume_ratio = volume_pattern['details']['volume_ratio']
            
            # Higher volume ratios get bigger boost
            volume_boost = min(0.15, (volume_ratio - 2.0) * 0.05)  # Up to 15% boost
            enhanced_confidence = min(0.95, base_confidence + volume_boost)
            
            logger.info(f"🤖 Volume boost for {self.symbol}/{self.exchange}: "
                       f"+{volume_boost:.2f} (volume ratio: {volume_ratio:.1f}x)")
        
        # ML-enhanced confidence based on trained asset
        final_confidence = self.ml_engine.get_pattern_confidence(
            symbol=self.symbol,
            exchange=self.exchange,
            pattern_name='volume_breakout',
            base_confidence=enhanced_confidence,
            timeframe=self.timeframe
        )
        
        price = last_candle['close']
        stop_loss = resistance_high
        price_target = price + (price - stop_loss) * 2  # 1:2 Risk-to-Reward

        signal = SignalEvent(
            symbol=self.symbol,
            signal_type='BUY',
            strategy_id='ENHANCED_VOLUME_BREAKOUT',
            price=price,
            confidence=final_confidence,
            price_target=price_target,
            stop_loss=stop_loss,
            metadata={
                'base_confidence': base_confidence,
                'volume_boost': volume_boost,
                'final_confidence': final_confidence,
                'exchange': self.exchange,
                'resistance_high': resistance_high,
                'volume_ratio': last_candle['volume'] / last_candle[f'VOL_SMA_{self.volume_sma_period}'],
                'detected_patterns': pattern_scan.get('total_patterns', 0),
                'enhancement': 'ML_TRAINED'
            }
        )
        
        logger.info(f"[{pd.Timestamp.now()}] 🤖 ENHANCED BUY Signal: {self.symbol} "
                   f"confidence {base_confidence:.2f} -> {final_confidence:.2f}")
        return signal

class EnhancedStrategyFactory:
    """
    Factory for creating enhanced strategies optimized for specific assets
    """
    
    @staticmethod
    def create_divergence_capitulation(symbol: str, data: dict, exchange: str) -> EnhancedDivergenceCapitulation:
        return EnhancedDivergenceCapitulation(symbol, data, exchange)
    
    @staticmethod
    def create_htf_sweep(symbol: str, data: dict, exchange: str) -> EnhancedHTFSweep:
        return EnhancedHTFSweep(symbol, data, exchange)
    
    @staticmethod
    def create_volume_breakout(symbol: str, data: dict, exchange: str) -> EnhancedVolumeBreakout:
        return EnhancedVolumeBreakout(symbol, data, exchange)
    
    @staticmethod
    def get_all_strategies_for_asset(symbol: str, data: dict, exchange: str) -> Dict[str, BaseStrategy]:
        """Get all enhanced strategies for a specific asset"""
        return {
            'enhanced_divergence_capitulation': EnhancedDivergenceCapitulation(symbol, data, exchange),
            'enhanced_htf_sweep': EnhancedHTFSweep(symbol, data, exchange),
            'enhanced_volume_breakout': EnhancedVolumeBreakout(symbol, data, exchange)
        }

if __name__ == "__main__":
    # Example usage
    print("🤖 Enhanced Strategy System")
    
    # Mock data for testing
    mock_data = {
        '1h': pd.DataFrame({
            'timestamp': range(100),
            'open': [100] * 100,
            'high': [105] * 100,
            'low': [95] * 100,
            'close': [102] * 100,
            'volume': [1000] * 100
        }),
        '4h': pd.DataFrame({
            'timestamp': range(25),
            'open': [100] * 25,
            'high': [108] * 25,
            'low': [92] * 25,
            'close': [104] * 25,
            'volume': [4000] * 25
        })
    }
    
    # Test enhanced strategy
    strategy = EnhancedDivergenceCapitulation("BTC/USDT", mock_data, "binanceus")
    print(f"Strategy created for BTC/USDT on binanceus")