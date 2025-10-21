import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy
from core.event_system import SignalEvent
from ml.pattern_recognizer import ml_recognizer
from policy.pattern_library import Tier1Patterns
from utils.logger import log as logger

class EnhancedHTFSweep(BaseStrategy):
    """
    ML-Enhanced HTF Sweep Strategy
    
    Combines traditional higher timeframe sweep analysis with ML pattern recognition,
    multi-timeframe confirmation, and liquidity zone identification.
    """
    def __init__(self, symbol: str, data: dict):
        super().__init__(symbol, data)
        self.htf = '4h'
        self.ltf = '1h'
        self.confirmation_tf = '15m'
        self.ml_recognizer = ml_recognizer
        self.pattern_detector = Tier1Patterns(symbol)

    def _get_enhanced_market_data(self, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get market data from enhanced database"""
        return self.pattern_detector.fetch_recent_data(limit=limit, timeframe=timeframe)

    def check_signal(self):
        """
        Enhanced HTF sweep signal checking with ML and multi-timeframe analysis
        
        1. Traditional HTF sweep detection
        2. ML-enhanced liquidity zone analysis
        3. Multi-timeframe momentum confirmation
        4. Volume profile validation
        
        :return: A SignalEvent if conditions are met, otherwise None.
        """
        df_htf = self._get_enhanced_market_data(self.htf, limit=50)
        df_ltf = self._get_enhanced_market_data(self.ltf, limit=100)
        df_conf = self._get_enhanced_market_data(self.confirmation_tf, limit=200)

        if df_htf.empty or len(df_htf) < 3 or df_ltf.empty or df_conf.empty:
            return None

        # HTF analysis - Traditional sweep detection
        htf_prev_candle = df_htf.iloc[-2]
        htf_last_candle = df_htf.iloc[-1]
        
        htf_high_to_sweep = htf_prev_candle['high']

        # Condition 1: Last HTF candle swept the previous high but closed below it
        is_sweep = (htf_last_candle['high'] > htf_high_to_sweep) and \
                   (htf_last_candle['close'] < htf_high_to_sweep)

        if not is_sweep:
            return None
            
        # Condition 2: LTF confirmation with a bearish close
        ltf_last_candle = df_ltf.iloc[-1]
        is_ltf_confirmation = ltf_last_candle['close'] < ltf_last_candle['open']

        if not is_ltf_confirmation:
            return None

        # Enhanced ML Analysis
        try:
            # Base confidence from traditional analysis
            base_confidence = 0.8
            
            # Check for liquidity sweep pattern using ML
            liquidity_sweep = self.pattern_detector.check_for_liquidity_sweep()
            if liquidity_sweep:
                base_confidence += 0.1  # Boost for confirmed liquidity sweep
                logger.info(f"🎯 {self.symbol}: Liquidity sweep pattern confirmed")
            
            # Enhance with ML pattern recognition
            ml_confidence_htf = self.ml_recognizer.enhance_signal_confidence(
                base_confidence, 'liquidity_sweep', df_htf, self.htf
            )
            
            ml_confidence_ltf = self.ml_recognizer.enhance_signal_confidence(
                base_confidence, 'liquidity_sweep', df_ltf, self.ltf
            )
            
            # Multi-timeframe analysis
            mtf_analysis = self.ml_recognizer.get_multi_timeframe_analysis(
                self.symbol, 'liquidity_sweep'
            )
            
            # Calculate comprehensive confidence
            htf_weight = 0.4
            ltf_weight = 0.3
            mtf_weight = 0.3
            
            final_confidence = (
                ml_confidence_htf * htf_weight +
                ml_confidence_ltf * ltf_weight +
                (mtf_analysis.get('4h', 0.5) * 0.5 + mtf_analysis.get('1h', 0.5) * 0.5) * mtf_weight
            )
            
            # Momentum and volume analysis
            momentum_score = self._analyze_momentum(df_conf)
            volume_score = self._analyze_volume_confirmation(df_htf, df_ltf)
            
            # Adjust confidence based on momentum and volume
            momentum_adjustment = (momentum_score - 0.5) * 0.2  # ±0.1 max adjustment
            volume_adjustment = (volume_score - 0.5) * 0.15    # ±0.075 max adjustment
            
            final_confidence += momentum_adjustment + volume_adjustment
            final_confidence = max(0.1, min(0.95, final_confidence))
            
            # Only signal if confidence is above threshold
            if final_confidence < 0.65:
                logger.info(f"🚫 {self.symbol}: HTF sweep detected but ML confidence too low ({final_confidence:.3f})")
                return None
            
            # Calculate dynamic targets based on sweep analysis
            sweep_magnitude = htf_last_candle['high'] - htf_high_to_sweep
            atr_htf = ta.atr(df_htf['high'], df_htf['low'], df_htf['close'], length=14).iloc[-1]
            
            # Risk-reward calculation
            price = ltf_last_candle['close']
            stop_loss = htf_last_candle['high'] * 1.002  # Stop above the sweep high with buffer
            
            # Dynamic target based on sweep magnitude and volatility
            target_multiplier = max(1.5, min(3.0, sweep_magnitude / atr_htf))
            risk_amount = stop_loss - price
            price_target = price - (risk_amount * target_multiplier)
            
            # Ensure minimum risk-reward ratio
            if (price - price_target) / (stop_loss - price) < 1.5:
                price_target = price - (risk_amount * 1.5)
            
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='SELL',
                strategy_id='ENHANCED_HTF_SWEEP',
                price=price,
                confidence=final_confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                metadata={
                    'ml_confidence_htf': ml_confidence_htf,
                    'ml_confidence_ltf': ml_confidence_ltf,
                    'mtf_analysis': mtf_analysis,
                    'momentum_score': momentum_score,
                    'volume_score': volume_score,
                    'sweep_magnitude': sweep_magnitude,
                    'target_multiplier': target_multiplier,
                    'liquidity_sweep_detected': bool(liquidity_sweep),
                    'htf_sweep_high': htf_last_candle['high'],
                    'htf_reference_high': htf_high_to_sweep
                }
            )
            
            logger.info(f"🔻 SELL Signal: {self.symbol} by ENHANCED_HTF_SWEEP")
            logger.info(f"   💪 Confidence: {final_confidence:.3f} (HTF: {ml_confidence_htf:.3f}, LTF: {ml_confidence_ltf:.3f})")
            logger.info(f"   📊 Momentum: {momentum_score:.3f} | Volume: {volume_score:.3f}")
            logger.info(f"   🎯 Target: ${price_target:.2f} | 🛑 Stop: ${stop_loss:.2f} | RR: {((price - price_target) / (stop_loss - price)):.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error in ML analysis for {self.symbol}: {e}")
            # Fallback to traditional signal with reduced confidence
            price = ltf_last_candle['close']
            signal = SignalEvent(
                symbol=self.symbol,
                signal_type='SELL',
                strategy_id='HTF_SWEEP_FALLBACK',
                price=price,
                confidence=0.65,  # Reduced confidence for fallback
                price_target=price * 0.95,
                stop_loss=htf_last_candle['high']
            )
            logger.info(f"⚠️ Fallback SELL Signal: {self.symbol} (ML analysis failed)")
            return signal
    
    def _analyze_momentum(self, df: pd.DataFrame) -> float:
        """Analyze momentum using multiple indicators on confirmation timeframe"""
        if len(df) < 20:
            return 0.5
        
        try:
            # RSI momentum
            rsi = ta.rsi(df['close'], length=14).iloc[-1]
            rsi_score = 1.0 - (rsi / 100.0)  # For bearish signals, lower RSI is better
            
            # MACD momentum
            macd_line = ta.macd(df['close'])['MACD_12_26_9'].iloc[-1]
            macd_signal = ta.macd(df['close'])['MACDs_12_26_9'].iloc[-1]
            macd_score = 1.0 if macd_line < macd_signal else 0.3
            
            # Price vs moving averages
            sma_20 = ta.sma(df['close'], length=20).iloc[-1]
            price_vs_sma = df['close'].iloc[-1] / sma_20
            sma_score = max(0.0, min(1.0, (1.05 - price_vs_sma) / 0.1))  # Score higher when price is below SMA
            
            # Weighted momentum score
            momentum_score = (rsi_score * 0.4 + macd_score * 0.3 + sma_score * 0.3)
            return max(0.0, min(1.0, momentum_score))
            
        except Exception:
            return 0.5
    
    def _analyze_volume_confirmation(self, df_htf: pd.DataFrame, df_ltf: pd.DataFrame) -> float:
        """Analyze volume confirmation across timeframes"""
        if len(df_htf) < 10 or len(df_ltf) < 20:
            return 0.5
        
        try:
            # HTF volume analysis
            htf_vol_avg = df_htf['volume'].rolling(10).mean().iloc[-1]
            htf_current_vol = df_htf['volume'].iloc[-1]
            htf_vol_ratio = htf_current_vol / htf_vol_avg if htf_vol_avg > 0 else 1.0
            
            # LTF volume analysis
            ltf_vol_avg = df_ltf['volume'].rolling(20).mean().iloc[-1]
            ltf_current_vol = df_ltf['volume'].iloc[-1]
            ltf_vol_ratio = ltf_current_vol / ltf_vol_avg if ltf_vol_avg > 0 else 1.0
            
            # Volume confirmation score (higher volume = higher confidence for sweeps)
            htf_vol_score = min(1.0, htf_vol_ratio / 2.0)  # Cap at 1.0, normalize around 2x average
            ltf_vol_score = min(1.0, ltf_vol_ratio / 1.5)  # Cap at 1.0, normalize around 1.5x average
            
            volume_score = (htf_vol_score * 0.6 + ltf_vol_score * 0.4)
            return max(0.0, min(1.0, volume_score))
            
        except Exception:
            return 0.5