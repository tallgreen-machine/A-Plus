#!/usr/bin/env python3
"""
ML Pattern Recognition Module
Provides ML-enhanced pattern detection and signal confidence scoring for trading strategies
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import pickle
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

from shared.db import get_db_conn
from policy.pattern_library import Tier1Patterns
from utils.logger import log as logger


class MLPatternRecognizer:
    """
    ML-powered pattern recognition system that enhances traditional trading signals
    with machine learning confidence scores and multi-timeframe analysis
    """
    
    def __init__(self):
        self.db_conn = get_db_conn()
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.model_dir = '/workspaces/Trad/ml/models'
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Load or train models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize or load existing ML models"""
        model_configs = {
            'liquidity_sweep': {
                'type': 'gradient_boosting',
                'params': {'n_estimators': 100, 'learning_rate': 0.1, 'max_depth': 6}
            },
            'fair_value_gap': {
                'type': 'random_forest', 
                'params': {'n_estimators': 50, 'max_depth': 8}
            },
            'volume_confirmation': {
                'type': 'gradient_boosting',
                'params': {'n_estimators': 75, 'learning_rate': 0.15, 'max_depth': 5}
            },
            'divergence_strength': {
                'type': 'random_forest',
                'params': {'n_estimators': 60, 'max_depth': 10}
            }
        }
        
        for model_name, config in model_configs.items():
            model_path = os.path.join(self.model_dir, f'{model_name}_model.pkl')
            scaler_path = os.path.join(self.model_dir, f'{model_name}_scaler.pkl')
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                # Load existing model
                self.models[model_name] = joblib.load(model_path)
                self.scalers[model_name] = joblib.load(scaler_path)
                logger.info(f"✅ Loaded existing {model_name} model")
            else:
                # Train new model
                self._train_model(model_name, config)
    
    def _extract_features(self, df: pd.DataFrame, timeframe: str = '5m') -> pd.DataFrame:
        """Extract comprehensive features for ML training and prediction"""
        if len(df) < 50:
            return pd.DataFrame()
        
        features = pd.DataFrame(index=df.index[20:])  # Skip first 20 rows for indicators
        
        # Price action features
        features['price_change_pct'] = df['close'].pct_change().iloc[20:]
        features['volume_change_pct'] = df['volume'].pct_change().iloc[20:]
        features['high_low_ratio'] = (df['high'] / df['low']).iloc[20:]
        features['close_position'] = ((df['close'] - df['low']) / (df['high'] - df['low'])).iloc[20:]
        
        # Volatility features
        features['atr_14'] = self._calculate_atr(df, period=14).iloc[20:]
        features['volatility_5'] = df['close'].rolling(5).std().iloc[20:]
        features['volatility_20'] = df['close'].rolling(20).std().iloc[20:]
        
        # Volume features
        features['volume_sma_20'] = df['volume'].rolling(20).mean().iloc[20:]
        features['volume_ratio'] = (df['volume'] / features['volume_sma_20']).iloc[20:]
        features['volume_trend'] = df['volume'].rolling(5).mean().pct_change().iloc[20:]
        
        # Momentum features
        features['rsi_14'] = self._calculate_rsi(df, period=14).iloc[20:]
        features['macd'] = self._calculate_macd(df).iloc[20:]
        features['macd_signal'] = self._calculate_macd_signal(df).iloc[20:]
        features['macd_histogram'] = (features['macd'] - features['macd_signal'])
        
        # Moving average features
        features['sma_20'] = df['close'].rolling(20).mean().iloc[20:]
        features['sma_50'] = df['close'].rolling(50).mean().iloc[20:]
        features['price_vs_sma20'] = (df['close'] / features['sma_20'] - 1).iloc[20:]
        features['price_vs_sma50'] = (df['close'] / features['sma_50'] - 1).iloc[20:]
        
        # Pattern-specific features
        features['consecutive_green'] = self._count_consecutive_candles(df, 'green').iloc[20:]
        features['consecutive_red'] = self._count_consecutive_candles(df, 'red').iloc[20:]
        features['body_size_ratio'] = (abs(df['close'] - df['open']) / (df['high'] - df['low'])).iloc[20:]
        features['upper_shadow_ratio'] = ((df['high'] - df[['open', 'close']].max(axis=1)) / (df['high'] - df['low'])).iloc[20:]
        features['lower_shadow_ratio'] = ((df[['open', 'close']].min(axis=1) - df['low']) / (df['high'] - df['low'])).iloc[20:]
        
        # Time-based features (if needed for different timeframes)
        if 'timestamp' in df.columns:
            df['hour'] = pd.to_datetime(df['timestamp'], unit='ms').dt.hour
            features['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24).iloc[20:]
            features['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24).iloc[20:]
        
        # Drop any NaN values
        features = features.dropna()
        
        # Store feature columns for consistency
        if not self.feature_columns:
            self.feature_columns = features.columns.tolist()
        
        return features
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close_prev = abs(df['high'] - df['close'].shift(1))
        low_close_prev = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        return true_range.rolling(period).mean()
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26) -> pd.Series:
        """Calculate MACD line"""
        ema_fast = df['close'].ewm(span=fast).mean()
        ema_slow = df['close'].ewm(span=slow).mean()
        return ema_fast - ema_slow
    
    def _calculate_macd_signal(self, df: pd.DataFrame, signal_period: int = 9) -> pd.Series:
        """Calculate MACD signal line"""
        macd = self._calculate_macd(df)
        return macd.ewm(span=signal_period).mean()
    
    def _count_consecutive_candles(self, df: pd.DataFrame, candle_type: str) -> pd.Series:
        """Count consecutive green or red candles"""
        if candle_type == 'green':
            condition = df['close'] > df['open']
        else:
            condition = df['close'] < df['open']
        
        groups = (condition != condition.shift(1)).cumsum()
        consecutive = condition.groupby(groups).cumsum()
        return consecutive.where(condition, 0)
    
    def _prepare_training_data(self, pattern_type: str) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data for specific pattern type"""
        logger.info(f"🔄 Preparing training data for {pattern_type}")
        
        # Get historical data from enhanced database
        query = """
            SELECT symbol, timeframe, timestamp, open, high, low, close, volume
            FROM market_data_enhanced
            WHERE timeframe IN ('5m', '1h', '4h')
            ORDER BY timestamp
        """
        
        with self.db_conn.cursor() as cur:
            cur.execute(query)
            data = cur.fetchall()
        
        if not data:
            logger.error("No training data available")
            return pd.DataFrame(), pd.Series()
        
        df = pd.DataFrame(data, columns=['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert numeric columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        all_features = []
        all_labels = []
        
        # Process each symbol/timeframe combination
        for (symbol, timeframe), group in df.groupby(['symbol', 'timeframe']):
            if len(group) < 100:  # Need sufficient data
                continue
                
            group = group.sort_values('timestamp').reset_index(drop=True)
            
            # Extract features
            features = self._extract_features(group, timeframe)
            if features.empty:
                continue
            
            # Generate labels based on pattern type
            labels = self._generate_labels(group, pattern_type)
            
            if len(labels) == len(features):
                all_features.append(features)
                all_labels.extend(labels)
        
        if not all_features:
            logger.error(f"No valid feature data generated for {pattern_type}")
            return pd.DataFrame(), pd.Series()
        
        combined_features = pd.concat(all_features, ignore_index=True)
        combined_labels = pd.Series(all_labels)
        
        logger.info(f"✅ Training data prepared: {len(combined_features)} samples, {len(combined_features.columns)} features")
        return combined_features, combined_labels
    
    def _generate_labels(self, df: pd.DataFrame, pattern_type: str) -> List[int]:
        """Generate labels for training based on pattern type and future price movement"""
        labels = []
        
        # Use Tier1Patterns to identify pattern occurrences
        pattern_detector = Tier1Patterns()
        
        for i in range(20, len(df) - 10):  # Leave buffer for future price analysis
            current_price = df.iloc[i]['close']
            
            # Look ahead 5-10 candles to determine if trade would be profitable
            future_prices = df.iloc[i+1:i+11]['close']
            max_future_price = future_prices.max()
            min_future_price = future_prices.min()
            
            # Determine if this would be a good entry point
            if pattern_type in ['liquidity_sweep', 'fair_value_gap']:
                # For bullish patterns, check if price goes up by at least 2%
                profit_threshold = current_price * 1.02
                loss_threshold = current_price * 0.98
                
                if max_future_price >= profit_threshold:
                    labels.append(1)  # Good signal
                elif min_future_price <= loss_threshold:
                    labels.append(0)  # Bad signal
                else:
                    labels.append(0)  # Neutral/uncertain
            else:
                # For other patterns, use a more conservative approach
                profit_threshold = current_price * 1.015
                loss_threshold = current_price * 0.985
                
                if max_future_price >= profit_threshold:
                    labels.append(1)
                elif min_future_price <= loss_threshold:
                    labels.append(0)
                else:
                    labels.append(0)
        
        # Pad labels to match feature length
        while len(labels) < len(df) - 20:
            labels.append(0)
        
        return labels
    
    def _train_model(self, model_name: str, config: Dict[str, Any]):
        """Train a specific ML model"""
        logger.info(f"🚀 Training {model_name} model")
        
        # Prepare training data
        X, y = self._prepare_training_data(model_name)
        
        if X.empty or len(y) == 0:
            logger.error(f"Insufficient training data for {model_name}")
            return
        
        # Ensure features match expected columns
        if self.feature_columns and not X.columns.equals(pd.Index(self.feature_columns)):
            # Reorder columns to match
            X = X.reindex(columns=self.feature_columns, fill_value=0)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        if config['type'] == 'random_forest':
            model = RandomForestClassifier(**config['params'], random_state=42)
        elif config['type'] == 'gradient_boosting':
            model = GradientBoostingClassifier(**config['params'], random_state=42)
        else:
            raise ValueError(f"Unsupported model type: {config['type']}")
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"✅ {model_name} model trained with accuracy: {accuracy:.3f}")
        
        # Save model and scaler
        self.models[model_name] = model
        self.scalers[model_name] = scaler
        
        joblib.dump(model, os.path.join(self.model_dir, f'{model_name}_model.pkl'))
        joblib.dump(scaler, os.path.join(self.model_dir, f'{model_name}_scaler.pkl'))
        
        logger.info(f"💾 Saved {model_name} model and scaler")
    
    def get_pattern_confidence(self, pattern_type: str, df: pd.DataFrame, timeframe: str = '5m') -> float:
        """Get ML confidence score for a detected pattern"""
        if pattern_type not in self.models:
            logger.warning(f"No ML model available for {pattern_type}")
            return 0.5  # Default neutral confidence
        
        # Extract features for the latest data point
        features = self._extract_features(df, timeframe)
        if features.empty:
            return 0.5
        
        # Get the latest feature vector
        latest_features = features.iloc[-1:].values
        
        # Scale features
        scaler = self.scalers[pattern_type]
        latest_features_scaled = scaler.transform(latest_features)
        
        # Get prediction probability
        model = self.models[pattern_type]
        probabilities = model.predict_proba(latest_features_scaled)
        
        # Return confidence for positive class
        if len(probabilities[0]) > 1:
            return probabilities[0][1]  # Probability of class 1 (positive signal)
        else:
            return 0.5
    
    def enhance_signal_confidence(self, base_confidence: float, pattern_type: str, 
                                market_data: pd.DataFrame, timeframe: str = '5m') -> float:
        """Enhance traditional signal confidence with ML insights"""
        ml_confidence = self.get_pattern_confidence(pattern_type, market_data, timeframe)
        
        # Weighted combination of base confidence and ML confidence
        # Give more weight to ML if it's confident, but don't completely override traditional analysis
        if ml_confidence > 0.7:
            enhanced_confidence = 0.3 * base_confidence + 0.7 * ml_confidence
        elif ml_confidence < 0.3:
            enhanced_confidence = 0.7 * base_confidence + 0.3 * ml_confidence
        else:
            enhanced_confidence = 0.5 * base_confidence + 0.5 * ml_confidence
        
        # Ensure confidence stays within reasonable bounds
        enhanced_confidence = max(0.1, min(0.95, enhanced_confidence))
        
        return enhanced_confidence
    
    def get_multi_timeframe_analysis(self, symbol: str, pattern_type: str) -> Dict[str, float]:
        """Analyze pattern strength across multiple timeframes"""
        timeframes = ['5m', '1h', '4h']
        confidences = {}
        
        for tf in timeframes:
            try:
                # Get data for this timeframe
                query = """
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data_enhanced
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY timestamp DESC
                    LIMIT 100
                """
                
                with self.db_conn.cursor() as cur:
                    cur.execute(query, (symbol, tf))
                    data = cur.fetchall()
                
                if not data:
                    confidences[tf] = 0.5
                    continue
                
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col])
                
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                confidence = self.get_pattern_confidence(pattern_type, df, tf)
                confidences[tf] = confidence
                
            except Exception as e:
                logger.error(f"Error analyzing {tf} timeframe: {e}")
                confidences[tf] = 0.5
        
        return confidences


# Global instance
ml_recognizer = MLPatternRecognizer()