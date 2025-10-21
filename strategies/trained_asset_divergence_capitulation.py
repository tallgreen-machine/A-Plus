#!/usr/bin/env python3
"""
Enhanced Divergence Capitulation Strategy with Trained Assets
Uses token-exchange specific ML models for superior pattern recognition
"""

import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional, Any
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent
from ml.trained_assets_manager import trained_assets_manager
from policy.pattern_library import Tier1Patterns
from utils.logger import log as logger


class TrainedAssetDivergenceCapitulation(BaseStrategy):
    """
    ML-Enhanced Divergence-Confirmed Capitulation Strategy using Trained Assets
    
    Uses token-exchange specific ML models to enhance traditional divergence analysis.
    Each symbol-exchange combination has its own trained models for optimal performance.
    """
    
    def __init__(self, symbol: str, data: dict, exchange: str = "binanceus"):
        super().__init__(symbol, data)
        self.exchange = exchange
        self.timeframe = '1h'
        self.rsi_period = 14
        self.divergence_lookback = 10
        
        # ML components
        self.assets_manager = trained_assets_manager
        self.pattern_detector = Tier1Patterns(symbol)
        
        logger.info(f"🎯 Trained Asset Divergence Strategy initialized for {exchange}/{symbol}")

    def _get_enhanced_market_data(self, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get market data from enhanced database for specific exchange"""
        from shared.db import get_db_conn
        
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data_enhanced
            WHERE symbol = %s AND exchange = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s;
        """
        
        db_conn = get_db_conn()
        with db_conn.cursor() as cur:
            cur.execute(query, (self.symbol, self.exchange, timeframe, limit))
            data = cur.fetchall()
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        df = df.sort_values('timestamp', ascending=True).reset_index(drop=True)
        return df

    def check_signal(self):
        """
        Enhanced signal checking with trained asset ML models
        
        1. Traditional divergence and capitulation analysis
        2. Token-exchange specific ML confidence enhancement  
        3. Multi-timeframe trained asset validation
        4. Pattern library integration
        
        :return: A SignalEvent if conditions are met, otherwise None.
        """
        df = self._get_enhanced_market_data(self.timeframe)
        if df.empty or len(df) < self.divergence_lookback + 2:
            return None

        # Add RSI to DataFrame
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)

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
        rsi_makes_higher_low = last_low_2['rsi'] > last_low_1['rsi']
        
        is_divergence = price_makes_lower_low and rsi_makes_higher_low

        if not is_divergence:
            return None

        # Condition 2: Capitulation Candle at the second low
        capitulation_candle = df.loc[last_low_2.name]
        body_size = abs(capitulation_candle['close'] - capitulation_candle['open'])
        candle_range = capitulation_candle['high'] - capitulation_candle['low']
        
        if candle_range == 0:  # Avoid division by zero
            return None
            
        is_capitulation = (body_size / candle_range > 0.7) and (capitulation_candle['close'] < capitulation_candle['open'])

        if not (is_divergence and is_capitulation):
            return None

        # Enhanced ML Analysis using Trained Assets
        try:
            # Base confidence from traditional analysis
            base_confidence = 0.75
            
            # Get trained asset predictions for this specific token-exchange combination
            divergence_ml_confidence = self.assets_manager.predict_pattern_confidence(
                self.symbol, self.exchange, 'divergence_strength', df
            )
            
            # Enhanced divergence strength score
            rsi_divergence_strength = last_low_2['rsi'] - last_low_1['rsi']
            enhanced_divergence_score = self._get_enhanced_divergence_score(
                rsi_divergence_strength, df
            )
            
            # Multi-timeframe trained asset analysis
            mtf_confidences = self._get_multi_timeframe_ml_analysis(['5m', '15m', '1h', '4h'])
            
            # Calculate comprehensive ML-enhanced confidence
            ml_confidence = (
                divergence_ml_confidence * 0.4 +
                enhanced_divergence_score * 0.3 +
                mtf_confidences.get('5m', 0.5) * 0.1 +
                mtf_confidences.get('15m', 0.5) * 0.1 +
                mtf_confidences.get('1h', 0.5) * 0.05 +
                mtf_confidences.get('4h', 0.5) * 0.05
            )
            
            # Final confidence combines traditional and ML analysis
            final_confidence = (base_confidence * 0.3 + ml_confidence * 0.7)
            
            # Check for additional pattern confirmation using traditional library
            liquidity_sweep = self.pattern_detector.check_for_liquidity_sweep()
            fair_value_gap = self.pattern_detector.check_for_fair_value_gap()
            
            # Pattern boost from traditional confirmations
            pattern_boost = 0.0
            if liquidity_sweep:
                pattern_boost += 0.08
                logger.info(f"🎯 {self.symbol}: Liquidity sweep pattern adds confidence")
            if fair_value_gap:
                pattern_boost += 0.05
                logger.info(f"📊 {self.symbol}: Fair value gap pattern adds confidence")
            
            final_confidence = min(0.95, final_confidence + pattern_boost)
            
            # Only signal if ML confidence is above threshold
            if final_confidence < 0.65:
                logger.info(f"🚫 {self.symbol}: Divergence detected but trained asset confidence too low ({final_confidence:.3f})")
                return None
            
            # Calculate dynamic targets based on trained asset insights and volatility
            atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
            volatility_multiplier = max(1.5, min(3.5, atr / capitulation_candle['close'] * 100))
            
            # ML-enhanced target calculation
            ml_target_multiplier = self._get_ml_target_multiplier(df, final_confidence)
            
            price = capitulation_candle['close']
            price_target = price * (1 + 0.04 * volatility_multiplier * ml_target_multiplier)
            stop_loss = capitulation_candle['low'] * 0.995  # Tight stop below the low
            
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='TRAINED_ASSET_DIVERGENCE_CAPITULATION',
                price=price,
                confidence=final_confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                metadata={
                    'exchange': self.exchange,
                    'base_confidence': base_confidence,
                    'ml_confidence': ml_confidence,
                    'divergence_ml_confidence': divergence_ml_confidence,
                    'enhanced_divergence_score': enhanced_divergence_score,
                    'mtf_confidences': mtf_confidences,
                    'pattern_boost': pattern_boost,
                    'volatility_multiplier': volatility_multiplier,
                    'ml_target_multiplier': ml_target_multiplier,
                    'liquidity_sweep': bool(liquidity_sweep),
                    'fair_value_gap': bool(fair_value_gap),
                    'rsi_divergence_strength': rsi_divergence_strength,
                    'capitulation_strength': body_size / candle_range,
                    'trained_asset_strategy': True
                }
            )
            
            logger.info(f"🚀 BUY Signal: {self.exchange}/{self.symbol} by TRAINED_ASSET_DIVERGENCE_CAPITULATION")
            logger.info(f"   💪 Final confidence: {final_confidence:.3f}")
            logger.info(f"   🧠 ML confidence: {ml_confidence:.3f} (divergence: {divergence_ml_confidence:.3f})")
            logger.info(f"   📊 MTF analysis: {mtf_confidences}")
            logger.info(f"   🎯 Target: ${price_target:.2f} | 🛑 Stop: ${stop_loss:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error in trained asset ML analysis for {self.exchange}/{self.symbol}: {e}")
            # Fallback to traditional signal with reduced confidence
            price = capitulation_candle['close']
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='DIVERGENCE_CAPITULATION_FALLBACK',
                price=price,
                confidence=0.6,
                price_target=price * 1.05,
                stop_loss=capitulation_candle['low'] * 0.99,
                metadata={'exchange': self.exchange, 'fallback': True}
            )
            logger.info(f"⚠️ Fallback BUY Signal: {self.exchange}/{self.symbol} (trained asset analysis failed)")
            return signal
    
    def _get_enhanced_divergence_score(self, rsi_divergence: float, df: pd.DataFrame) -> float:
        """Get ML-enhanced divergence strength score using trained assets"""
        try:
            # Use trained asset for divergence strength
            ml_score = self.assets_manager.predict_pattern_confidence(
                self.symbol, self.exchange, 'divergence_strength', df
            )
            
            # Traditional divergence strength
            traditional_score = min(1.0, abs(rsi_divergence) / 15.0)
            
            # Combine scores with more weight to ML if confident
            if ml_score > 0.7:
                return 0.2 * traditional_score + 0.8 * ml_score
            else:
                return 0.6 * traditional_score + 0.4 * ml_score
                
        except Exception as e:
            logger.warning(f"⚠️ Enhanced divergence scoring failed: {e}")
            return min(1.0, abs(rsi_divergence) / 15.0)
    
    def _get_multi_timeframe_ml_analysis(self, timeframes: list) -> Dict[str, float]:
        """Get trained asset analysis across multiple timeframes"""
        confidences = {}
        
        for tf in timeframes:
            try:
                df = self._get_enhanced_market_data(tf, limit=100)
                if df.empty:
                    confidences[tf] = 0.5
                    continue
                
                # Get ML confidence for divergence pattern on this timeframe
                confidence = self.assets_manager.predict_pattern_confidence(
                    self.symbol, self.exchange, 'divergence_strength', df
                )
                confidences[tf] = confidence
                
            except Exception as e:
                logger.warning(f"⚠️ Multi-timeframe analysis failed for {tf}: {e}")
                confidences[tf] = 0.5
        
        return confidences
    
    def _get_ml_target_multiplier(self, df: pd.DataFrame, confidence: float) -> float:
        """Calculate ML-enhanced target multiplier based on market conditions"""
        try:
            # Base multiplier on confidence
            base_multiplier = 0.8 + (confidence * 0.4)  # 0.8 to 1.2 range
            
            # Get volume confirmation from trained asset
            volume_confidence = self.assets_manager.predict_pattern_confidence(
                self.symbol, self.exchange, 'volume_confirmation', df
            )
            
            # Adjust based on volume confirmation
            if volume_confidence > 0.7:
                base_multiplier *= 1.2
            elif volume_confidence < 0.4:
                base_multiplier *= 0.8
            
            return max(0.5, min(2.0, base_multiplier))
            
        except Exception:
            return 1.0