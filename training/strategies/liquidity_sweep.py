"""
LiquiditySweepStrategy - Key Level Pierce Detection

Detects liquidity sweeps (stop hunts) where price pierces a key level,
triggers stops, then reverses direction with volume confirmation.

Entry Logic:
1. Identify key support/resistance levels
2. Detect pierce through level (pierce_depth)
3. Confirm volume spike (volume_spike_threshold × average)
4. Confirm reversal candles (rejection pattern)
5. Enter on reversal confirmation

Exit Logic:
- Take-profit: risk_reward_ratio × stop_distance
- Stop-loss: stop_distance below/above entry
- Max holding: max_holding_periods candles
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
import logging

log = logging.getLogger(__name__)


@dataclass
class KeyLevel:
    """Identified support/resistance level."""
    price: float
    strength: int  # Number of touches
    type: str      # 'SUPPORT' or 'RESISTANCE'


class LiquiditySweepStrategy:
    """
    LIQUIDITY SWEEP V3 Strategy Implementation
    
    Detects and trades liquidity sweeps (stop hunts) at key levels.
    
    Parameters (to be optimized):
        pierce_depth (float): Pierce depth as fraction (0.001 = 0.1%)
        volume_spike_threshold (float): Volume multiplier vs average (2.0 = 2x)
        reversal_candles (int): Required reversal candles (1-5)
        min_distance_from_level (float): Minimum distance to consider level valid
        atr_multiplier_sl (float): Stop-loss distance (ATR multiplier)
        risk_reward_ratio (float): Take-profit ratio (1.5 = 1.5:1)
        max_holding_periods (int): Maximum candles to hold position
        key_level_lookback (int): Periods to look back for key levels
        min_level_touches (int): Minimum touches to qualify as key level
    
    Example:
        params = {
            'pierce_depth': 0.002,           # 0.2%
            'volume_spike_threshold': 2.5,   # 2.5x volume
            'reversal_candles': 2,
            'min_distance_from_level': 0.001,
            'atr_multiplier_sl': 1.5,
            'risk_reward_ratio': 2.0,
            'max_holding_periods': 30,
            'key_level_lookback': 100,
            'min_level_touches': 3
        }
        
        strategy = LiquiditySweepStrategy(params)
        signals = strategy.generate_signals(data)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Initialize strategy with parameters.
        
        Args:
            params: Strategy parameters dict
        """
        self.params = params
        
        # Extract parameters
        self.pierce_depth = params.get('pierce_depth', 0.002)
        self.volume_spike_threshold = params.get('volume_spike_threshold', 2.0)
        self.reversal_candles = params.get('reversal_candles', 2)
        self.min_distance_from_level = params.get('min_distance_from_level', 0.001)
        self.atr_multiplier_sl = params.get('atr_multiplier_sl', 1.5)
        self.risk_reward_ratio = params.get('risk_reward_ratio', 2.0)
        self.max_holding_periods = params.get('max_holding_periods', 30)
        self.key_level_lookback = params.get('key_level_lookback', 100)
        self.min_level_touches = params.get('min_level_touches', 3)
        
        log.debug(f"LiquiditySweepStrategy initialized: {self.params}")
    
    def generate_signals(self, data: pd.DataFrame, progress_callback: callable = None) -> pd.DataFrame:
        """
        Generate trading signals from OHLCV data.
        
        Args:
            data: DataFrame with columns:
                  timestamp, open, high, low, close, volume, atr
            progress_callback: Optional callback(current, total, phase) 
                               Called periodically during signal generation
        
        Returns:
            DataFrame with columns:
                timestamp, signal, stop_loss, take_profit
                
                signal values:
                - 'BUY': Long entry
                - 'SELL': Short entry  
                - 'HOLD': No action
        """
        log.info(f"Generating signals: {len(data)} candles")
        
        df = data.copy()
        
        # Step 1: Identify key levels
        key_levels = self._identify_key_levels(df)
        log.debug(f"Found {len(key_levels)} key levels")
        
        # Step 2: Calculate volume average
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        # Step 3: Detect liquidity sweeps
        signals = []
        total_candles = len(df) - self.key_level_lookback
        
        # Pre-calculate price ranges for faster level filtering
        price_tolerance = df['atr'].median() * 3  # Only check levels within 3 ATR
        
        for i, idx in enumerate(range(self.key_level_lookback, len(df))):
            # Report progress every 100 candles (more frequent for visibility)
            if progress_callback and i > 0 and i % 100 == 0:
                progress_callback(i, total_candles, 'signal_generation')
            
            row = df.iloc[idx]
            prev_rows = df.iloc[max(0, idx - 10):idx]
            
            signal_data = {
                'timestamp': int(row['timestamp']),
                'signal': 'HOLD',
                'stop_loss': 0.0,
                'take_profit': 0.0
            }
            
            # Filter key levels to only those near current price (optimization)
            price_min = row['close'] - price_tolerance
            price_max = row['close'] + price_tolerance
            relevant_levels = [lvl for lvl in key_levels if price_min <= lvl.price <= price_max]
            
            # Check for liquidity sweep at each relevant key level
            for level in relevant_levels:
                # LONG setup: Pierce below support, then reverse up
                if level.type == 'SUPPORT':
                    sweep = self._detect_long_sweep(
                        current=row,
                        previous=prev_rows,
                        level=level
                    )
                    
                    if sweep:
                        signal_data['signal'] = 'BUY'
                        signal_data['stop_loss'] = row['close'] - (row['atr'] * self.atr_multiplier_sl)
                        signal_data['take_profit'] = row['close'] + (
                            row['atr'] * self.atr_multiplier_sl * self.risk_reward_ratio
                        )
                        break
                
                # SHORT setup: Pierce above resistance, then reverse down
                elif level.type == 'RESISTANCE':
                    sweep = self._detect_short_sweep(
                        current=row,
                        previous=prev_rows,
                        level=level
                    )
                    
                    if sweep:
                        signal_data['signal'] = 'SELL'
                        signal_data['stop_loss'] = row['close'] + (row['atr'] * self.atr_multiplier_sl)
                        signal_data['take_profit'] = row['close'] - (
                            row['atr'] * self.atr_multiplier_sl * self.risk_reward_ratio
                        )
                        break
            
            signals.append(signal_data)
        
        # Convert to DataFrame
        signals_df = pd.DataFrame(signals)
        
        log.info(
            f"✅ Signals generated: "
            f"{len(signals_df[signals_df['signal'] == 'BUY'])} BUY, "
            f"{len(signals_df[signals_df['signal'] == 'SELL'])} SELL"
        )
        
        return signals_df
    
    def _identify_key_levels(self, df: pd.DataFrame) -> List[KeyLevel]:
        """
        Identify key support/resistance levels.
        
        Uses swing high/low detection with minimum touches requirement.
        
        Returns:
            List of KeyLevel objects
        """
        levels = []
        lookback = self.key_level_lookback
        
        # Find swing highs and lows
        df['swing_high'] = (
            (df['high'] > df['high'].shift(1)) &
            (df['high'] > df['high'].shift(2)) &
            (df['high'] > df['high'].shift(-1)) &
            (df['high'] > df['high'].shift(-2))
        )
        
        df['swing_low'] = (
            (df['low'] < df['low'].shift(1)) &
            (df['low'] < df['low'].shift(2)) &
            (df['low'] < df['low'].shift(-1)) &
            (df['low'] < df['low'].shift(-2))
        )
        
        # Get swing prices
        swing_highs = df[df['swing_high']]['high'].values
        swing_lows = df[df['swing_low']]['low'].values
        
        # Cluster swing points into levels (within min_distance)
        # Resistance levels (from swing highs)
        resistance_clusters = self._cluster_prices(swing_highs)
        for price, count in resistance_clusters:
            if count >= self.min_level_touches:
                levels.append(KeyLevel(
                    price=price,
                    strength=count,
                    type='RESISTANCE'
                ))
        
        # Support levels (from swing lows)
        support_clusters = self._cluster_prices(swing_lows)
        for price, count in support_clusters:
            if count >= self.min_level_touches:
                levels.append(KeyLevel(
                    price=price,
                    strength=count,
                    type='SUPPORT'
                ))
        
        return levels
    
    def _cluster_prices(self, prices: np.ndarray) -> List[tuple]:
        """
        Cluster prices within min_distance into levels.
        
        Returns:
            List of (cluster_price, count) tuples
        """
        if len(prices) == 0:
            return []
        
        prices_sorted = np.sort(prices)
        clusters = []
        current_cluster = [prices_sorted[0]]
        
        for price in prices_sorted[1:]:
            # If within min_distance, add to current cluster
            if abs(price - np.mean(current_cluster)) / np.mean(current_cluster) <= self.min_distance_from_level:
                current_cluster.append(price)
            else:
                # Save current cluster, start new one
                clusters.append((np.mean(current_cluster), len(current_cluster)))
                current_cluster = [price]
        
        # Add last cluster
        if current_cluster:
            clusters.append((np.mean(current_cluster), len(current_cluster)))
        
        return clusters
    
    def _detect_long_sweep(
        self,
        current: pd.Series,
        previous: pd.DataFrame,
        level: KeyLevel
    ) -> bool:
        """
        Detect LONG liquidity sweep setup.
        
        Conditions:
        1. Previous candle(s) pierced below support
        2. Volume spike during pierce
        3. Current candle(s) show reversal back above support
        4. Reversal candles meet minimum count requirement
        
        Returns:
            True if valid long sweep detected
        """
        # 1. Check if recent candles pierced below level
        pierce_distance = level.price * self.pierce_depth
        pierced_recently = any(
            row['low'] <= (level.price - pierce_distance)
            for _, row in previous.tail(self.reversal_candles + 1).iterrows()
        )
        
        if not pierced_recently:
            return False
        
        # 2. Check volume spike during pierce
        volume_spiked = any(
            row['volume'] >= (row.get('volume_ma', row['volume']) * self.volume_spike_threshold)
            for _, row in previous.tail(self.reversal_candles + 1).iterrows()
        )
        
        if not volume_spiked:
            return False
        
        # 3. Check reversal: current close above level
        if current['close'] <= level.price:
            return False
        
        # 4. Check reversal strength: bullish candle(s)
        reversal_count = 0
        for _, row in previous.tail(self.reversal_candles).iterrows():
            if row['close'] > row['open']:  # Bullish candle
                reversal_count += 1
        
        # Add current candle
        if current['close'] > current['open']:
            reversal_count += 1
        
        if reversal_count < self.reversal_candles:
            return False
        
        return True
    
    def _detect_short_sweep(
        self,
        current: pd.Series,
        previous: pd.DataFrame,
        level: KeyLevel
    ) -> bool:
        """
        Detect SHORT liquidity sweep setup.
        
        Conditions:
        1. Previous candle(s) pierced above resistance
        2. Volume spike during pierce
        3. Current candle(s) show reversal back below resistance
        4. Reversal candles meet minimum count requirement
        
        Returns:
            True if valid short sweep detected
        """
        # 1. Check if recent candles pierced above level
        pierce_distance = level.price * self.pierce_depth
        pierced_recently = any(
            row['high'] >= (level.price + pierce_distance)
            for _, row in previous.tail(self.reversal_candles + 1).iterrows()
        )
        
        if not pierced_recently:
            return False
        
        # 2. Check volume spike during pierce
        volume_spiked = any(
            row['volume'] >= (row.get('volume_ma', row['volume']) * self.volume_spike_threshold)
            for _, row in previous.tail(self.reversal_candles + 1).iterrows()
        )
        
        if not volume_spiked:
            return False
        
        # 3. Check reversal: current close below level
        if current['close'] >= level.price:
            return False
        
        # 4. Check reversal strength: bearish candle(s)
        reversal_count = 0
        for _, row in previous.tail(self.reversal_candles).iterrows():
            if row['close'] < row['open']:  # Bearish candle
                reversal_count += 1
        
        # Add current candle
        if current['close'] < current['open']:
            reversal_count += 1
        
        if reversal_count < self.reversal_candles:
            return False
        
        return True
    
    def get_parameter_space(self) -> Dict[str, Any]:
        """
        Get parameter search space for optimization.
        
        Returns:
            Dict with parameter ranges suitable for optimizers
        """
        return {
            'pierce_depth': (0.0005, 0.005),          # 0.05% to 0.5%
            'volume_spike_threshold': (1.5, 5.0),     # 1.5x to 5x
            'reversal_candles': [1, 2, 3, 4, 5],      # Discrete
            'min_distance_from_level': (0.0005, 0.003), # 0.05% to 0.3%
            'atr_multiplier_sl': (1.0, 3.0),          # 1 to 3 ATR
            'risk_reward_ratio': (1.5, 4.0),          # 1.5:1 to 4:1
            'max_holding_periods': [10, 20, 30, 50, 100],  # Discrete
            'key_level_lookback': [50, 100, 150, 200], # Discrete
            'min_level_touches': [2, 3, 4, 5]         # Discrete
        }
