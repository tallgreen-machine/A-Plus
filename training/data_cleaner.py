"""
Data Quality Cleaner - Intelligent Filtering of Invalid Candles

Removes problematic candles that degrade training quality:
- Zero volume candles (no trades occurred)
- Low volume candles (insufficient liquidity)
- Flat candles (price didn't move)
- Micro-movement candles (< 0.01% change)

Configurable thresholds allow experimentation to find optimal cleaning.

Example:
    cleaner = DataCleaner(config={
        'enable_filtering': True,
        'min_volume_threshold': 0.1,
        'min_price_movement_pct': 0.01,
        'filter_flat_candles': True
    })
    
    filtered_df, stats = cleaner.clean(candles_df)
    print(f"Removed {stats['removed_count']} invalid candles ({stats['removed_pct']:.1f}%)")
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging

log = logging.getLogger(__name__)


class DataCleaner:
    """
    Filters invalid/problematic candles from OHLCV data.
    
    Configurable filtering with detailed statistics and validation.
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        'enable_filtering': True,
        'min_volume_threshold': 0.1,        # SOL traded (adjust per asset)
        'min_price_movement_pct': 0.01,     # 0.01% = 1 basis point
        'filter_flat_candles': True,         # Remove O=H=L=C candles
        'preserve_high_volume_single_price': True  # Keep single-price trades if volume > 1.0
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DataCleaner with configuration.
        
        Args:
            config: Dictionary with filtering parameters:
                - enable_filtering (bool): Master switch
                - min_volume_threshold (float): Minimum volume to keep
                - min_price_movement_pct (float): Minimum price movement (e.g., 0.01 = 1%)
                - filter_flat_candles (bool): Remove O=H=L=C candles
                - preserve_high_volume_single_price (bool): Keep flat candles if volume > 1.0
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        log.info(f"DataCleaner initialized: {self.config}")
    
    def clean(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Clean OHLCV dataframe by removing invalid candles.
        
        Args:
            df: DataFrame with columns: timestamp, open, high, low, close, volume
        
        Returns:
            Tuple of (cleaned_df, statistics_dict):
                - cleaned_df: Filtered dataframe
                - statistics_dict: Detailed breakdown of what was removed
        
        Raises:
            ValueError: If dataframe is empty or missing required columns
        """
        # Validate input
        if df is None or len(df) == 0:
            raise ValueError("Cannot clean empty dataframe")
        
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # If filtering disabled, return original with stats
        if not self.config['enable_filtering']:
            return df.copy(), {
                'filtering_enabled': False,
                'original_count': len(df),
                'filtered_count': len(df),
                'removed_count': 0,
                'removed_pct': 0.0
            }
        
        original_count = len(df)
        log.info(f"Cleaning {original_count} candles with config: {self.config}")
        
        # Track removal reasons
        removal_reasons = {
            'zero_volume': 0,
            'insufficient_volume': 0,
            'flat_low_volume': 0,
            'insufficient_movement': 0,
            'valid_single_price': 0,  # Kept despite being flat
            'valid': 0
        }
        
        # Apply filters row by row
        keep_mask = []
        
        for idx, row in df.iterrows():
            is_valid, reason = self._is_valid_candle(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            removal_reasons[reason] += 1
            keep_mask.append(is_valid)
        
        # Filter dataframe
        filtered_df = df[keep_mask].copy()
        removed_count = original_count - len(filtered_df)
        
        # Calculate statistics
        stats = {
            'filtering_enabled': True,
            'config': self.config,
            'original_count': original_count,
            'filtered_count': len(filtered_df),
            'removed_count': removed_count,
            'removed_pct': (removed_count / original_count * 100) if original_count > 0 else 0.0,
            'removal_breakdown': removal_reasons,
            'removal_breakdown_pct': {
                k: (v / original_count * 100) if original_count > 0 else 0.0
                for k, v in removal_reasons.items()
            },
            'data_quality_score': self._calculate_quality_score(removal_reasons, original_count)
        }
        
        # Log summary
        self._log_summary(stats)
        
        return filtered_df, stats
    
    def _is_valid_candle(
        self,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float
    ) -> Tuple[bool, str]:
        """
        Determine if a single candle should be kept or filtered.
        
        Args:
            open_price, high, low, close, volume: OHLCV values
        
        Returns:
            Tuple of (is_valid, reason):
                - is_valid (bool): True to keep, False to remove
                - reason (str): Classification reason for statistics
        """
        # Criterion 1: Absolute zero volume
        if volume == 0:
            return False, 'zero_volume'
        
        # Criterion 2: Volume too low to be meaningful
        if volume < self.config['min_volume_threshold']:
            return False, 'insufficient_volume'
        
        # Criterion 3: Completely flat (all prices identical)
        is_flat = (open_price == high == low == close)
        
        if is_flat:
            # Special case: High volume single-price trades are legitimate
            if self.config['preserve_high_volume_single_price'] and volume >= 1.0:
                return True, 'valid_single_price'
            else:
                return False, 'flat_low_volume'
        
        # Criterion 4: Price movement too small (likely noise or manipulation)
        if self.config['filter_flat_candles']:
            price_range = high - low
            
            # Avoid division by zero
            if open_price > 0:
                price_movement_pct = (price_range / open_price) * 100
            else:
                # If open is 0 (invalid data), remove it
                return False, 'insufficient_movement'
            
            if price_movement_pct < self.config['min_price_movement_pct']:
                return False, 'insufficient_movement'
        
        return True, 'valid'
    
    def _calculate_quality_score(self, removal_reasons: Dict[str, int], total: int) -> float:
        """
        Calculate data quality score (0-100) based on valid candles.
        
        Higher is better. 100 = all candles valid.
        """
        if total == 0:
            return 0.0
        
        valid_count = removal_reasons.get('valid', 0) + removal_reasons.get('valid_single_price', 0)
        return (valid_count / total) * 100
    
    def _log_summary(self, stats: Dict[str, Any]):
        """Log human-readable summary of cleaning results."""
        log.info("=" * 80)
        log.info("DATA CLEANING SUMMARY")
        log.info("=" * 80)
        log.info(f"Original candles:  {stats['original_count']:,}")
        log.info(f"Filtered candles:  {stats['filtered_count']:,}")
        log.info(f"Removed candles:   {stats['removed_count']:,} ({stats['removed_pct']:.1f}%)")
        log.info(f"Data quality score: {stats['data_quality_score']:.1f}%")
        log.info("")
        log.info("Removal Breakdown:")
        
        breakdown = stats['removal_breakdown']
        breakdown_pct = stats['removal_breakdown_pct']
        
        log.info(f"  ✓ Valid candles:          {breakdown['valid']:,} ({breakdown_pct['valid']:.1f}%)")
        log.info(f"  ✓ Valid single-price:     {breakdown['valid_single_price']:,} ({breakdown_pct['valid_single_price']:.1f}%)")
        log.info(f"  ✗ Zero volume:            {breakdown['zero_volume']:,} ({breakdown_pct['zero_volume']:.1f}%)")
        log.info(f"  ✗ Insufficient volume:    {breakdown['insufficient_volume']:,} ({breakdown_pct['insufficient_volume']:.1f}%)")
        log.info(f"  ✗ Flat (low volume):      {breakdown['flat_low_volume']:,} ({breakdown_pct['flat_low_volume']:.1f}%)")
        log.info(f"  ✗ Insufficient movement:  {breakdown['insufficient_movement']:,} ({breakdown_pct['insufficient_movement']:.1f}%)")
        log.info("=" * 80)
    
    def validate_sample(self, df: pd.DataFrame, sample_size: int = 10) -> Dict[str, Any]:
        """
        Inspect a random sample of candles for manual validation.
        
        Useful for debugging and understanding what's being filtered.
        
        Args:
            df: Original (unfiltered) dataframe
            sample_size: Number of candles to sample
        
        Returns:
            Dictionary with sample inspection results
        """
        if len(df) == 0:
            return {'error': 'Empty dataframe'}
        
        # Sample random candles
        sample = df.sample(min(sample_size, len(df)))
        
        inspections = []
        for idx, row in sample.iterrows():
            is_valid, reason = self._is_valid_candle(
                row['open'], row['high'], row['low'], row['close'], row['volume']
            )
            
            inspections.append({
                'timestamp': row['timestamp'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
                'is_valid': is_valid,
                'reason': reason,
                'price_range': row['high'] - row['low'],
                'price_movement_pct': ((row['high'] - row['low']) / row['open'] * 100) if row['open'] > 0 else 0
            })
        
        return {
            'sample_size': len(inspections),
            'inspections': inspections
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration (merge with existing)."""
        self.config.update(new_config)
        log.info(f"Config updated: {self.config}")


# =============================================================================
# Utility Functions
# =============================================================================

def quick_clean(
    df: pd.DataFrame,
    enable: bool = True,
    min_volume: float = 0.1,
    min_movement: float = 0.01
) -> pd.DataFrame:
    """
    Quick cleaning with default settings (convenience function).
    
    Args:
        df: OHLCV dataframe
        enable: Enable filtering
        min_volume: Minimum volume threshold
        min_movement: Minimum price movement %
    
    Returns:
        Cleaned dataframe (without statistics)
    """
    cleaner = DataCleaner({
        'enable_filtering': enable,
        'min_volume_threshold': min_volume,
        'min_price_movement_pct': min_movement
    })
    
    cleaned_df, _ = cleaner.clean(df)
    return cleaned_df


def analyze_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze data quality without filtering (diagnostic tool).
    
    Args:
        df: OHLCV dataframe
    
    Returns:
        Quality metrics and statistics
    """
    if len(df) == 0:
        return {'error': 'Empty dataframe'}
    
    zero_volume = (df['volume'] == 0).sum()
    flat_candles = ((df['open'] == df['high']) & 
                    (df['high'] == df['low']) & 
                    (df['low'] == df['close'])).sum()
    
    # Calculate price movement for each candle
    price_movements = ((df['high'] - df['low']) / df['open'] * 100).replace([np.inf, -np.inf], 0)
    micro_movements = (price_movements < 0.01).sum()
    
    low_volume = (df['volume'] < 0.1).sum()
    
    return {
        'total_candles': len(df),
        'zero_volume': int(zero_volume),
        'zero_volume_pct': float(zero_volume / len(df) * 100),
        'flat_candles': int(flat_candles),
        'flat_candles_pct': float(flat_candles / len(df) * 100),
        'low_volume': int(low_volume),
        'low_volume_pct': float(low_volume / len(df) * 100),
        'micro_movements': int(micro_movements),
        'micro_movements_pct': float(micro_movements / len(df) * 100),
        'avg_volume': float(df['volume'].mean()),
        'median_volume': float(df['volume'].median()),
        'avg_price_movement_pct': float(price_movements.mean()),
        'quality_estimate': float(100 - (zero_volume + flat_candles) / len(df) * 100)
    }
