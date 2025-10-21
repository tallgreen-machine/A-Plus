import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent
from ml.pattern_recognizer import ml_recognizer
from policy.pattern_library import Tier1Patterns
from utils.logger import log as logger

class EnhancedVolumeBreakout(BaseStrategy):
    """
    ML-Enhanced Volume-Confirmed Breakout Strategy
    
    Combines traditional volume breakout analysis with ML pattern recognition,
    multi-timeframe confirmation, and smart resistance/support level detection.
    """
    def __init__(self, symbol: str, data: dict):
        super().__init__(symbol, data)
        self.timeframe = '1h'
        self.confirmation_tf = '15m'
        self.htf = '4h'
        self.resistance_lookback = 24
        self.volume_sma_period = 20
        self.volume_multiplier = 2.0
        self.ml_recognizer = ml_recognizer
        self.pattern_detector = Tier1Patterns(symbol)

    def _get_enhanced_market_data(self, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get market data from enhanced database"""
        return self.pattern_detector.fetch_recent_data(limit=limit, timeframe=timeframe)

    def check_signal(self):
        """
        Enhanced volume breakout signal checking with ML and smart level detection
        
        1. Smart resistance/support level identification
        2. ML-enhanced breakout validation
        3. Multi-timeframe volume confirmation
        4. Fair value gap integration
        
        :return: A SignalEvent if conditions are met, otherwise None.
        """
        df = self._get_enhanced_market_data(self.timeframe, limit=50)
        df_conf = self._get_enhanced_market_data(self.confirmation_tf, limit=200)
        df_htf = self._get_enhanced_market_data(self.htf, limit=30)

        if df.empty or len(df) < self.resistance_lookback + 1:
            return None

        # Add volume indicators
        df['vol_sma'] = ta.sma(df['volume'], length=self.volume_sma_period)

        # Smart resistance level detection using multiple methods
        resistance_levels = self._detect_smart_resistance_levels(df, df_htf)
        if not resistance_levels:
            return None

        last_candle = df.iloc[-1]
        
        # Find the most relevant resistance level for breakout
        current_price = last_candle['close']
        relevant_resistance = None
        
        for level in resistance_levels:
            if level['price'] > current_price * 0.995 and level['price'] < current_price * 1.05:
                relevant_resistance = level
                break
        
        if not relevant_resistance:
            return None

        # Enhanced breakout detection
        is_breakout = current_price > relevant_resistance['price']
        
        # Traditional volume confirmation
        vol_sma = last_candle['vol_sma']
        is_volume_confirmed = vol_sma > 0 and last_candle['volume'] > (vol_sma * self.volume_multiplier)

        if not (is_breakout and is_volume_confirmed):
            return None

        # Enhanced ML Analysis
        try:
            # Base confidence from traditional analysis
            base_confidence = 0.85
            
            # Enhance with ML pattern recognition
            ml_confidence = self.ml_recognizer.enhance_signal_confidence(
                base_confidence, 'volume_confirmation', df, self.timeframe
            )
            
            # Multi-timeframe analysis
            mtf_analysis = self.ml_recognizer.get_multi_timeframe_analysis(
                self.symbol, 'volume_confirmation'
            )
            
            # Volume profile analysis across timeframes
            volume_profile = self._analyze_volume_profile(df, df_conf, df_htf)
            
            # Pattern detection enhancements
            fair_value_gap = self.pattern_detector.check_for_fair_value_gap()
            
            # Calculate comprehensive confidence
            resistance_strength = relevant_resistance.get('strength', 0.5)
            volume_strength = self._calculate_volume_strength(df)
            
            # Weighted confidence calculation
            final_confidence = (
                ml_confidence * 0.35 +
                mtf_analysis.get('1h', 0.5) * 0.25 +
                mtf_analysis.get('4h', 0.5) * 0.2 +
                resistance_strength * 0.1 +
                volume_strength * 0.1
            )
            
            # Pattern bonuses
            pattern_boost = 0.0
            if fair_value_gap:
                pattern_boost += 0.08
                logger.info(f"📊 {self.symbol}: Fair value gap detected, boosting confidence")
            
            if volume_profile['score'] > 0.7:
                pattern_boost += 0.05
                logger.info(f"📈 {self.symbol}: Strong volume profile, boosting confidence")
            
            final_confidence = min(0.95, final_confidence + pattern_boost)
            
            # Only signal if confidence is above threshold
            if final_confidence < 0.7:
                logger.info(f"🚫 {self.symbol}: Breakout detected but ML confidence too low ({final_confidence:.3f})")
                return None
            
            # Dynamic target calculation based on resistance analysis and volatility
            atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
            resistance_gap = self._calculate_next_resistance_level(df, df_htf, current_price)
            
            # Calculate stop loss and target
            stop_loss = relevant_resistance['price'] * 0.998  # Stop below resistance with buffer
            
            if resistance_gap:
                # Target next resistance level minus some buffer
                price_target = resistance_gap * 0.95
            else:
                # Use ATR-based target
                volatility_multiplier = max(2.0, min(4.0, atr / current_price * 200))
                risk_amount = current_price - stop_loss
                price_target = current_price + (risk_amount * volatility_multiplier)
            
            # Ensure minimum risk-reward ratio
            risk_amount = current_price - stop_loss
            reward_amount = price_target - current_price
            if reward_amount / risk_amount < 2.0:
                price_target = current_price + (risk_amount * 2.0)
            
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='ENHANCED_VOLUME_BREAKOUT',
                price=current_price,
                confidence=final_confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                metadata={
                    'ml_confidence': ml_confidence,
                    'mtf_analysis': mtf_analysis,
                    'resistance_level': relevant_resistance['price'],
                    'resistance_strength': resistance_strength,
                    'volume_strength': volume_strength,
                    'volume_profile': volume_profile,
                    'pattern_boost': pattern_boost,
                    'fair_value_gap': bool(fair_value_gap),
                    'volume_multiplier_achieved': last_candle['volume'] / vol_sma,
                    'next_resistance': resistance_gap,
                    'risk_reward_ratio': reward_amount / risk_amount if risk_amount > 0 else 0
                }
            )
            
            logger.info(f"🚀 BUY Signal: {self.symbol} by ENHANCED_VOLUME_BREAKOUT")
            logger.info(f"   💪 Confidence: {final_confidence:.3f} (ML: {ml_confidence:.3f})")
            logger.info(f"   📊 Resistance: ${relevant_resistance['price']:.2f} (strength: {resistance_strength:.3f})")
            logger.info(f"   📈 Volume: {last_candle['volume'] / vol_sma:.2f}x average (strength: {volume_strength:.3f})")
            logger.info(f"   🎯 Target: ${price_target:.2f} | 🛑 Stop: ${stop_loss:.2f} | RR: {reward_amount / risk_amount:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error in ML analysis for {self.symbol}: {e}")
            # Fallback to traditional signal
            price = current_price
            stop_loss = relevant_resistance['price']
            price_target = price + (price - stop_loss) * 2
            
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='VOLUME_BREAKOUT_FALLBACK',
                price=price,
                confidence=0.7,
                price_target=price_target,
                stop_loss=stop_loss
            )
            logger.info(f"⚠️ Fallback BUY Signal: {self.symbol} (ML analysis failed)")
            return signal
    
    def _detect_smart_resistance_levels(self, df: pd.DataFrame, df_htf: pd.DataFrame) -> list:
        """Detect smart resistance levels using multiple timeframes and techniques"""
        levels = []
        
        try:
            # Method 1: Recent significant highs
            lookback_df = df.iloc[-(self.resistance_lookback + 1):-1]
            resistance_high = lookback_df['high'].max()
            
            # Find touches of this level
            touches = len(lookback_df[abs(lookback_df['high'] - resistance_high) / resistance_high < 0.005])
            
            levels.append({
                'price': resistance_high,
                'method': 'recent_high',
                'strength': min(1.0, touches / 3.0),  # More touches = stronger
                'touches': touches
            })
            
            # Method 2: HTF resistance levels
            if not df_htf.empty and len(df_htf) >= 10:
                htf_resistance = df_htf['high'].rolling(10).max().iloc[-1]
                levels.append({
                    'price': htf_resistance,
                    'method': 'htf_resistance',
                    'strength': 0.8,  # HTF levels are generally strong
                    'touches': 1
                })
            
            # Method 3: Psychological levels (round numbers)
            current_price = df['close'].iloc[-1]
            for multiplier in [1.01, 1.02, 1.05, 1.1]:
                psych_level = round(current_price * multiplier, -2)  # Round to nearest 100
                if psych_level > current_price:
                    levels.append({
                        'price': psych_level,
                        'method': 'psychological',
                        'strength': 0.6,
                        'touches': 0
                    })
                    break
            
            # Sort by proximity to current price and filter
            current_price = df['close'].iloc[-1]
            levels = [l for l in levels if l['price'] > current_price]
            levels.sort(key=lambda x: abs(x['price'] - current_price))
            
            return levels[:3]  # Return top 3 levels
            
        except Exception:
            return []
    
    def _calculate_next_resistance_level(self, df: pd.DataFrame, df_htf: pd.DataFrame, current_price: float) -> float:
        """Calculate the next significant resistance level for target setting"""
        try:
            # Look for next resistance in current timeframe
            future_highs = df['high'].rolling(5).max()
            next_resistance = None
            
            for high in sorted(future_highs.dropna().unique(), reverse=True):
                if high > current_price * 1.02:  # At least 2% above current price
                    next_resistance = high
                    break
            
            # Check HTF for additional resistance
            if not df_htf.empty:
                htf_highs = df_htf['high'].rolling(5).max()
                for high in sorted(htf_highs.dropna().unique(), reverse=True):
                    if high > current_price * 1.02:
                        if next_resistance is None or high < next_resistance:
                            next_resistance = high
                        break
            
            return next_resistance
            
        except Exception:
            return None
    
    def _analyze_volume_profile(self, df: pd.DataFrame, df_conf: pd.DataFrame, df_htf: pd.DataFrame) -> dict:
        """Analyze volume profile across multiple timeframes"""
        try:
            scores = []
            
            # Current timeframe volume analysis
            if len(df) >= 10:
                recent_vol_avg = df['volume'].rolling(10).mean().iloc[-3:]
                current_vol = df['volume'].iloc[-1]
                vol_trend = recent_vol_avg.pct_change().mean()
                tf_score = min(1.0, (current_vol / recent_vol_avg.mean()) / 2.0) + (vol_trend * 2)
                scores.append(max(0.0, min(1.0, tf_score)))
            
            # Confirmation timeframe volume analysis
            if not df_conf.empty and len(df_conf) >= 20:
                conf_vol_avg = df_conf['volume'].rolling(20).mean().iloc[-1]
                conf_recent_avg = df_conf['volume'].rolling(5).mean().iloc[-1]
                conf_score = min(1.0, (conf_recent_avg / conf_vol_avg) / 1.5) if conf_vol_avg > 0 else 0.5
                scores.append(max(0.0, min(1.0, conf_score)))
            
            # HTF volume analysis
            if not df_htf.empty and len(df_htf) >= 5:
                htf_vol_avg = df_htf['volume'].rolling(5).mean().iloc[-1]
                htf_current = df_htf['volume'].iloc[-1]
                htf_score = min(1.0, (htf_current / htf_vol_avg) / 1.8) if htf_vol_avg > 0 else 0.5
                scores.append(max(0.0, min(1.0, htf_score)))
            
            overall_score = sum(scores) / len(scores) if scores else 0.5
            
            return {
                'score': overall_score,
                'timeframe_scores': scores,
                'analysis_count': len(scores)
            }
            
        except Exception:
            return {'score': 0.5, 'timeframe_scores': [], 'analysis_count': 0}
    
    def _calculate_volume_strength(self, df: pd.DataFrame) -> float:
        """Calculate volume strength score"""
        try:
            if len(df) < self.volume_sma_period:
                return 0.5
            
            current_vol = df['volume'].iloc[-1]
            vol_sma = df['vol_sma'].iloc[-1]
            
            if vol_sma <= 0:
                return 0.5
            
            # Volume ratio relative to average
            vol_ratio = current_vol / vol_sma
            
            # Volume consistency (less variance in recent volume = better)
            recent_vol_std = df['volume'].rolling(5).std().iloc[-1]
            vol_consistency = 1.0 - min(1.0, recent_vol_std / vol_sma)
            
            # Combine ratio and consistency
            strength = (min(1.0, vol_ratio / 3.0) * 0.7 + vol_consistency * 0.3)
            
            return max(0.0, min(1.0, strength))
            
        except Exception:
            return 0.5