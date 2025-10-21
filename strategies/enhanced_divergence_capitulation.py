import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent
from ml.pattern_recognizer import ml_recognizer
from policy.pattern_library import Tier1Patterns
from utils.logger import log as logger

class EnhancedDivergenceCapitulation(BaseStrategy):
    """
    ML-Enhanced Divergence-Confirmed Capitulation Strategy
    
    Combines traditional divergence analysis with ML pattern recognition
    and multi-timeframe confirmation for improved signal accuracy.
    """
    def __init__(self, symbol: str, data: dict):
        super().__init__(symbol, data)
        self.timeframe = '1h'
        self.rsi_period = 14
        self.divergence_lookback = 10
        self.ml_recognizer = ml_recognizer
        self.pattern_detector = Tier1Patterns(symbol)

    def _get_enhanced_market_data(self, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get market data from enhanced database"""
        return self.pattern_detector.fetch_recent_data(limit=limit, timeframe=timeframe)

    def check_signal(self):
        """
        Enhanced signal checking with ML confidence scoring
        
        1. Traditional divergence and capitulation analysis
        2. ML-enhanced confidence scoring
        3. Multi-timeframe confirmation
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

        # Enhanced ML Analysis
        try:
            # Base confidence from traditional analysis
            base_confidence = 0.75
            
            # Enhance with ML pattern recognition
            ml_confidence = self.ml_recognizer.enhance_signal_confidence(
                base_confidence, 'divergence_strength', df, self.timeframe
            )
            
            # Multi-timeframe analysis
            mtf_analysis = self.ml_recognizer.get_multi_timeframe_analysis(
                self.symbol, 'divergence_strength'
            )
            
            # Calculate multi-timeframe confidence
            mtf_confidence = (
                mtf_analysis.get('5m', 0.5) * 0.2 +
                mtf_analysis.get('1h', 0.5) * 0.5 +
                mtf_analysis.get('4h', 0.5) * 0.3
            )
            
            # Final confidence calculation
            final_confidence = (ml_confidence * 0.6 + mtf_confidence * 0.4)
            
            # Only signal if confidence is above threshold
            if final_confidence < 0.6:
                logger.info(f"🚫 {self.symbol}: Divergence detected but ML confidence too low ({final_confidence:.3f})")
                return None
            
            # Check for additional pattern confirmation
            liquidity_sweep = self.pattern_detector.check_for_liquidity_sweep()
            fair_value_gap = self.pattern_detector.check_for_fair_value_gap()
            
            # Boost confidence if additional patterns are detected
            pattern_boost = 0.0
            if liquidity_sweep:
                pattern_boost += 0.1
                logger.info(f"🎯 {self.symbol}: Liquidity sweep detected, boosting confidence")
            if fair_value_gap:
                pattern_boost += 0.05
                logger.info(f"📊 {self.symbol}: Fair value gap detected, boosting confidence")
            
            final_confidence = min(0.95, final_confidence + pattern_boost)
            
            # Calculate dynamic targets based on volatility
            atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
            volatility_multiplier = max(1.5, min(3.0, atr / capitulation_candle['close'] * 100))
            
            price = capitulation_candle['close']
            price_target = price * (1 + 0.04 * volatility_multiplier)  # Dynamic target
            stop_loss = capitulation_candle['low'] * 0.995  # Tight stop below the low
            
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='ENHANCED_DIVERGENCE_CAPITULATION',
                price=price,
                confidence=final_confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                metadata={
                    'ml_confidence': ml_confidence,
                    'mtf_confidence': mtf_confidence,
                    'pattern_boost': pattern_boost,
                    'volatility_multiplier': volatility_multiplier,
                    'liquidity_sweep': bool(liquidity_sweep),
                    'fair_value_gap': bool(fair_value_gap),
                    'rsi_divergence_strength': last_low_2['rsi'] - last_low_1['rsi'],
                    'capitulation_strength': body_size / candle_range
                }
            )
            
            logger.info(f"🚀 BUY Signal: {self.symbol} by ENHANCED_DIVERGENCE_CAPITULATION")
            logger.info(f"   💪 Confidence: {final_confidence:.3f} (ML: {ml_confidence:.3f}, MTF: {mtf_confidence:.3f})")
            logger.info(f"   🎯 Target: ${price_target:.2f} | 🛑 Stop: ${stop_loss:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error in ML analysis for {self.symbol}: {e}")
            # Fallback to traditional signal with reduced confidence
            price = capitulation_candle['close']
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='BUY',
                strategy_id='DIVERGENCE_CAPITULATION_FALLBACK',
                price=price,
                confidence=0.6,  # Reduced confidence for fallback
                price_target=price * 1.05,
                stop_loss=capitulation_candle['low'] * 0.99
            )
            logger.info(f"⚠️ Fallback BUY Signal: {self.symbol} (ML analysis failed)")
            return signal