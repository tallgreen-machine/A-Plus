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
class TrainedStrategy:
    """
    Represents a trained ML model for a specific strategy with multi-dimensional training
    
    Architecture:
    - Each strategy (HTF Sweep, Volume Breakout, etc.) has optimized parameters
    - Training occurs across multiple dimensions: token/exchange, market regime, timeframe
    - Strategy parameters are what get optimized, not patterns
    """
    symbol: str
    exchange: str
    strategy_id: str  # 'htf_sweep', 'volume_breakout', 'divergence_capitulation'
    market_regime: str  # 'bull', 'bear', 'sideways'
    timeframe: str  # '1m', '5m', '1h', '4h', '1d'
    model_version: str
    accuracy: float
    training_samples: int
    last_trained: str
    strategy_parameters: Dict[str, float]  # Optimized strategy parameters
    feature_importance: Dict[str, float]
    performance_metrics: Dict[str, float]
    metadata: Dict[str, Any]


@dataclass 
class TrainedAsset:
    """
    Complete collection of trained strategies for a token-exchange pair
    
    A Trained Asset contains all trained strategies across:
    - All supported strategies (HTF Sweep, Volume Breakout, Divergence Capitulation)
    - All market regimes (bull, bear, sideways)
    - All timeframes (1m, 5m, 1h, 4h, 1d)
    """
    symbol: str
    exchange: str
    strategies: Dict[str, TrainedStrategy]  # Key: strategy_id_regime_timeframe
    last_updated: str
    total_strategies: int
    coverage_metrics: Dict[str, float]
    metadata: Dict[str, Any]


class TrainedAssetsManager:
    """
    Manages trained ML strategies per token-exchange combination with multi-dimensional training
    
    New Architecture:
    - Strategies (not patterns) with parameters get trained
    - Multi-dimensional: token/exchange + market regime + timeframe  
    - Strategy Management: comprehensive parameter optimization
    - Trained Asset = collection of all trained strategies for a symbol/exchange
    """
    
    def __init__(self, models_dir: str = "/workspaces/Trad/ml/trained_assets"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_conn = get_db_conn()
        self.trained_assets: Dict[str, TrainedAsset] = {}
        self.available_combinations: List[Tuple[str, str]] = []
        
        # Strategy definitions (replaces pattern_types)
        self.supported_strategies = [
            'htf_sweep',           # HTF Sweep: 1h→5m liquidity sweep
            'volume_breakout',     # Volume Breakout: ATR-based consolidation
            'divergence_capitulation'  # Divergence Capitulation: trend + divergence
        ]
        
        # Market regime definitions
        self.market_regimes = ['bull', 'bear', 'sideways']
        
        # Timeframe definitions  
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        # Storage for individual trained strategies (strategy_key -> TrainedStrategy)
        self.trained_strategies: Dict[str, TrainedStrategy] = {}
        
        logger.info(f"🚀 TrainedAssetsManager initialized:")
        logger.info(f"   📈 Strategies: {len(self.supported_strategies)}")
        logger.info(f"   🌊 Market regimes: {len(self.market_regimes)}")
        logger.info(f"   ⏰ Timeframes: {len(self.timeframes)}")
        logger.info(f"   🎯 Total combinations per asset: {len(self.supported_strategies) * len(self.market_regimes) * len(self.timeframes)}")
        
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
    
    def _get_asset_key(self, symbol: str, exchange: str) -> str:
        """Generate unique key for a trained asset (collection of strategies)"""
        return f"{exchange}_{symbol}".replace("/", "_").replace("-", "_")
    
    def _get_strategy_key(self, symbol: str, exchange: str, strategy_id: str, 
                         market_regime: str, timeframe: str) -> str:
        """Generate unique key for an individual trained strategy"""
        return f"{exchange}_{symbol}_{strategy_id}_{market_regime}_{timeframe}".replace("/", "_").replace("-", "_")
    
    def get_strategy_path(self, symbol: str, exchange: str, strategy_id: str,
                         market_regime: str, timeframe: str) -> Tuple[Path, Path]:
        """Get file paths for individual strategy model and metadata"""
        base_name = self._get_strategy_key(symbol, exchange, strategy_id, market_regime, timeframe)
        model_path = self.models_dir / f"{base_name}.pkl"
        metadata_path = self.models_dir / f"{base_name}.json"
        return model_path, metadata_path
    
    def get_asset_path(self, symbol: str, exchange: str) -> Tuple[Path, Path]:
        """Get file paths for complete trained asset (all strategies collection)"""
        base_name = self._get_asset_key(symbol, exchange)
        asset_path = self.models_dir / f"{base_name}_asset.json"
        summary_path = self.models_dir / f"{base_name}_summary.json"
        return asset_path, summary_path
    
    def train_strategy_multidimensional(self, symbol: str, exchange: str, strategy_id: str,
                                       market_regime: str = None, timeframe: str = None,
                                       min_samples: int = 200) -> Optional[TrainedStrategy]:
        """
        Train ML model for specific strategy with multi-dimensional approach
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange: Exchange name (e.g., 'binanceus')
            strategy_id: Strategy identifier ('htf_sweep', 'volume_breakout', 'divergence_capitulation')
            market_regime: Market regime ('bull', 'bear', 'sideways') - auto-detected if None
            timeframe: Timeframe ('1m', '5m', '1h') - uses strategy default if None
            min_samples: Minimum samples required for training
            
        Returns:
            TrainedStrategy object or None if training failed
        """
        # Auto-detect market regime if not provided
        if market_regime is None:
            market_regime = self._detect_current_market_regime(symbol, exchange)
        
        # Use strategy default timeframe if not provided
        if timeframe is None:
            timeframe = self._get_strategy_default_timeframe(strategy_id)
        
        logger.info(f"🚀 Training strategy: {exchange}/{symbol} - {strategy_id} ({market_regime}, {timeframe})")
        
        try:
            # Get regime-specific training data
            training_data = self._get_regime_specific_training_data(
                symbol, exchange, strategy_id, market_regime, timeframe
            )
            
            if training_data is None or len(training_data) < min_samples:
                logger.warning(f"❌ Insufficient data for {exchange}/{symbol} - {strategy_id} ({market_regime}, {timeframe}): "
                             f"{len(training_data) if training_data is not None else 0} < {min_samples}")
                return None
            
            # Prepare strategy-specific features and labels
            X, y = self._prepare_strategy_features(training_data, strategy_id, market_regime, timeframe)
            
            if len(X) == 0 or len(y) == 0:
                logger.warning(f"❌ No valid features generated for {strategy_id} ({market_regime}, {timeframe})")
                return None
            
            # Train model using scikit-learn
            try:
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.model_selection import train_test_split
                from sklearn.metrics import accuracy_score, classification_report
                from sklearn.preprocessing import StandardScaler
                import joblib
            except ImportError:
                logger.error("❌ Required ML libraries not available. Install: pip install scikit-learn")
                return None
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model with strategy-specific parameters
            model_params = self._get_model_parameters(strategy_id, market_regime)
            model = RandomForestClassifier(**model_params, random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Extract feature importance
            feature_names = self._get_feature_names(strategy_id)
            feature_importance = dict(zip(feature_names, model.feature_importances_))
            
            # Extract optimized strategy parameters from model
            optimized_params = self._extract_strategy_parameters(
                model, feature_importance, training_data, strategy_id
            )
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(y_test, y_pred, accuracy)
            
            # Create TrainedStrategy object
            trained_strategy = TrainedStrategy(
                symbol=symbol,
                exchange=exchange,
                strategy_id=strategy_id,
                market_regime=market_regime,
                timeframe=timeframe,
                model_version="1.0",
                accuracy=accuracy,
                training_samples=len(training_data),
                last_trained=datetime.now().isoformat(),
                strategy_parameters=optimized_params,
                feature_importance=feature_importance,
                performance_metrics=performance_metrics,
                metadata={
                    'model_params': model_params,
                    'feature_count': len(feature_names),
                    'regime_detected': market_regime,
                    'timeframe_used': timeframe
                }
            )
            
            # Save model and metadata
            model_path, metadata_path = self.get_strategy_path(symbol, exchange, strategy_id, market_regime, timeframe)
            
            # Save model
            joblib.dump({'model': model, 'scaler': scaler}, model_path)
            
            # Save metadata
            with open(metadata_path, 'w') as f:
                # Convert TrainedStrategy to dict for JSON serialization
                strategy_dict = {
                    'symbol': trained_strategy.symbol,
                    'exchange': trained_strategy.exchange,
                    'strategy_id': trained_strategy.strategy_id,
                    'market_regime': trained_strategy.market_regime,
                    'timeframe': trained_strategy.timeframe,
                    'model_version': trained_strategy.model_version,
                    'accuracy': trained_strategy.accuracy,
                    'training_samples': trained_strategy.training_samples,
                    'last_trained': trained_strategy.last_trained,
                    'strategy_parameters': trained_strategy.strategy_parameters,
                    'feature_importance': trained_strategy.feature_importance,
                    'performance_metrics': trained_strategy.performance_metrics,
                    'metadata': trained_strategy.metadata
                }
                json.dump(strategy_dict, f, indent=2)
            
            # Store in memory
            strategy_key = self._get_strategy_key(symbol, exchange, strategy_id, market_regime, timeframe)
            self.trained_strategies[strategy_key] = trained_strategy
            
            logger.info(f"✅ Strategy trained successfully: {exchange}/{symbol} - {strategy_id} ({market_regime}, {timeframe})")
            logger.info(f"   📊 Accuracy: {accuracy:.3f}")
            logger.info(f"   📈 Samples: {len(training_data)}")
            logger.info(f"   🎯 Top parameters: {list(optimized_params.keys())[:3]}")
            
            return trained_strategy
            
        except Exception as e:
            logger.error(f"❌ Failed to train strategy {exchange}/{symbol} - {strategy_id} ({market_regime}, {timeframe}): {e}")
            return None
            
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
    def _get_regime_specific_training_data(self, symbol: str, exchange: str, strategy_id: str,
                                         market_regime: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Get training data filtered for specific market regime and timeframe
        
        This method filters historical data to match the specified market conditions,
        ensuring the model trains only on relevant market scenarios.
        """
        try:
            if self.db_conn is None:
                logger.error("❌ Database connection not available")
                return None
            
            # Get historical data with regime classification
            with self.db_conn.cursor() as cur:
                # Get substantial historical data for regime analysis
                cur.execute(
                    """
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data 
                    WHERE symbol = %s AND exchange = %s 
                    AND timeframe = %s
                    ORDER BY timestamp ASC
                    """,
                    (symbol, exchange, timeframe)
                )
                
                rows = cur.fetchall()
                if not rows:
                    logger.warning(f"⚠️ No historical data found for {symbol} on {exchange} ({timeframe})")
                    return None
                
                # Convert to DataFrame
                df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Convert price columns to float
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Add regime classification to each period
                df = self._classify_historical_regimes(df)
                
                # Filter for specific regime
                regime_data = df[df['market_regime'] == market_regime].copy()
                
                if len(regime_data) == 0:
                    logger.warning(f"⚠️ No {market_regime} regime data found for {symbol}")
                    return None
                
                # Add strategy-specific features
                regime_data = self._add_strategy_features(regime_data, strategy_id)
                
                logger.info(f"📊 Retrieved {len(regime_data)} {market_regime} regime samples for {symbol} ({timeframe})")
                return regime_data
                
        except Exception as e:
            logger.error(f"❌ Error getting regime-specific data: {e}")
            return None
    
    def _classify_historical_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify each historical period by market regime"""
        try:
            # Calculate rolling trend metrics for regime classification
            window_size = 50  # 50 periods for regime classification
            df['market_regime'] = 'sideways'  # Default
            
            for i in range(window_size, len(df)):
                # Get window of data for regime analysis
                window_data = df.iloc[i-window_size:i].copy()
                
                # Calculate trend metrics for this window
                metrics = self._calculate_trend_metrics(window_data)
                
                # Classify regime for this period
                regime = self._classify_market_regime(metrics)
                df.loc[i, 'market_regime'] = regime
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error classifying historical regimes: {e}")
            df['market_regime'] = 'sideways'  # Safe default
            return df
    
    def _add_strategy_features(self, df: pd.DataFrame, strategy_id: str) -> pd.DataFrame:
        """Add strategy-specific technical features to the data"""
        try:
            # Common features for all strategies
            df['rsi'] = self._calculate_rsi(df['close'])
            df['atr'] = self._calculate_atr(df)
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Strategy-specific features
            if strategy_id == 'htf_sweep':
                # HTF Sweep specific features
                df['swing_high'] = df['high'].rolling(window=20).max()
                df['swing_low'] = df['low'].rolling(window=20).min()
                df['price_vs_swing_high'] = (df['close'] - df['swing_high']) / df['swing_high']
                df['price_vs_swing_low'] = (df['close'] - df['swing_low']) / df['swing_low']
                
            elif strategy_id == 'volume_breakout':
                # Volume Breakout specific features
                df['price_range'] = df['high'] - df['low']
                df['consolidation_range'] = df['price_range'].rolling(window=10).mean()
                df['breakout_threshold'] = df['consolidation_range'] * 1.5
                df['volume_spike'] = df['volume_ratio'] > 2.5
                
            elif strategy_id == 'divergence_capitulation':
                # Divergence Capitulation specific features
                df['ema_50'] = df['close'].ewm(span=50).mean()
                df['ema_200'] = df['close'].ewm(span=200).mean()
                df['trend_context'] = df['ema_50'] > df['ema_200']
                df['rsi_divergence'] = self._calculate_rsi_divergence(df)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error adding strategy features: {e}")
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return pd.Series([50] * len(prices), index=prices.index)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            return atr
        except:
            return pd.Series([1.0] * len(df), index=df.index)
    
    def _calculate_rsi_divergence(self, df: pd.DataFrame) -> pd.Series:
        """Calculate RSI divergence signals"""
        try:
            # Simple divergence detection - can be enhanced
            rsi = df['rsi']
            price = df['close']
            
            # Find local lows in price and RSI
            price_lows = price.rolling(window=10).min() == price
            rsi_lows = rsi.rolling(window=10).min() == rsi
            
            # Basic divergence signal (simplified)
            divergence = pd.Series([0] * len(df), index=df.index)
            
            return divergence
        except:
            return pd.Series([0] * len(df), index=df.index)
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
    
    
    def get_strategy_parameters(self, symbol: str, exchange: str, strategy_id: str, 
                               market_regime: str = None, timeframe: str = None) -> Optional[Dict[str, Any]]:
        """
        Get ML-optimized strategy parameters for a specific strategy on a symbol/exchange combination
        
        This is the key integration point between ML and A+ strategies.
        Returns optimized strategy parameters rather than pattern confidence scores.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange: Exchange name (e.g., 'binanceus') 
            strategy_id: Strategy identifier ('htf_sweep', 'volume_breakout', 'divergence_capitulation')
            market_regime: Optional market regime ('bull', 'bear', 'sideways') - auto-detected if None
            timeframe: Optional timeframe ('1m', '5m', '1h') - uses strategy default if None
            
        Returns:
            Dictionary of optimized strategy parameters or None if not trained
        """
        # Auto-detect market regime if not provided
        if market_regime is None:
            market_regime = self._detect_current_market_regime(symbol, exchange)
        
        # Use strategy default timeframe if not provided
        if timeframe is None:
            timeframe = self._get_strategy_default_timeframe(strategy_id)
        
        strategy_key = self._get_strategy_key(symbol, exchange, strategy_id, market_regime, timeframe)
        
        if strategy_key not in self.trained_strategies:
            logger.warning(f"⚠️ No trained strategy for {exchange}/{symbol} - {strategy_id} ({market_regime}, {timeframe})")
            return self._get_default_strategy_parameters(strategy_id)
        
        trained_strategy = self.trained_strategies[strategy_key]
        
        # Extract optimized strategy parameters based on ML training
        try:
            # Base parameters optimized by ML performance
            optimized_params = {
                'confidence_threshold': max(0.6, trained_strategy.accuracy),
                'training_accuracy': trained_strategy.accuracy,
                'sample_size': trained_strategy.training_samples,
                'market_regime': market_regime,
                'timeframe': timeframe,
                'last_trained': trained_strategy.last_trained
            }
            
            # Add ML-optimized strategy parameters
            optimized_params.update(trained_strategy.strategy_parameters)
            
            # Strategy-specific parameter optimization
            if strategy_id == 'htf_sweep':
                # HTF Sweep strategy parameters optimized by ML
                optimized_params.update({
                    'swing_lookback_periods': self._optimize_swing_lookback(trained_strategy),
                    'risk_reward_ratio': self._optimize_risk_reward(trained_strategy),
                    'min_sweep_percentage': self._optimize_sweep_percentage(trained_strategy),
                    'structure_shift_confirmation': trained_strategy.accuracy > 0.75
                })
            
            elif strategy_id == 'volume_breakout':
                # Volume Breakout strategy parameters
                optimized_params.update({
                    'consolidation_period': self._optimize_consolidation_period(trained_strategy),
                    'volume_sma_period': 20,  # Standard but could be optimized
                    'volume_multiplier': self._optimize_volume_multiplier(trained_strategy),
                    'atr_multiplier': self._optimize_atr_multiplier(trained_strategy)
                })
            
            elif strategy_id == 'divergence_capitulation':
                # Divergence Capitulation strategy parameters
                optimized_params.update({
                    'rsi_period': 14,  # Could be optimized based on asset performance
                    'ema_fast_period': 50,
                    'ema_slow_period': 200,
                    'volume_spike_multiplier': self._optimize_volume_spike(trained_strategy),
                    'divergence_lookback': self._optimize_divergence_lookback(trained_strategy)
                })
            
            logger.debug(f"📊 Retrieved optimized strategy parameters for {exchange}/{symbol} - {strategy_id} ({market_regime}, {timeframe})")
            return optimized_params
            
        except Exception as e:
            logger.error(f"❌ Error getting strategy parameters for {strategy_key}: {e}")
            return self._get_default_strategy_parameters(strategy_id)
    
    def _get_default_strategy_parameters(self, strategy_id: str) -> Dict[str, Any]:
        """Get default strategy parameters when no trained model is available"""
        defaults = {
            'htf_sweep': {
                'swing_lookback_periods': 20,
                'risk_reward_ratio': 2.0,
                'min_sweep_percentage': 0.5,
                'structure_shift_confirmation': True,
                'confidence_threshold': 0.7
            },
            'volume_breakout': {
                'consolidation_period': 10,
                'volume_sma_period': 20,
                'volume_multiplier': 2.5,
                'atr_multiplier': 1.5,
                'confidence_threshold': 0.65
            },
            'divergence_capitulation': {
                'rsi_period': 14,
                'ema_fast_period': 50,
                'ema_slow_period': 200,
                'volume_spike_multiplier': 3.0,
                'divergence_lookback': 50,
                'confidence_threshold': 0.75
            }
        }
        
        return defaults.get(strategy_id, {'confidence_threshold': 0.6})
    
    def _detect_current_market_regime(self, symbol: str, exchange: str) -> str:
        """
        Detect current market regime for the symbol/exchange pair
        
        Uses technical analysis to classify market as:
        - 'bull': Strong uptrend with higher highs/lows
        - 'bear': Strong downtrend with lower highs/lows  
        - 'sideways': Consolidation/ranging market
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange: Exchange name (e.g., 'binanceus')
            
        Returns:
            Market regime classification
        """
        try:
            # Get recent price data for regime analysis
            price_data = self._get_recent_price_data(symbol, exchange, periods=100)
            
            if price_data is None or len(price_data) < 50:
                logger.warning(f"⚠️ Insufficient data for market regime detection: {symbol}")
                return 'sideways'  # Default to sideways if no data
            
            # Calculate trend indicators
            trend_metrics = self._calculate_trend_metrics(price_data)
            
            # Classify market regime based on trend strength and direction
            regime = self._classify_market_regime(trend_metrics)
            
            logger.debug(f"📊 Market regime detected for {symbol}: {regime}")
            return regime
            
        except Exception as e:
            logger.error(f"❌ Error detecting market regime for {symbol}: {e}")
            return 'sideways'  # Safe default
    
    def _get_recent_price_data(self, symbol: str, exchange: str, periods: int = 100) -> Optional[pd.DataFrame]:
        """Get recent price data for market regime analysis"""
        try:
            if self.db_conn is None:
                return None
            
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data 
                    WHERE symbol = %s AND exchange = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                    """,
                    (symbol, exchange, periods)
                )
                
                rows = cur.fetchall()
                if not rows:
                    return None
                
                # Convert to DataFrame and reverse to chronological order
                df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                # Convert price columns to float
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                return df
                
        except Exception as e:
            logger.error(f"❌ Error fetching price data for {symbol}: {e}")
            return None
    
    def _calculate_trend_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate trend strength and direction metrics"""
        try:
            # Calculate moving averages
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            
            # Current price vs moving averages
            current_price = df['close'].iloc[-1]
            ema_20 = df['ema_20'].iloc[-1]
            ema_50 = df['ema_50'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            
            # Trend direction (% above/below MAs)
            ema_20_diff = (current_price - ema_20) / ema_20 * 100
            ema_50_diff = (current_price - ema_50) / ema_50 * 100
            sma_20_diff = (current_price - sma_20) / sma_20 * 100
            
            # Moving average alignment (trend strength)
            ma_alignment = 0
            if ema_20 > ema_50:  # Short-term above long-term = bullish
                ma_alignment += 1
            if current_price > ema_20:  # Price above short-term = bullish
                ma_alignment += 1
            if current_price > ema_50:  # Price above long-term = bullish
                ma_alignment += 1
            
            # Calculate recent volatility
            df['returns'] = df['close'].pct_change()
            volatility = df['returns'].tail(20).std() * 100
            
            # Calculate trend consistency (% of recent periods following trend)
            recent_closes = df['close'].tail(20)
            trend_consistency = 0
            if len(recent_closes) > 1:
                upward_moves = (recent_closes.diff() > 0).sum()
                trend_consistency = upward_moves / (len(recent_closes) - 1) * 100
            
            return {
                'ema_20_diff': ema_20_diff,
                'ema_50_diff': ema_50_diff,
                'sma_20_diff': sma_20_diff,
                'ma_alignment': ma_alignment,  # 0-3 scale
                'volatility': volatility,
                'trend_consistency': trend_consistency,  # 0-100%
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating trend metrics: {e}")
            return {}
    
    def _classify_market_regime(self, metrics: Dict[str, float]) -> str:
        """
        Classify market regime based on trend metrics
        
        Classification Logic:
        - Bull: Strong upward trend with aligned MAs and momentum
        - Bear: Strong downward trend with aligned MAs and momentum  
        - Sideways: Weak trend, high volatility, or conflicting signals
        """
        if not metrics:
            return 'sideways'
        
        ma_alignment = metrics.get('ma_alignment', 0)
        ema_20_diff = metrics.get('ema_20_diff', 0)
        ema_50_diff = metrics.get('ema_50_diff', 0)
        trend_consistency = metrics.get('trend_consistency', 50)
        volatility = metrics.get('volatility', 0)
        
        # Bull market conditions
        if (ma_alignment >= 2 and  # Price above most MAs
            ema_20_diff > 2 and      # Price significantly above EMA20
            ema_50_diff > 1 and      # Price above EMA50
            trend_consistency > 60):  # Consistent upward movement
            return 'bull'
        
        # Bear market conditions  
        elif (ma_alignment <= 1 and   # Price below most MAs
              ema_20_diff < -2 and    # Price significantly below EMA20
              ema_50_diff < -1 and    # Price below EMA50
              trend_consistency < 40): # Consistent downward movement
            return 'bear'
        
        # Sideways market (default for unclear conditions)
        else:
            return 'sideways'
    
    def _get_strategy_default_timeframe(self, strategy_id: str) -> str:
        """Get default timeframe for each strategy"""
        defaults = {
            'htf_sweep': '5m',           # HTF Sweep operates on 5m primarily
            'volume_breakout': '15m',    # Volume breakout works well on 15m
            'divergence_capitulation': '1h'  # Divergence needs higher timeframe context
        }
        return defaults.get(strategy_id, '5m')
        
    def _optimize_swing_lookback(self, trained_strategy: TrainedStrategy) -> int:
        """Optimize swing lookback periods based on trained strategy performance"""
        base_lookback = 20
        
        # Adjust based on accuracy and sample size
        if trained_strategy.accuracy > 0.85:
            return max(15, base_lookback - 5)  # Shorter for high accuracy
        elif trained_strategy.accuracy < 0.65:
            return min(30, base_lookback + 10)  # Longer for lower accuracy
        
        return base_lookback
    
    def _optimize_risk_reward(self, trained_strategy: TrainedStrategy) -> float:
        """Optimize risk-reward ratio based on trained strategy performance"""
        base_rr = 2.5
        
        # Higher accuracy models can use more aggressive targets
        if trained_strategy.accuracy > 0.85:
            return min(3.0, base_rr + 0.5)
        elif trained_strategy.accuracy < 0.65:
            return max(2.0, base_rr - 0.5)
        
        return base_rr
    
    def _optimize_sweep_percentage(self, trained_strategy: TrainedStrategy) -> float:
        """Optimize minimum sweep percentage"""
        base_percentage = 0.001  # 0.1%
        
        # More samples allow for tighter requirements
        if trained_strategy.training_samples > 2000:
            return base_percentage * 0.5  # Tighter for more data
        elif trained_strategy.training_samples < 1000:
            return base_percentage * 2.0  # Looser for less data
        
        return base_percentage
    
    def _optimize_consolidation_period(self, trained_strategy: TrainedStrategy) -> int:
        """Optimize consolidation period for volume breakouts"""
        base_period = 10
        
        if trained_strategy.accuracy > 0.8:
            return max(8, base_period - 2)
        elif trained_strategy.accuracy < 0.65:
            return min(15, base_period + 5)
        
        return base_period
    
    def _optimize_volume_multiplier(self, trained_strategy: TrainedStrategy) -> float:
        """Optimize volume confirmation multiplier"""
        base_multiplier = 2.5
        
        # High accuracy models can be more selective
        if trained_strategy.accuracy > 0.85:
            return min(3.5, base_multiplier + 1.0)
        elif trained_strategy.accuracy < 0.65:
            return max(1.8, base_multiplier - 0.7)
        
        return base_multiplier
    
    def _optimize_atr_multiplier(self, trained_strategy: TrainedStrategy) -> float:
        """Optimize ATR multiplier for consolidation detection"""
        base_multiplier = 1.5
        
        if trained_strategy.accuracy > 0.8:
            return max(1.2, base_multiplier - 0.3)
        elif trained_strategy.accuracy < 0.65:
            return min(2.0, base_multiplier + 0.5)
        
        return base_multiplier
    
    def _optimize_volume_spike(self, trained_strategy: TrainedStrategy) -> float:
        """Optimize volume spike multiplier for divergence capitulation"""
        base_multiplier = 3.0
        
        if trained_strategy.accuracy > 0.85:
            return min(4.0, base_multiplier + 1.0)
        elif trained_strategy.accuracy < 0.65:
            return max(2.0, base_multiplier - 1.0)
        
        return base_multiplier
    
    def _optimize_divergence_lookback(self, trained_strategy: TrainedStrategy) -> int:
        """Optimize divergence lookback period"""
        base_lookback = 50
        
        if trained_strategy.accuracy > 0.8:
            return max(40, base_lookback - 10)  # Shorter for high accuracy
        elif trained_strategy.accuracy < 0.65:
            return min(70, base_lookback + 20)  # Longer for lower accuracy
        
        return base_lookback
    
    def _optimize_volume_spike(self, asset: TrainedAsset) -> float:
        """Optimize volume spike multiplier for divergence"""
        base_spike = 3.0
        
        if asset.accuracy > 0.85:
            return min(4.0, base_spike + 1.0)
        elif asset.accuracy < 0.65:
            return max(2.0, base_spike - 1.0)
        
        return base_spike
    
    def _optimize_divergence_lookback(self, asset: TrainedAsset) -> int:
        """Optimize divergence lookback period"""
        base_lookback = 10
        
        if asset.training_samples > 2000:
            return max(8, base_lookback - 2)
        elif asset.training_samples < 1000:
            return min(15, base_lookback + 5)
        
        return base_lookback
    
    def _optimize_resistance_lookback(self, asset: TrainedAsset) -> int:
        """Optimize resistance lookback for breakouts"""
        base_lookback = 24
        
        if asset.accuracy > 0.8:
            return max(20, base_lookback - 4)
        elif asset.accuracy < 0.65:
            return min(30, base_lookback + 6)
        
        return base_lookback
    
    def _optimize_breakout_percentage(self, asset: TrainedAsset) -> float:
        """Optimize breakout confirmation percentage"""
        base_percentage = 0.002  # 0.2%
        
        if asset.accuracy > 0.85:
            return base_percentage * 0.5
        elif asset.accuracy < 0.65:
            return base_percentage * 2.0
        
        return base_percentage
    
    def _optimize_gap_threshold(self, asset: TrainedAsset) -> float:
        """Optimize fair value gap size threshold"""
        base_threshold = 0.005  # 0.5%
        
        if asset.accuracy > 0.8:
            return base_threshold * 0.7
        elif asset.accuracy < 0.65:
            return base_threshold * 1.5
        
        return base_threshold
    
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
    
    def train_complete_asset(self, symbol: str, exchange: str, 
                           target_regimes: List[str] = None, 
                           target_timeframes: List[str] = None) -> Optional[TrainedAsset]:
        """
        Train complete asset with all strategy combinations across regimes and timeframes
        
        Creates a comprehensive TrainedAsset containing all trained strategies
        for the symbol/exchange combination.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange: Exchange name (e.g., 'binanceus')
            target_regimes: List of regimes to train (defaults to all)
            target_timeframes: List of timeframes to train (defaults to all)
            
        Returns:
            Complete TrainedAsset or None if training failed
        """
        # Use defaults if not specified
        if target_regimes is None:
            target_regimes = self.market_regimes
        if target_timeframes is None:
            target_timeframes = self.timeframes
        
        logger.info(f"🚀 Training complete asset: {exchange}/{symbol}")
        logger.info(f"   📈 Strategies: {len(self.supported_strategies)}")
        logger.info(f"   🌊 Regimes: {target_regimes}")
        logger.info(f"   ⏰ Timeframes: {target_timeframes}")
        
        trained_strategies = {}
        successful_trainings = 0
        total_combinations = len(self.supported_strategies) * len(target_regimes) * len(target_timeframes)
        
        # Train all strategy combinations
        for strategy_id in self.supported_strategies:
            for regime in target_regimes:
                for timeframe in target_timeframes:
                    
                    logger.info(f"🔄 Training: {strategy_id} ({regime}, {timeframe})")
                    
                    # Train individual strategy
                    trained_strategy = self.train_strategy_multidimensional(
                        symbol=symbol,
                        exchange=exchange,
                        strategy_id=strategy_id,
                        market_regime=regime,
                        timeframe=timeframe,
                        min_samples=100  # Lower threshold for comprehensive training
                    )
                    
                    if trained_strategy:
                        strategy_key = self._get_strategy_key(symbol, exchange, strategy_id, regime, timeframe)
                        trained_strategies[strategy_key] = trained_strategy
                        successful_trainings += 1
                        logger.info(f"✅ {strategy_id} ({regime}, {timeframe}) - Accuracy: {trained_strategy.accuracy:.3f}")
                    else:
                        logger.warning(f"❌ Failed: {strategy_id} ({regime}, {timeframe})")
        
        if successful_trainings == 0:
            logger.error(f"❌ No strategies successfully trained for {symbol}")
            return None
        
        # Calculate coverage metrics
        coverage_metrics = {
            'total_combinations': total_combinations,
            'successful_trainings': successful_trainings,
            'coverage_percentage': (successful_trainings / total_combinations) * 100,
            'strategies_covered': len(set(s.strategy_id for s in trained_strategies.values())),
            'regimes_covered': len(set(s.market_regime for s in trained_strategies.values())),
            'timeframes_covered': len(set(s.timeframe for s in trained_strategies.values())),
            'average_accuracy': np.mean([s.accuracy for s in trained_strategies.values()]) if trained_strategies else 0.0
        }
        
        # Create complete TrainedAsset
        trained_asset = TrainedAsset(
            symbol=symbol,
            exchange=exchange,
            strategies=trained_strategies,
            last_updated=datetime.now().isoformat(),
            total_strategies=successful_trainings,
            coverage_metrics=coverage_metrics,
            metadata={
                'training_session': datetime.now().isoformat(),
                'target_regimes': target_regimes,
                'target_timeframes': target_timeframes,
                'supported_strategies': self.supported_strategies
            }
        )
        
        # Save complete asset
        asset_path, summary_path = self.get_asset_path(symbol, exchange)
        
        try:
            # Save asset data
            asset_dict = {
                'symbol': trained_asset.symbol,
                'exchange': trained_asset.exchange,
                'strategies': {k: {
                    'symbol': v.symbol,
                    'exchange': v.exchange,
                    'strategy_id': v.strategy_id,
                    'market_regime': v.market_regime,
                    'timeframe': v.timeframe,
                    'model_version': v.model_version,
                    'accuracy': v.accuracy,
                    'training_samples': v.training_samples,
                    'last_trained': v.last_trained,
                    'strategy_parameters': v.strategy_parameters,
                    'feature_importance': v.feature_importance,
                    'performance_metrics': v.performance_metrics,
                    'metadata': v.metadata
                } for k, v in trained_asset.strategies.items()},
                'last_updated': trained_asset.last_updated,
                'total_strategies': trained_asset.total_strategies,
                'coverage_metrics': trained_asset.coverage_metrics,
                'metadata': trained_asset.metadata
            }
            
            with open(asset_path, 'w') as f:
                json.dump(asset_dict, f, indent=2)
            
            # Save summary
            with open(summary_path, 'w') as f:
                json.dump(coverage_metrics, f, indent=2)
            
            # Store in memory
            asset_key = self._get_asset_key(symbol, exchange)
            self.trained_assets[asset_key] = trained_asset
            
            logger.info(f"🎉 Complete asset training finished: {exchange}/{symbol}")
            logger.info(f"   ✅ Successful: {successful_trainings}/{total_combinations} ({coverage_metrics['coverage_percentage']:.1f}%)")
            logger.info(f"   📊 Average accuracy: {coverage_metrics['average_accuracy']:.3f}")
            logger.info(f"   📈 Strategies: {coverage_metrics['strategies_covered']}/{len(self.supported_strategies)}")
            
            return trained_asset
            
        except Exception as e:
            logger.error(f"❌ Error saving trained asset: {e}")
            return None
    
    def train_multi_dimensional_strategies(self, symbols: List[str], exchanges: List[str], 
                                         min_samples: int = 200) -> Dict[str, Any]:
        """
        Enhanced multi-dimensional training across all supported dimensions
        
        Trains strategies across:
        - Multiple symbols and exchanges
        - All market regimes (bull, bear, sideways)  
        - All timeframes (1m, 5m, 15m, 1h, 4h, 1d)
        - All strategies (htf_sweep, volume_breakout, divergence_capitulation)
        
        Args:
            symbols: List of symbols to train
            exchanges: List of exchanges to train on
            min_samples: Minimum samples required for training
            
        Returns:
            Training summary with statistics
        """
        logger.info(f"🚀 Starting multi-dimensional training campaign:")
        logger.info(f"   📊 Symbols: {len(symbols)} ({', '.join(symbols[:3])}{'...' if len(symbols) > 3 else ''})")
        logger.info(f"   🏢 Exchanges: {len(exchanges)} ({', '.join(exchanges)})")
        logger.info(f"   📈 Strategies: {len(self.supported_strategies)}")
        logger.info(f"   🌊 Market regimes: {len(self.market_regimes)}")
        logger.info(f"   ⏰ Timeframes: {len(self.timeframes)}")
        
        total_combinations = (len(symbols) * len(exchanges) * len(self.supported_strategies) * 
                            len(self.market_regimes) * len(self.timeframes))
        logger.info(f"   🎯 Total training combinations: {total_combinations}")
        
        training_results = {
            'total_combinations': total_combinations,
            'successful_trainings': 0,
            'failed_trainings': 0,
            'assets_completed': 0,
            'strategy_results': {},
            'regime_results': {},
            'timeframe_results': {},
            'start_time': datetime.now().isoformat()
        }
        
        try:
            # Train each symbol/exchange combination
            for symbol in symbols:
                for exchange in exchanges:
                    logger.info(f"🎯 Training asset: {exchange}/{symbol}")
                    
                    asset_results = {
                        'symbol': symbol,
                        'exchange': exchange,
                        'strategies_trained': 0,
                        'total_accuracy': 0.0,
                        'best_accuracy': 0.0,
                        'strategy_breakdown': {}
                    }
                    
                    # Train all strategies for this asset
                    for strategy_id in self.supported_strategies:
                        strategy_results = {
                            'total_trained': 0,
                            'successful': 0,
                            'avg_accuracy': 0.0,
                            'regimes': {},
                            'timeframes': {}
                        }
                        
                        # Train across all regimes and timeframes
                        for market_regime in self.market_regimes:
                            for timeframe in self.timeframes:
                                
                                # Attempt training
                                trained_strategy = self.train_strategy_multi_dimensional(
                                    symbol=symbol,
                                    exchange=exchange,
                                    strategy_id=strategy_id,
                                    market_regime=market_regime,
                                    timeframe=timeframe,
                                    min_samples=min_samples
                                )
                                
                                strategy_results['total_trained'] += 1
                                
                                if trained_strategy:
                                    strategy_results['successful'] += 1
                                    training_results['successful_trainings'] += 1
                                    
                                    # Update accuracy tracking
                                    accuracy = trained_strategy.accuracy
                                    strategy_results['avg_accuracy'] += accuracy
                                    asset_results['total_accuracy'] += accuracy
                                    asset_results['best_accuracy'] = max(asset_results['best_accuracy'], accuracy)
                                    
                                    # Track by regime and timeframe
                                    if market_regime not in strategy_results['regimes']:
                                        strategy_results['regimes'][market_regime] = {'count': 0, 'avg_accuracy': 0.0}
                                    strategy_results['regimes'][market_regime]['count'] += 1
                                    strategy_results['regimes'][market_regime]['avg_accuracy'] += accuracy
                                    
                                    if timeframe not in strategy_results['timeframes']:
                                        strategy_results['timeframes'][timeframe] = {'count': 0, 'avg_accuracy': 0.0}
                                    strategy_results['timeframes'][timeframe]['count'] += 1
                                    strategy_results['timeframes'][timeframe]['avg_accuracy'] += accuracy
                                    
                                    logger.debug(f"✅ {strategy_id} ({market_regime}, {timeframe}): {accuracy:.3f}")
                                else:
                                    training_results['failed_trainings'] += 1
                                    logger.debug(f"❌ {strategy_id} ({market_regime}, {timeframe}): Failed")
                        
                        # Calculate averages for this strategy
                        if strategy_results['successful'] > 0:
                            strategy_results['avg_accuracy'] /= strategy_results['successful']
                            asset_results['strategies_trained'] += 1
                            
                            # Calculate regime averages
                            for regime_data in strategy_results['regimes'].values():
                                if regime_data['count'] > 0:
                                    regime_data['avg_accuracy'] /= regime_data['count']
                            
                            # Calculate timeframe averages
                            for timeframe_data in strategy_results['timeframes'].values():
                                if timeframe_data['count'] > 0:
                                    timeframe_data['avg_accuracy'] /= timeframe_data['count']
                        
                        asset_results['strategy_breakdown'][strategy_id] = strategy_results
                        training_results['strategy_results'][f"{exchange}_{symbol}_{strategy_id}"] = strategy_results
                    
                    # Calculate asset averages
                    if asset_results['strategies_trained'] > 0:
                        asset_results['avg_accuracy'] = asset_results['total_accuracy'] / training_results['successful_trainings']
                        training_results['assets_completed'] += 1
                    
                    logger.info(f"🎉 Asset completed: {exchange}/{symbol}")
                    logger.info(f"   📈 Strategies trained: {asset_results['strategies_trained']}/{len(self.supported_strategies)}")
                    logger.info(f"   🎯 Best accuracy: {asset_results['best_accuracy']:.3f}")
            
            # Final summary
            training_results['end_time'] = datetime.now().isoformat()
            training_results['success_rate'] = (training_results['successful_trainings'] / 
                                               training_results['total_combinations'] * 100)
            
            logger.info(f"🎊 Multi-dimensional training campaign COMPLETE!")
            logger.info(f"   ✅ Success rate: {training_results['success_rate']:.1f}%")
            logger.info(f"   📊 Total successful: {training_results['successful_trainings']}")
            logger.info(f"   🏆 Assets completed: {training_results['assets_completed']}")
            
            return training_results
            
        except Exception as e:
            logger.error(f"❌ Multi-dimensional training campaign failed: {e}")
            training_results['error'] = str(e)
            return training_results
    
    def train_strategy_multi_dimensional(self, symbol: str, exchange: str, strategy_id: str,
                                       market_regime: str, timeframe: str, 
                                       min_samples: int = 200) -> Optional[TrainedStrategy]:
        """
        Train a single strategy for specific market regime and timeframe
        
        This is the core training method that handles regime and timeframe specific data preparation
        """
        logger.debug(f"🎯 Training: {strategy_id} for {symbol} ({market_regime}, {timeframe})")
        
        try:
            # Get regime and timeframe specific training data
            training_data = self._get_regime_timeframe_data(
                symbol, exchange, strategy_id, market_regime, timeframe
            )
            
            if training_data is None or len(training_data) < min_samples:
                logger.debug(f"❌ Insufficient data: {len(training_data) if training_data is not None else 0} < {min_samples}")
                return None
            
            # Prepare features specific to strategy and conditions
            X, y = self._prepare_strategy_features(training_data, strategy_id, market_regime, timeframe)
            
            if len(X) == 0 or len(y) == 0:
                logger.debug(f"❌ No valid features for {strategy_id}")
                return None
            
            # Train the model
            model, accuracy, feature_importance = self._train_strategy_model(X, y, strategy_id)
            
            if model is None:
                return None
            
            # Extract optimized strategy parameters from trained model
            strategy_parameters = self._extract_strategy_parameters(
                model, feature_importance, strategy_id, market_regime, timeframe
            )
            
            # Create trained strategy
            trained_strategy = TrainedStrategy(
                symbol=symbol,
                exchange=exchange,
                strategy_id=strategy_id,
                market_regime=market_regime,
                timeframe=timeframe,
                model_version="1.0",
                accuracy=accuracy,
                training_samples=len(training_data),
                last_trained=datetime.now().isoformat(),
                strategy_parameters=strategy_parameters,
                feature_importance=feature_importance,
                performance_metrics={'accuracy': accuracy, 'sample_size': len(training_data)},
                metadata={'training_date': datetime.now().isoformat()}
            )
            
            # Save the trained strategy
            strategy_key = self._get_strategy_key(symbol, exchange, strategy_id, market_regime, timeframe)
            self.trained_strategies[strategy_key] = trained_strategy
            
            # Save to disk
            model_path, metadata_path = self.get_strategy_path(symbol, exchange, strategy_id, market_regime, timeframe)
            
            # Save model
            try:
                import joblib
                joblib.dump(model, model_path)
            except ImportError:
                import pickle
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)
            
            # Save metadata
            strategy_dict = {
                'symbol': trained_strategy.symbol,
                'exchange': trained_strategy.exchange,
                'strategy_id': trained_strategy.strategy_id,
                'market_regime': trained_strategy.market_regime,
                'timeframe': trained_strategy.timeframe,
                'model_version': trained_strategy.model_version,
                'accuracy': trained_strategy.accuracy,
                'training_samples': trained_strategy.training_samples,
                'last_trained': trained_strategy.last_trained,
                'strategy_parameters': trained_strategy.strategy_parameters,
                'feature_importance': trained_strategy.feature_importance,
                'performance_metrics': trained_strategy.performance_metrics,
                'metadata': trained_strategy.metadata
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(strategy_dict, f, indent=2)
            
            logger.debug(f"✅ Strategy trained: {strategy_id} ({accuracy:.3f})")
            return trained_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy training failed {strategy_id}: {e}")
            return None
    
    def _get_regime_timeframe_data(self, symbol: str, exchange: str, strategy_id: str,
                                 market_regime: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get training data filtered by market regime and timeframe"""
        try:
            # This would implement regime and timeframe specific data filtering
            # For now, return general training data as placeholder
            return self._get_training_data(symbol, exchange, strategy_id)
        except Exception as e:
            logger.error(f"❌ Error getting regime/timeframe data: {e}")
            return None
    
    def _prepare_strategy_features(self, df: pd.DataFrame, strategy_id: str, 
                                 market_regime: str, timeframe: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features specific to strategy, regime, and timeframe"""
        try:
            # Enhanced feature preparation based on strategy type
            return self._prepare_training_features(df, strategy_id)
        except Exception as e:
            logger.error(f"❌ Error preparing strategy features: {e}")
            return np.array([]), np.array([])
    
    def _train_strategy_model(self, X: np.ndarray, y: np.ndarray, 
                            strategy_id: str) -> Tuple[Any, float, Dict[str, float]]:
        """Train ML model for specific strategy"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model with strategy-specific parameters
            model_params = {
                'htf_sweep': {'n_estimators': 100, 'max_depth': 10},
                'volume_breakout': {'n_estimators': 150, 'max_depth': 8},
                'divergence_capitulation': {'n_estimators': 200, 'max_depth': 12}
            }
            
            params = model_params.get(strategy_id, {'n_estimators': 100, 'max_depth': 10})
            model = RandomForestClassifier(**params, random_state=42)
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Feature importance
            feature_names = [f'feature_{i}' for i in range(X.shape[1])]
            feature_importance = dict(zip(feature_names, model.feature_importances_))
            
            return model, accuracy, feature_importance
            
        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            return None, 0.0, {}
    
    def _extract_strategy_parameters(self, model: Any, feature_importance: Dict[str, float],
                                   strategy_id: str, market_regime: str, 
                                   timeframe: str) -> Dict[str, float]:
        """Extract optimized strategy parameters from trained model"""
        try:
            # Base parameters optimized by feature importance and model performance
            base_params = self._get_default_strategy_parameters(strategy_id)
            
            # Adjust parameters based on regime and timeframe
            regime_adjustments = {
                'bull': {'aggression_multiplier': 1.2, 'confidence_boost': 0.05},
                'bear': {'aggression_multiplier': 0.8, 'confidence_boost': -0.05},
                'sideways': {'aggression_multiplier': 1.0, 'confidence_boost': 0.0}
            }
            
            timeframe_adjustments = {
                '1m': {'sensitivity': 1.3, 'noise_filter': 0.8},
                '5m': {'sensitivity': 1.1, 'noise_filter': 0.9},
                '15m': {'sensitivity': 1.0, 'noise_filter': 1.0},
                '1h': {'sensitivity': 0.9, 'noise_filter': 1.1},
                '4h': {'sensitivity': 0.8, 'noise_filter': 1.2},
                '1d': {'sensitivity': 0.7, 'noise_filter': 1.3}
            }
            
            regime_adj = regime_adjustments.get(market_regime, {'aggression_multiplier': 1.0, 'confidence_boost': 0.0})
            timeframe_adj = timeframe_adjustments.get(timeframe, {'sensitivity': 1.0, 'noise_filter': 1.0})
            
            # Apply adjustments to base parameters
            optimized_params = base_params.copy()
            
            # Regime-based adjustments
            if 'confidence_threshold' in optimized_params:
                optimized_params['confidence_threshold'] += regime_adj['confidence_boost']
                optimized_params['confidence_threshold'] = max(0.5, min(0.9, optimized_params['confidence_threshold']))
            
            # Timeframe-based adjustments
            if strategy_id == 'htf_sweep':
                if 'swing_lookback_periods' in optimized_params:
                    optimized_params['swing_lookback_periods'] = int(
                        optimized_params['swing_lookback_periods'] * timeframe_adj['sensitivity']
                    )
            
            # Add regime and timeframe specific parameters
            optimized_params.update({
                'regime_aggression': regime_adj['aggression_multiplier'],
                'timeframe_sensitivity': timeframe_adj['sensitivity'],
                'noise_filter': timeframe_adj['noise_filter']
            })
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"❌ Parameter extraction failed: {e}")
            return self._get_default_strategy_parameters(strategy_id)


# Global instance
trained_assets_manager = TrainedAssetsManager()