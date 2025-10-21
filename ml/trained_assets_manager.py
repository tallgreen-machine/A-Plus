#!/usr/bin/env python3
"""
Trained Assets ML System
Creates and manages ML models per token-exchange combination for optimized pattern recognition
"""

import os
import pickle
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

from shared.db import get_db_conn
from utils.logger import log as logger


@dataclass
class TrainedAsset:
    """Represents a trained ML model for a specific token-exchange combination"""
    symbol: str
    exchange: str
    pattern_type: str
    model_version: str
    accuracy: float
    training_samples: int
    last_trained: str
    feature_importance: Dict[str, float]
    metadata: Dict[str, Any]


class TrainedAssetsManager:
    """
    Manages trained ML models per token-exchange combination
    
    Design Philosophy:
    - Each token-exchange pair gets its own trained models
    - Models are pattern-specific (liquidity_sweep, fair_value_gap, etc.)
    - Completely modular - supports any number of exchanges/tokens
    - Models auto-retrain when new data is available
    """
    
    def __init__(self, models_dir: str = "/workspaces/Trad/ml/trained_assets"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_conn = get_db_conn()
        self.trained_assets: Dict[str, TrainedAsset] = {}
        self.available_combinations: List[Tuple[str, str]] = []
        
        # Pattern types we train models for
        self.pattern_types = [
            'liquidity_sweep',
            'fair_value_gap', 
            'volume_confirmation',
            'divergence_strength',
            'breakout_momentum'
        ]
        
        # Initialize system
        self._discover_available_combinations()
        self._load_existing_assets()
        
        logger.info(f"🎯 Trained Assets Manager initialized")
        logger.info(f"   📁 Models directory: {self.models_dir}")
        logger.info(f"   🔗 Available combinations: {len(self.available_combinations)}")
        logger.info(f"   🧠 Loaded assets: {len(self.trained_assets)}")
    
    def _discover_available_combinations(self):
        """Dynamically discover all token-exchange combinations from database"""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT exchange, symbol, COUNT(*) as records
                FROM market_data_enhanced 
                GROUP BY exchange, symbol
                HAVING COUNT(*) >= 1000  -- Minimum data requirement
                ORDER BY exchange, symbol
            """)
            
            results = cur.fetchall()
            self.available_combinations = [(row[1], row[0]) for row in results]  # (symbol, exchange)
            
            logger.info(f"🔍 Discovered {len(self.available_combinations)} viable token-exchange combinations")
            
            # Log summary by exchange
            exchange_counts = {}
            for symbol, exchange in self.available_combinations:
                exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
            
            for exchange, count in sorted(exchange_counts.items()):
                logger.info(f"   {exchange}: {count} symbols")
    
    def _load_existing_assets(self):
        """Load existing trained assets from disk"""
        assets_loaded = 0
        
        for asset_file in self.models_dir.glob("*.json"):
            try:
                with open(asset_file, 'r') as f:
                    asset_data = json.load(f)
                
                asset = TrainedAsset(**asset_data)
                asset_key = self._get_asset_key(asset.symbol, asset.exchange, asset.pattern_type)
                self.trained_assets[asset_key] = asset
                assets_loaded += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to load asset {asset_file}: {e}")
        
        logger.info(f"📥 Loaded {assets_loaded} existing trained assets")
    
    def _get_asset_key(self, symbol: str, exchange: str, pattern_type: str) -> str:
        """Generate unique key for a trained asset"""
        return f"{exchange}_{symbol}_{pattern_type}".replace("/", "_").replace("-", "_")
    
    def get_asset_path(self, symbol: str, exchange: str, pattern_type: str) -> Tuple[Path, Path]:
        """Get file paths for model and metadata"""
        base_name = self._get_asset_key(symbol, exchange, pattern_type)
        model_path = self.models_dir / f"{base_name}.pkl"
        metadata_path = self.models_dir / f"{base_name}.json"
        return model_path, metadata_path
    
    def train_asset(self, symbol: str, exchange: str, pattern_type: str, 
                   min_samples: int = 500) -> Optional[TrainedAsset]:
        """Train ML model for specific token-exchange-pattern combination"""
        logger.info(f"🚀 Training asset: {exchange}/{symbol} - {pattern_type}")
        
        try:
            # Get training data
            training_data = self._get_training_data(symbol, exchange, pattern_type)
            
            if len(training_data) < min_samples:
                logger.warning(f"❌ Insufficient data for {exchange}/{symbol} - {pattern_type}: {len(training_data)} < {min_samples}")
                return None
            
            # Prepare features and labels
            X, y = self._prepare_training_features(training_data, pattern_type)
            
            if len(X) == 0 or len(y) == 0:
                logger.warning(f"❌ No valid features generated for {exchange}/{symbol} - {pattern_type}")
                return None
            
            # Train model using scikit-learn (lightweight approach)
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, classification_report
            from sklearn.preprocessing import StandardScaler
            import joblib
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'  # Handle imbalanced data
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Feature importance
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
            feature_importance = dict(zip(feature_names, model.feature_importances_))
            
            # Create trained asset
            asset = TrainedAsset(
                symbol=symbol,
                exchange=exchange,
                pattern_type=pattern_type,
                model_version="1.0",
                accuracy=accuracy,
                training_samples=len(X),
                last_trained=datetime.now().isoformat(),
                feature_importance=feature_importance,
                metadata={
                    'training_period_days': (training_data['timestamp'].max() - training_data['timestamp'].min()) / (1000 * 60 * 60 * 24),
                    'positive_samples': int(sum(y)),
                    'negative_samples': int(len(y) - sum(y)),
                    'feature_count': X.shape[1]
                }
            )
            
            # Save model and metadata
            model_path, metadata_path = self.get_asset_path(symbol, exchange, pattern_type)
            
            # Save model with scaler
            joblib.dump({'model': model, 'scaler': scaler}, model_path)
            
            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(asdict(asset), f, indent=2)
            
            # Store in memory
            asset_key = self._get_asset_key(symbol, exchange, pattern_type)
            self.trained_assets[asset_key] = asset
            
            logger.info(f"✅ Asset trained successfully: {exchange}/{symbol} - {pattern_type}")
            logger.info(f"   🎯 Accuracy: {accuracy:.3f}")
            logger.info(f"   📊 Samples: {len(X)} ({sum(y)} positive)")
            
            return asset
            
        except Exception as e:
            logger.error(f"❌ Failed to train asset {exchange}/{symbol} - {pattern_type}: {e}")
            return None
    
    def _get_training_data(self, symbol: str, exchange: str, pattern_type: str) -> pd.DataFrame:
        """Get training data for specific combination"""
        with self.db_conn.cursor() as cur:
            # Get multi-timeframe data for better training
            cur.execute("""
                SELECT timestamp, open, high, low, close, volume, timeframe
                FROM market_data_enhanced
                WHERE symbol = %s AND exchange = %s
                AND timeframe IN ('5m', '15m', '1h', '4h')
                ORDER BY timestamp
            """, (symbol, exchange))
            
            data = cur.fetchall()
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'timeframe'])
            
            # Convert numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            return df
    
    def _prepare_training_features(self, df: pd.DataFrame, pattern_type: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and labels for training"""
        if df.empty:
            return np.array([]), np.array([])
        
        # Group by timeframe and create features
        all_features = []
        all_labels = []
        
        for timeframe, group in df.groupby('timeframe'):
            if len(group) < 50:  # Need minimum candles
                continue
            
            group = group.sort_values('timestamp').reset_index(drop=True)
            
            # Extract technical features
            features = self._extract_technical_features(group)
            
            # Generate labels based on pattern type and future price movement
            labels = self._generate_pattern_labels(group, pattern_type)
            
            # Ensure features and labels are aligned
            min_length = min(len(features), len(labels))
            if min_length > 0:
                all_features.extend(features[:min_length])
                all_labels.extend(labels[:min_length])
        
        if not all_features:
            return np.array([]), np.array([])
        
        return np.array(all_features), np.array(all_labels)
    
    def _extract_technical_features(self, df: pd.DataFrame) -> List[List[float]]:
        """Extract technical analysis features"""
        features = []
        
        # Calculate indicators
        df['rsi'] = self._calculate_rsi(df['close'])
        df['sma_20'] = df['close'].rolling(20).mean()
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['atr'] = self._calculate_atr(df)
        
        # Generate features for each candle (skip first 25 for indicators)
        for i in range(25, len(df)):
            current = df.iloc[i]
            prev_5 = df.iloc[i-5:i]
            prev_20 = df.iloc[i-20:i]
            
            feature_vector = [
                # Price action
                current['close'] / current['open'] - 1,  # Body percentage
                (current['high'] - current['low']) / current['close'],  # Range
                (current['close'] - prev_5['close'].mean()) / prev_5['close'].mean(),  # 5-period momentum
                (current['close'] - prev_20['close'].mean()) / prev_20['close'].mean(),  # 20-period momentum
                
                # Volume
                current['volume'] / current['volume_sma'] if current['volume_sma'] > 0 else 1,
                prev_5['volume'].mean() / prev_20['volume'].mean() if prev_20['volume'].mean() > 0 else 1,
                
                # Volatility
                current['atr'] / current['close'] if current['close'] > 0 else 0,
                prev_5['atr'].std() / prev_5['atr'].mean() if prev_5['atr'].mean() > 0 else 0,
                
                # Technical indicators
                current['rsi'] / 100,
                (current['close'] - current['sma_20']) / current['sma_20'] if current['sma_20'] > 0 else 0,
                
                # Pattern-specific features
                len(prev_5[prev_5['close'] > prev_5['open']]) / 5,  # Green candle ratio
                (prev_5['high'].max() - prev_5['low'].min()) / prev_5['close'].mean(),  # Recent range
            ]
            
            # Only add if all features are valid numbers
            if all(np.isfinite(f) for f in feature_vector):
                features.append(feature_vector)
        
        return features
    
    def _generate_pattern_labels(self, df: pd.DataFrame, pattern_type: str) -> List[int]:
        """Generate training labels based on future price movement"""
        labels = []
        
        # Generate labels for the same range as features (25 to len-10)
        for i in range(25, len(df) - 10):  # Same range as feature extraction
            current_price = df.iloc[i]['close']
            
            # Look ahead 5-10 candles for price movement
            future_end = min(i + 11, len(df))
            future_prices = df.iloc[i+1:future_end]['close']
            
            if len(future_prices) == 0:
                labels.append(0)
                continue
            
            max_future = future_prices.max()
            min_future = future_prices.min()
            
            # Pattern-specific labeling logic
            if pattern_type in ['liquidity_sweep', 'volume_confirmation', 'breakout_momentum']:
                # For bullish patterns
                profit_threshold = current_price * 1.02  # 2% profit
                loss_threshold = current_price * 0.98   # 2% loss
                
                if max_future >= profit_threshold:
                    labels.append(1)  # Good signal
                elif min_future <= loss_threshold:
                    labels.append(0)  # Bad signal
                else:
                    labels.append(0)  # Neutral treated as bad
            
            elif pattern_type == 'fair_value_gap':
                # More conservative for FVG
                profit_threshold = current_price * 1.015  # 1.5% profit
                if max_future >= profit_threshold:
                    labels.append(1)
                else:
                    labels.append(0)
            
            else:  # divergence_strength
                # Very conservative for divergence
                profit_threshold = current_price * 1.025  # 2.5% profit
                if max_future >= profit_threshold:
                    labels.append(1)
                else:
                    labels.append(0)
        
        return labels
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR"""
        high_low = df['high'] - df['low']
        high_close_prev = abs(df['high'] - df['close'].shift(1))
        low_close_prev = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        return true_range.rolling(period).mean()
    
    def predict_pattern_confidence(self, symbol: str, exchange: str, pattern_type: str, 
                                 current_data: pd.DataFrame) -> float:
        """Get ML confidence for pattern detection"""
        asset_key = self._get_asset_key(symbol, exchange, pattern_type)
        
        if asset_key not in self.trained_assets:
            logger.warning(f"⚠️ No trained asset for {exchange}/{symbol} - {pattern_type}")
            return 0.5  # Neutral confidence
        
        try:
            # Load model
            model_path, _ = self.get_asset_path(symbol, exchange, pattern_type)
            
            if not model_path.exists():
                logger.warning(f"⚠️ Model file not found for {asset_key}")
                return 0.5
            
            import joblib
            model_data = joblib.load(model_path)
            model = model_data['model']
            scaler = model_data['scaler']
            
            # Extract features for current data
            features = self._extract_technical_features(current_data)
            
            if not features:
                return 0.5
            
            # Get latest feature vector
            latest_features = np.array(features[-1:])
            
            # Scale and predict
            latest_features_scaled = scaler.transform(latest_features)
            probabilities = model.predict_proba(latest_features_scaled)
            
            # Return confidence for positive class
            if len(probabilities[0]) > 1:
                confidence = probabilities[0][1]  # Probability of class 1
            else:
                confidence = 0.5
            
            return float(confidence)
            
        except Exception as e:
            logger.error(f"❌ Error predicting with asset {asset_key}: {e}")
            return 0.5
    
    def train_all_assets(self, force_retrain: bool = False):
        """Train ML models for all available token-exchange combinations"""
        logger.info(f"🚀 Starting bulk asset training...")
        logger.info(f"   📊 Combinations: {len(self.available_combinations)}")
        logger.info(f"   🎯 Patterns: {len(self.pattern_types)}")
        logger.info(f"   🔄 Total models to train: {len(self.available_combinations) * len(self.pattern_types)}")
        
        trained_count = 0
        failed_count = 0
        
        for symbol, exchange in self.available_combinations:
            for pattern_type in self.pattern_types:
                asset_key = self._get_asset_key(symbol, exchange, pattern_type)
                
                # Skip if already trained and not forcing retrain
                if not force_retrain and asset_key in self.trained_assets:
                    logger.info(f"⏭️ Skipping {exchange}/{symbol} - {pattern_type} (already trained)")
                    continue
                
                asset = self.train_asset(symbol, exchange, pattern_type)
                
                if asset:
                    trained_count += 1
                else:
                    failed_count += 1
        
        logger.info(f"✅ Bulk training completed:")
        logger.info(f"   🎯 Successfully trained: {trained_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        logger.info(f"   📊 Total assets: {len(self.trained_assets)}")
    
    def get_asset_summary(self) -> Dict[str, Any]:
        """Get summary of all trained assets"""
        summary = {
            'total_assets': len(self.trained_assets),
            'exchanges': set(),
            'symbols': set(),
            'pattern_types': set(),
            'avg_accuracy': 0.0,
            'assets_by_exchange': {},
            'assets_by_pattern': {}
        }
        
        if not self.trained_assets:
            return summary
        
        accuracies = []
        
        for asset in self.trained_assets.values():
            summary['exchanges'].add(asset.exchange)
            summary['symbols'].add(asset.symbol)
            summary['pattern_types'].add(asset.pattern_type)
            accuracies.append(asset.accuracy)
            
            # Count by exchange
            if asset.exchange not in summary['assets_by_exchange']:
                summary['assets_by_exchange'][asset.exchange] = 0
            summary['assets_by_exchange'][asset.exchange] += 1
            
            # Count by pattern
            if asset.pattern_type not in summary['assets_by_pattern']:
                summary['assets_by_pattern'][asset.pattern_type] = 0
            summary['assets_by_pattern'][asset.pattern_type] += 1
        
        summary['avg_accuracy'] = sum(accuracies) / len(accuracies)
        summary['exchanges'] = sorted(list(summary['exchanges']))
        summary['symbols'] = sorted(list(summary['symbols']))
        summary['pattern_types'] = sorted(list(summary['pattern_types']))
        
        return summary


# Global instance
trained_assets_manager = TrainedAssetsManager()