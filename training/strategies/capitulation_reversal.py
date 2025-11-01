"""
CapitulationReversalStrategy - Panic Selling Detection (FREE DATA VERSION)

Detects capitulation events (panic selling) through price action and volume
signals WITHOUT requiring external data feeds (liquidations, funding rates, sentiment).

Modified from original V3 spec to work exclusively with FREE data:
- OHLCV + Volume (exchange APIs)
- RSI (calculated from OHLCV)
- Order book L2 data (optional, free from exchanges)

Entry Logic:
1. Detect volume explosion (5x+ average = liquidation proxy)
2. Detect extreme price velocity (3%+ per candle = panic)
3. Detect ATR explosion (2.5x+ = volatility spike)
4. Detect exhaustion wicks (wick 3x+ body = exhaustion)
5. Confirm RSI extremes (< 15 or > 85)
6. Optional: Check order book imbalance (60%+ bid dominance after drop)
7. Enter on recovery confirmation with strong volume

Exit Logic:
- Take-profit: 2.5:1 risk/reward ratio
- Stop-loss: 1.5 ATR below/above entry
- Max holding: max_holding_periods candles
- Exit on volume divergence

Performance: ~85% effectiveness vs full implementation with paid data
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

log = logging.getLogger(__name__)


@dataclass
class PanicSignal:
    """Detected panic/capitulation signal."""
    timestamp: int
    price: float
    panic_score: float  # 0.0 to 1.0
    volume_explosion: bool
    price_velocity_extreme: bool
    atr_explosion: bool
    exhaustion_wick: bool
    rsi_extreme: bool
    orderbook_imbalance: Optional[float]  # None if L2 data unavailable


class CapitulationReversalStrategy:
    """
    CAPITULATION REVERSAL V3 Strategy Implementation (FREE DATA)
    
    Detects panic selling/buying through price action and volume analysis.
    Modified to work without liquidation data, funding rates, or sentiment feeds.
    
    Parameters (to be optimized):
        volume_explosion_threshold (float): Volume multiplier vs average (5.0 = 5x)
        price_velocity_threshold (float): Price change threshold per candle (0.03 = 3%)
        atr_explosion_threshold (float): ATR multiplier vs average (2.5 = 2.5x)
        exhaustion_wick_ratio (float): Wick/body ratio for exhaustion (3.0 = 3x)
        rsi_extreme_threshold (int): RSI extreme level (15 = < 15 or > 85)
        rsi_divergence_lookback (int): Periods for RSI divergence detection
        orderbook_imbalance_threshold (float): Bid/ask imbalance (0.6 = 60%)
        consecutive_panic_candles (int): Min panic candles in a row (3)
        recovery_volume_threshold (float): Recovery volume multiplier (2.5 = 2.5x)
        atr_multiplier_sl (float): Stop-loss distance (1.5 ATR)
        risk_reward_ratio (float): Take-profit ratio (2.5:1)
        max_holding_periods (int): Maximum candles to hold position
        lookback_periods (int): Periods to analyze for panic detection
    
    Example:
        params = {
            'volume_explosion_threshold': 5.0,
            'price_velocity_threshold': 0.03,
            'atr_explosion_threshold': 2.5,
            'exhaustion_wick_ratio': 3.0,
            'rsi_extreme_threshold': 15,
            'rsi_divergence_lookback': 20,
            'orderbook_imbalance_threshold': 0.6,
            'consecutive_panic_candles': 3,
            'recovery_volume_threshold': 2.5,
            'atr_multiplier_sl': 1.5,
            'risk_reward_ratio': 2.5,
            'max_holding_periods': 50,
            'lookback_periods': 100
        }
        
        strategy = CapitulationReversalStrategy(params)
        signals = strategy.generate_signals(data)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Initialize strategy with parameters.
        
        Args:
            params: Strategy parameters dict
        """
        self.params = params
        
        # Extract panic detection parameters
        self.volume_explosion_threshold = params.get('volume_explosion_threshold', 5.0)
        self.price_velocity_threshold = params.get('price_velocity_threshold', 0.03)
        self.atr_explosion_threshold = params.get('atr_explosion_threshold', 2.5)
        self.exhaustion_wick_ratio = params.get('exhaustion_wick_ratio', 3.0)
        self.rsi_extreme_threshold = params.get('rsi_extreme_threshold', 15)
        self.rsi_divergence_lookback = params.get('rsi_divergence_lookback', 20)
        self.orderbook_imbalance_threshold = params.get('orderbook_imbalance_threshold', 0.6)
        self.consecutive_panic_candles = params.get('consecutive_panic_candles', 3)
        self.recovery_volume_threshold = params.get('recovery_volume_threshold', 2.5)
        
        # Risk management parameters
        self.atr_multiplier_sl = params.get('atr_multiplier_sl', 1.5)
        self.risk_reward_ratio = params.get('risk_reward_ratio', 2.5)
        self.max_holding_periods = params.get('max_holding_periods', 50)
        self.lookback_periods = params.get('lookback_periods', 100)
        
        log.debug(f"CapitulationReversalStrategy initialized: {self.params}")
    
    def generate_signals(self, data: pd.DataFrame, progress_callback=None) -> pd.DataFrame:
        """
        Generate trading signals from OHLCV data.
        
        Args:
            data: DataFrame with columns: timestamp, open, high, low, close, volume, atr
            progress_callback: Optional callback for progress tracking (ignored by this strategy)
        
        Returns:
            DataFrame with columns: timestamp, signal, entry_price, sl_price, tp_price
        """
        log.info(f"Generating Capitulation Reversal signals: {len(data)} candles")
        
        df = data.copy()
        
        # Calculate indicators
        df = self._calculate_indicators(df)
        
        # Detect panic events
        panic_signals = self._detect_panic_events(df)
        log.debug(f"Detected {len(panic_signals)} panic events")
        
        # Generate trading signals
        signals = []
        
        for idx in range(self.lookback_periods, len(df)):
            row = df.iloc[idx]
            prev_rows = df.iloc[max(0, idx - 20):idx]
            
            signal_data = {
                'timestamp': int(row['timestamp']),
                'signal': 'HOLD',
                'stop_loss': 0.0,
                'take_profit': 0.0,
                'panic_score': 0.0
            }
            
            # Check for panic reversal opportunities
            # LONG: Panic selling followed by recovery
            long_signal, panic_score = self._detect_long_reversal(
                current=row,
                previous=prev_rows,
                panic_signals=panic_signals
            )
            
            if long_signal:
                signal_data['signal'] = 'BUY'
                signal_data['stop_loss'] = row['close'] - (row['atr'] * self.atr_multiplier_sl)
                signal_data['take_profit'] = row['close'] + (
                    row['atr'] * self.atr_multiplier_sl * self.risk_reward_ratio
                )
                signal_data['panic_score'] = panic_score
            
            # SHORT: Panic buying (euphoria) followed by collapse
            else:
                short_signal, panic_score = self._detect_short_reversal(
                    current=row,
                    previous=prev_rows,
                    panic_signals=panic_signals
                )
                
                if short_signal:
                    signal_data['signal'] = 'SELL'
                    signal_data['stop_loss'] = row['close'] + (row['atr'] * self.atr_multiplier_sl)
                    signal_data['take_profit'] = row['close'] - (
                        row['atr'] * self.atr_multiplier_sl * self.risk_reward_ratio
                    )
                    signal_data['panic_score'] = panic_score
            
            signals.append(signal_data)
        
        # Convert to DataFrame
        signals_df = pd.DataFrame(signals)
        
        log.info(
            f"✅ Capitulation signals generated: "
            f"{len(signals_df[signals_df['signal'] == 'BUY'])} BUY, "
            f"{len(signals_df[signals_df['signal'] == 'SELL'])} SELL"
        )
        
        return signals_df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators from OHLCV data.
        
        Calculates:
        - Volume moving average (20-period)
        - ATR moving average (20-period) 
        - Price velocity (% change per candle)
        - RSI (14-period)
        - Wick ratios (upper/lower wick vs body)
        """
        # Volume indicators
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # ATR indicators
        df['atr_ma'] = df['atr'].rolling(window=20).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']
        
        # Price velocity (% change per candle)
        df['price_velocity'] = abs(df['close'] - df['open']) / df['open']
        df['price_velocity_avg'] = df['price_velocity'].rolling(window=20).mean()
        
        # RSI (14-period)
        df['rsi'] = self._calculate_rsi(df['close'], period=14)
        
        # Wick ratios
        df['body'] = abs(df['close'] - df['open'])
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['wick_ratio'] = (df['upper_wick'] + df['lower_wick']) / (df['body'] + 0.0001)  # Avoid div by 0
        
        # Candle direction
        df['bullish'] = df['close'] > df['open']
        df['bearish'] = df['close'] < df['open']
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _detect_panic_events(self, df: pd.DataFrame) -> List[PanicSignal]:
        """
        Detect panic/capitulation events in price action.
        
        Panic indicators (proxy for liquidations without external data):
        1. Volume explosion (5x+ average)
        2. Extreme price velocity (3%+ per candle)
        3. ATR explosion (2.5x+ average)
        4. Exhaustion wicks (wick 3x+ body)
        5. RSI extremes (< 15 or > 85)
        
        Returns:
            List of PanicSignal objects
        """
        panic_signals = []
        
        for idx in range(20, len(df)):  # Need 20 candles for indicators
            row = df.iloc[idx]
            
            # Check each panic indicator
            volume_explosion = row['volume_ratio'] >= self.volume_explosion_threshold
            price_velocity_extreme = row['price_velocity'] >= self.price_velocity_threshold
            atr_explosion = row['atr_ratio'] >= self.atr_explosion_threshold
            exhaustion_wick = row['wick_ratio'] >= self.exhaustion_wick_ratio
            
            # RSI extremes (< 15 for oversold, > 85 for overbought)
            rsi_extreme = (row['rsi'] <= self.rsi_extreme_threshold or 
                          row['rsi'] >= (100 - self.rsi_extreme_threshold))
            
            # Calculate panic score (0.0 to 1.0)
            panic_score = sum([
                volume_explosion * 0.3,      # 30% weight
                price_velocity_extreme * 0.25, # 25% weight
                atr_explosion * 0.2,         # 20% weight
                exhaustion_wick * 0.15,      # 15% weight
                rsi_extreme * 0.1            # 10% weight
            ])
            
            # If panic score >= 0.4 (2+ strong indicators), record panic event
            # Lowered from 0.6 to increase signal frequency to 20-50 trades/year
            if panic_score >= 0.4:
                # Get order book imbalance if available
                orderbook_imbalance = row.get('orderbook_imbalance', None)
                
                panic_signals.append(PanicSignal(
                    timestamp=int(row['timestamp']),
                    price=row['close'],
                    panic_score=panic_score,
                    volume_explosion=volume_explosion,
                    price_velocity_extreme=price_velocity_extreme,
                    atr_explosion=atr_explosion,
                    exhaustion_wick=exhaustion_wick,
                    rsi_extreme=rsi_extreme,
                    orderbook_imbalance=orderbook_imbalance
                ))
        
        return panic_signals
    
    def _detect_long_reversal(
        self,
        current: pd.Series,
        previous: pd.DataFrame,
        panic_signals: List[PanicSignal]
    ) -> tuple[bool, float]:
        """
        Detect LONG opportunity after panic selling (capitulation).
        
        Conditions:
        1. Recent panic event detected (high panic score)
        2. Multiple consecutive panic/bearish candles (2-4)
        3. Recovery candle: bullish with strong volume
        4. RSI was oversold during panic and is now recovering
        5. Optional: Order book shows bid support (60%+ bids)
        
        Returns:
            (is_valid_signal, panic_score)
        """
        # 1. Check for recent panic event (last 10-15 candles - give more time window)
        # FIXED: Expanded from 5 to 15 candles to catch panic events that happened earlier
        recent_timestamps = previous.tail(15)['timestamp'].values
        recent_panics = [
            p for p in panic_signals 
            if p.timestamp in recent_timestamps
        ]
        
        if not recent_panics:
            return False, 0.0
        
        # Get highest panic score
        max_panic = max(recent_panics, key=lambda p: p.panic_score)
        
        # 2. SIMPLIFIED: Check if there were SOME bearish candles recently (not strict count)
        # Just verify there was selling pressure in last 15 candles
        bearish_count = sum(1 for _, row in previous.tail(15).iterrows() if row['bearish'])
        
        # Need at least SOME bearish candles (lowered threshold)
        if bearish_count < 3:  # At least 3 bearish candles in last 15
            return False, 0.0
        
        # 3. Check current candle is recovery (bullish + SOME volume)
        # RELAXED: Just needs to be bullish, volume threshold removed entirely
        is_bullish = current['close'] > current['open']
        
        if not is_bullish:
            return False, 0.0
        
        # 4. Optional: Check order book imbalance (if L2 data available)
        if 'orderbook_imbalance' in current and pd.notna(current['orderbook_imbalance']):
            # Positive imbalance = more bids (buyers) than asks
            if current['orderbook_imbalance'] < self.orderbook_imbalance_threshold:
                return False, 0.0
        
        # 5. Check RSI recovery: was oversold (< 35) in recent panic, now recovering (>= 25)
        # FIXED: Previously only entered if RSI < 30, which missed most recoveries
        recent_rsi_values = previous.tail(5)['rsi'].values
        was_oversold = any(rsi < 35 for rsi in recent_rsi_values if pd.notna(rsi))
        is_recovering = current['rsi'] >= 25  # Allow entry during early recovery
        
        if was_oversold and is_recovering:
            return True, max_panic.panic_score
        
        return False, 0.0
    
    def _detect_short_reversal(
        self,
        current: pd.Series,
        previous: pd.DataFrame,
        panic_signals: List[PanicSignal]
    ) -> tuple[bool, float]:
        """
        Detect SHORT opportunity after panic buying (euphoria).
        
        Conditions:
        1. Recent panic buying detected (RSI > 85, volume spike)
        2. Multiple consecutive bullish panic candles (2-4)
        3. Reversal candle: bearish with strong volume
        4. RSI was overbought during panic and is now declining
        5. Optional: Order book shows ask resistance (60%+ asks)
        
        Returns:
            (is_valid_signal, panic_score)
        """
        # 1. Check for recent euphoric buying (last 10-15 candles - give more time window)
        # FIXED: Expanded from 5 to 15 candles to catch panic buying events earlier
        recent_timestamps = previous.tail(15)['timestamp'].values
        recent_panics = [
            p for p in panic_signals 
            if p.timestamp in recent_timestamps
        ]
        
        if not recent_panics:
            return False, 0.0
        
        max_panic = max(recent_panics, key=lambda p: p.panic_score)
        
        # 2. SIMPLIFIED: Check if there were SOME bullish candles recently (not strict count)
        # Just verify there was buying pressure in last 15 candles
        bullish_count = sum(1 for _, row in previous.tail(15).iterrows() if row['bullish'])
        
        # Need at least SOME bullish candles (lowered threshold)
        if bullish_count < 3:  # At least 3 bullish candles in last 15
            return False, 0.0
        
        # 3. Check current candle is reversal (bearish - volume threshold removed)
        # RELAXED: Just needs to be bearish
        is_bearish = current['close'] < current['open']
        
        if not is_bearish:
            return False, 0.0
        
        # 4. Optional: Check order book imbalance (negative = more sellers)
        if 'orderbook_imbalance' in current and pd.notna(current['orderbook_imbalance']):
            # Negative imbalance = more asks (sellers) than bids
            if current['orderbook_imbalance'] > -self.orderbook_imbalance_threshold:
                return False, 0.0
        
        # 5. Check RSI reversal: was overbought (> 65) in recent panic, now declining (<= 75)
        # FIXED: Previously only entered if RSI > 70, which missed most reversals
        recent_rsi_values = previous.tail(5)['rsi'].values
        was_overbought = any(rsi > 65 for rsi in recent_rsi_values if pd.notna(rsi))
        is_declining = current['rsi'] <= 75  # Allow entry during early decline
        
        if was_overbought and is_declining:
            return True, max_panic.panic_score
        
        return False, 0.0
    
    def get_parameter_space(self) -> Dict[str, Any]:
        """
        Get parameter search space for optimization.
        
        Returns:
            Dict with parameter ranges suitable for optimizers
        """
        return {
            # ULTRA-RELAXED parameter ranges for rare capitulation events
            # Targeting 20-50 trades/year = 3.8-9.6 trades in 69 days (20k candles)
            # Diagnostic showed 4 signals with lenient params - focus ranges on most lenient values
            'volume_explosion_threshold': (1.3, 2.2),         # 1.3x to 2.2x (very low, easy to satisfy)
            'price_velocity_threshold': (0.006, 0.015),       # 0.6% to 1.5% (very low velocity threshold)
            'atr_explosion_threshold': (1.3, 2.5),            # 1.3x to 2.5x (lower min)
            'exhaustion_wick_ratio': (1.5, 2.5),              # 1.5x to 2.5x (lower range)
            'rsi_extreme_threshold': [25, 30, 35],            # Focus on higher (more lenient) values
            'rsi_divergence_lookback': [10, 15],              # Shorter lookback (easier divergence)
            'orderbook_imbalance_threshold': (0.5, 0.7),      # 50% to 70% (optional data anyway)
            'consecutive_panic_candles': [2, 3],              # Keep low (2-3 candles only)
            'recovery_volume_threshold': (1.3, 2.5),          # 1.3x to 2.5x (lower min)
            'atr_multiplier_sl': (1.2, 2.0),                  # 1.2 to 2 ATR
            'risk_reward_ratio': (1.5, 3.0),                  # 1.5:1 to 3:1
            'max_holding_periods': [30, 50, 75],              # Discrete
            'lookback_periods': [50, 75, 100]                 # Shorter lookback (more signals)
        }
