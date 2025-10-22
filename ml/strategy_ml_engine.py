#!/usr/bin/env python3
"""
Pattern ML Engine - Trains pattern recognition models per token and per exchange
Creates "trained assets" - ML models optimized for specific symbol-exchange combinations
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Add project paths
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

from shared.db import get_db_conn
from policy.pattern_library import Tier1Patterns
from utils.logger import log as logger

@dataclass
class TrainedAsset:
    """Represents a trained ML model for a specific symbol-exchange combination"""
    symbol: str
    exchange: str
    timeframe: str
    pattern_weights: Dict[str, float]  # Pattern name -> confidence multiplier
    model_version: str
    training_date: datetime
    performance_metrics: Dict[str, float]
    
class PatternMLEngine:
    """
    ML Engine that creates trained assets - pattern recognition models 
    optimized per token and per exchange combination
    """
    
    def __init__(self):
        self.db_conn = get_db_conn()
        self.pattern_detector = Tier1Patterns()
        self.trained_assets = {}  # (symbol, exchange, timeframe) -> TrainedAsset
        self.models_dir = "/workspaces/Trad/models"
        os.makedirs(self.models_dir, exist_ok=True)
        
    def get_available_assets(self) -> List[Tuple[str, str]]:
        """Get all symbol-exchange combinations available for training"""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT symbol, exchange 
                FROM market_data_enhanced 
                ORDER BY exchange, symbol
            """)
            return cur.fetchall()
    
    def extract_pattern_features(self, symbol: str, exchange: str, timeframe: str = '5m', 
                                lookback_days: int = 30) -> pd.DataFrame:
        """
        Extract pattern features for a specific symbol-exchange combination
        Returns DataFrame with pattern detections and forward returns
        """
        # Fetch historical data for this specific asset
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM market_data_enhanced
                WHERE symbol = %s AND exchange = %s AND timeframe = %s
                AND timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp ASC
            """, (symbol, exchange, timeframe, start_date, end_date))
            
            data = cur.fetchall()
        
        if not data:
            logger.warning(f"No data found for {symbol} on {exchange} timeframe {timeframe}")
            return pd.DataFrame()
            
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        # Initialize pattern detector for this specific asset
        asset_pattern_detector = Tier1Patterns(symbol=symbol)
        asset_pattern_detector.db_conn = self.db_conn
        
        # Extract pattern features
        pattern_features = []
        
        for i in range(20, len(df) - 10):  # Leave buffer for lookback and forward returns
            window_end = i
            timestamp = df.iloc[i]['timestamp']
            
            # Simulate pattern detection at this point in time
            # (In real implementation, this would be more sophisticated)
            
            # Basic pattern signals (simplified for demo)
            features = {
                'timestamp': timestamp,
                'symbol': symbol,
                'exchange': exchange,
                'timeframe': timeframe,
                'price': df.iloc[i]['close'],
            }
            
            # Add pattern detection results
            # Liquidity Sweep detection (simplified)
            recent_lows = df.iloc[i-10:i]['low']
            current_low = df.iloc[i]['low']
            is_liquidity_sweep = current_low < recent_lows.quantile(0.1)
            features['liquidity_sweep'] = 1 if is_liquidity_sweep else 0
            
            # Fair Value Gap detection (simplified)
            if i >= 3:
                c1, c2, c3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
                is_fvg = c3['low'] > c1['high']
                features['fair_value_gap'] = 1 if is_fvg else 0
            else:
                features['fair_value_gap'] = 0
            
            # Volume anomaly
            avg_volume = df.iloc[i-20:i]['volume'].mean()
            current_volume = df.iloc[i]['volume']
            features['volume_spike'] = 1 if current_volume > avg_volume * 2 else 0
            
            # Calculate forward returns (target variable)
            if i + 5 < len(df):  # 5-period forward return
                current_price = df.iloc[i]['close']
                future_price = df.iloc[i + 5]['close']
                forward_return = (future_price - current_price) / current_price
                features['forward_return_5'] = forward_return
            else:
                features['forward_return_5'] = 0
                
            pattern_features.append(features)
        
        return pd.DataFrame(pattern_features)
    
    def train_asset_model(self, symbol: str, exchange: str, timeframe: str = '5m') -> TrainedAsset:
        """
        Train a pattern recognition model for a specific symbol-exchange combination
        Returns a TrainedAsset with optimized pattern weights
        """
        logger.info(f"🤖 Training ML model for {symbol} on {exchange} ({timeframe})")
        
        # Extract features for this asset
        features_df = self.extract_pattern_features(symbol, exchange, timeframe)
        
        if features_df.empty:
            logger.error(f"No features extracted for {symbol} on {exchange}")
            return None
        
        # Simple pattern weight optimization (in real implementation, use proper ML)
        pattern_weights = {}
        
        # Analyze correlation between each pattern and forward returns
        patterns = ['liquidity_sweep', 'fair_value_gap', 'volume_spike']
        
        for pattern in patterns:
            if pattern in features_df.columns:
                pattern_signals = features_df[features_df[pattern] == 1]
                if len(pattern_signals) > 0:
                    avg_return = pattern_signals['forward_return_5'].mean()
                    success_rate = (pattern_signals['forward_return_5'] > 0).mean()
                    
                    # Weight combines average return and success rate
                    weight = avg_return * success_rate * 10  # Scale factor
                    pattern_weights[pattern] = max(0, min(2.0, weight))  # Clamp between 0 and 2
                else:
                    pattern_weights[pattern] = 1.0  # Default weight
            else:
                pattern_weights[pattern] = 1.0
        
        # Calculate performance metrics
        total_signals = len(features_df[features_df[patterns].sum(axis=1) > 0])
        profitable_signals = len(features_df[
            (features_df[patterns].sum(axis=1) > 0) & 
            (features_df['forward_return_5'] > 0)
        ])
        
        performance_metrics = {
            'total_signals': total_signals,
            'profitable_signals': profitable_signals,
            'win_rate': profitable_signals / total_signals if total_signals > 0 else 0,
            'avg_return': features_df['forward_return_5'].mean(),
            'training_samples': len(features_df)
        }
        
        # Create trained asset
        trained_asset = TrainedAsset(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            pattern_weights=pattern_weights,
            model_version="v1.0",
            training_date=datetime.now(),
            performance_metrics=performance_metrics
        )
        
        # Store in memory and save to disk
        key = (symbol, exchange, timeframe)
        self.trained_assets[key] = trained_asset
        self._save_trained_asset(trained_asset)
        
        logger.info(f"✅ Trained asset created: {symbol}/{exchange} - Win rate: {performance_metrics['win_rate']:.2%}")
        return trained_asset
    
    def train_all_assets(self, timeframes: List[str] = ['5m', '1h']) -> Dict[str, TrainedAsset]:
        """Train ML models for all available symbol-exchange combinations"""
        logger.info("🚀 Starting training for all assets...")
        
        available_assets = self.get_available_assets()
        trained_assets = {}
        
        for symbol, exchange in available_assets:
            for timeframe in timeframes:
                try:
                    asset_key = f"{symbol}_{exchange}_{timeframe}"
                    trained_asset = self.train_asset_model(symbol, exchange, timeframe)
                    if trained_asset:
                        trained_assets[asset_key] = trained_asset
                except Exception as e:
                    logger.error(f"Error training {symbol} on {exchange}: {e}")
        
        logger.info(f"🎯 Training complete! Created {len(trained_assets)} trained assets")
        return trained_assets
    
    def get_pattern_confidence(self, symbol: str, exchange: str, pattern_name: str, 
                              base_confidence: float, timeframe: str = '5m') -> float:
        """
        Get ML-enhanced confidence for a pattern on a specific asset
        Returns base_confidence * trained_weight for this symbol-exchange combination
        """
        key = (symbol, exchange, timeframe)
        
        if key not in self.trained_assets:
            # Load from disk if not in memory
            self._load_trained_asset(symbol, exchange, timeframe)
        
        if key in self.trained_assets:
            trained_asset = self.trained_assets[key]
            weight = trained_asset.pattern_weights.get(pattern_name, 1.0)
            enhanced_confidence = base_confidence * weight
            
            logger.debug(f"Enhanced confidence for {pattern_name} on {symbol}/{exchange}: "
                        f"{base_confidence:.2f} -> {enhanced_confidence:.2f} (weight: {weight:.2f})")
            
            return min(1.0, enhanced_confidence)  # Cap at 100%
        
        # Return base confidence if no trained model available
        return base_confidence
    
    def _save_trained_asset(self, trained_asset: TrainedAsset):
        """Save trained asset to disk"""
        filename = f"{trained_asset.symbol}_{trained_asset.exchange}_{trained_asset.timeframe}_model.pkl"
        filepath = os.path.join(self.models_dir, filename)
        
        with open(filepath, 'wb') as f:
            pickle.dump(trained_asset, f)
    
    def _load_trained_asset(self, symbol: str, exchange: str, timeframe: str) -> bool:
        """Load trained asset from disk"""
        filename = f"{symbol}_{exchange}_{timeframe}_model.pkl"
        filepath = os.path.join(self.models_dir, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                trained_asset = pickle.load(f)
                key = (symbol, exchange, timeframe)
                self.trained_assets[key] = trained_asset
                return True
        return False
    
    def get_asset_summary(self) -> Dict[str, Any]:
        """Get summary of all trained assets"""
        return {
            'total_trained_assets': len(self.trained_assets),
            'assets': [
                {
                    'symbol': asset.symbol,
                    'exchange': asset.exchange,
                    'timeframe': asset.timeframe,
                    'win_rate': asset.performance_metrics.get('win_rate', 0),
                    'training_date': asset.training_date.isoformat()
                }
                for asset in self.trained_assets.values()
            ]
        }

if __name__ == "__main__":
    # Example usage
    engine = PatternMLEngine()
    
    # Train models for all available assets
    trained_assets = engine.train_all_assets()
    
    # Print summary
    summary = engine.get_asset_summary()
    print(json.dumps(summary, indent=2))