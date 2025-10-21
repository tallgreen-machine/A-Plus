#!/usr/bin/env python3
"""
Enhanced Pattern Library - Uses ML-trained assets to provide superior pattern detection
Integrates traditional pattern detection with per-token, per-exchange ML optimization
"""

import sys
import os
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

from policy.pattern_library import Tier1Patterns, PATTERN_REGISTRY, register_pattern
from ml.pattern_ml_engine import PatternMLEngine
from utils.logger import log as logger
from typing import Dict, Optional, Any

@register_pattern("Enhanced")
class EnhancedPatterns(Tier1Patterns):
    """
    Enhanced pattern detection using ML-trained assets
    Provides pattern confidence scores optimized per symbol-exchange combination
    """
    
    def __init__(self, symbol="BTC/USDT", exchange="binanceus"):
        super().__init__(symbol)
        self.exchange = exchange
        self.ml_engine = PatternMLEngine()
        
        # Extract base symbol (remove /USDT, /USD, etc.)
        self.base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
        
    def check_for_liquidity_sweep_enhanced(self, timeframe='5m') -> Optional[Dict[str, Any]]:
        """
        Enhanced liquidity sweep detection using ML-trained confidence weights
        """
        # Get base pattern detection result
        base_result = self.check_for_liquidity_sweep()
        
        if base_result is None:
            return None
        
        # Enhance confidence using trained asset
        base_confidence = base_result.get('confidence', 0.71)
        enhanced_confidence = self.ml_engine.get_pattern_confidence(
            symbol=self.symbol,
            exchange=self.exchange,
            pattern_name='liquidity_sweep',
            base_confidence=base_confidence,
            timeframe=timeframe
        )
        
        # Create enhanced result
        enhanced_result = base_result.copy()
        enhanced_result['confidence'] = enhanced_confidence
        enhanced_result['enhancement'] = 'ML_TRAINED'
        enhanced_result['original_confidence'] = base_confidence
        enhanced_result['ml_weight'] = enhanced_confidence / base_confidence if base_confidence > 0 else 1.0
        
        logger.info(f"🤖 Enhanced Liquidity Sweep: {self.symbol}/{self.exchange} "
                   f"confidence {base_confidence:.2f} -> {enhanced_confidence:.2f}")
        
        return enhanced_result
    
    def check_for_fair_value_gap_enhanced(self, timeframe='5m') -> Optional[Dict[str, Any]]:
        """
        Enhanced Fair Value Gap detection using ML-trained confidence weights
        """
        # Get base pattern detection result  
        base_result = self.check_for_fair_value_gap()
        
        if base_result is None:
            return None
        
        # Enhance confidence using trained asset
        base_confidence = base_result.get('confidence', 0.65)
        enhanced_confidence = self.ml_engine.get_pattern_confidence(
            symbol=self.symbol,
            exchange=self.exchange,
            pattern_name='fair_value_gap',
            base_confidence=base_confidence,
            timeframe=timeframe
        )
        
        # Create enhanced result
        enhanced_result = base_result.copy()
        enhanced_result['confidence'] = enhanced_confidence
        enhanced_result['enhancement'] = 'ML_TRAINED'
        enhanced_result['original_confidence'] = base_confidence
        enhanced_result['ml_weight'] = enhanced_confidence / base_confidence if base_confidence > 0 else 1.0
        
        logger.info(f"🤖 Enhanced Fair Value Gap: {self.symbol}/{self.exchange} "
                   f"confidence {base_confidence:.2f} -> {enhanced_confidence:.2f}")
        
        return enhanced_result
    
    def check_for_volume_spike_enhanced(self, timeframe='5m') -> Optional[Dict[str, Any]]:
        """
        Enhanced volume spike detection using ML patterns
        """
        df = self.fetch_recent_data(limit=30, timeframe=timeframe)
        if len(df) < 20:
            return None
        
        # Calculate volume metrics
        recent_volume = df['volume'].iloc[-20:-1].mean()  # Exclude current candle
        current_volume = df['volume'].iloc[-1]
        volume_ratio = current_volume / recent_volume if recent_volume > 0 else 0
        
        # Base pattern: significant volume spike
        if volume_ratio < 2.0:  # Less than 2x average volume
            return None
        
        # Base confidence based on volume ratio
        base_confidence = min(0.9, (volume_ratio - 1.0) / 10.0)  # Scale to reasonable range
        
        # Enhance confidence using trained asset
        enhanced_confidence = self.ml_engine.get_pattern_confidence(
            symbol=self.symbol,
            exchange=self.exchange,
            pattern_name='volume_spike',
            base_confidence=base_confidence,
            timeframe=timeframe
        )
        
        current_price = df['close'].iloc[-1]
        
        result = {
            'pattern_name': 'Volume Spike',
            'confidence': enhanced_confidence,
            'enhancement': 'ML_TRAINED',
            'original_confidence': base_confidence,
            'ml_weight': enhanced_confidence / base_confidence if base_confidence > 0 else 1.0,
            'details': {
                'price': current_price,
                'volume_ratio': volume_ratio,
                'current_volume': current_volume,
                'average_volume': recent_volume
            }
        }
        
        logger.info(f"🤖 Enhanced Volume Spike: {self.symbol}/{self.exchange} "
                   f"confidence {base_confidence:.2f} -> {enhanced_confidence:.2f} "
                   f"(volume: {volume_ratio:.1f}x)")
        
        return result
    
    def scan_all_patterns_enhanced(self, timeframe='5m') -> Dict[str, Any]:
        """
        Scan for all enhanced patterns and return comprehensive results
        """
        patterns = {}
        
        # Check all enhanced patterns
        liquidity_sweep = self.check_for_liquidity_sweep_enhanced(timeframe)
        if liquidity_sweep:
            patterns['liquidity_sweep'] = liquidity_sweep
        
        fair_value_gap = self.check_for_fair_value_gap_enhanced(timeframe)
        if fair_value_gap:
            patterns['fair_value_gap'] = fair_value_gap
        
        volume_spike = self.check_for_volume_spike_enhanced(timeframe)
        if volume_spike:
            patterns['volume_spike'] = volume_spike
        
        # Calculate overall pattern strength
        if patterns:
            avg_confidence = sum(p['confidence'] for p in patterns.values()) / len(patterns)
            max_confidence = max(p['confidence'] for p in patterns.values())
            
            summary = {
                'total_patterns': len(patterns),
                'average_confidence': avg_confidence,
                'max_confidence': max_confidence,
                'patterns': patterns,
                'enhancement': 'ML_TRAINED',
                'asset': f"{self.symbol}/{self.exchange}",
                'timeframe': timeframe
            }
        else:
            summary = {
                'total_patterns': 0,
                'patterns': {},
                'asset': f"{self.symbol}/{self.exchange}",
                'timeframe': timeframe
            }
        
        return summary

class EnhancedPatternFactory:
    """
    Factory for creating enhanced pattern detectors for specific assets
    """
    
    @staticmethod
    def create_for_asset(symbol: str, exchange: str) -> EnhancedPatterns:
        """Create enhanced pattern detector for specific symbol-exchange combination"""
        return EnhancedPatterns(symbol=symbol, exchange=exchange)
    
    @staticmethod
    def scan_all_assets(timeframe='5m') -> Dict[str, Any]:
        """
        Scan patterns across all available assets
        Returns comprehensive market pattern overview
        """
        from ml.pattern_ml_engine import PatternMLEngine
        
        engine = PatternMLEngine()
        available_assets = engine.get_available_assets()
        
        all_patterns = {}
        summary_stats = {
            'total_assets_scanned': 0,
            'assets_with_patterns': 0,
            'total_patterns_found': 0,
            'top_patterns': []
        }
        
        for symbol, exchange in available_assets:
            try:
                detector = EnhancedPatterns(symbol=symbol, exchange=exchange)
                asset_patterns = detector.scan_all_patterns_enhanced(timeframe)
                
                asset_key = f"{symbol}_{exchange}"
                all_patterns[asset_key] = asset_patterns
                
                summary_stats['total_assets_scanned'] += 1
                if asset_patterns['total_patterns'] > 0:
                    summary_stats['assets_with_patterns'] += 1
                    summary_stats['total_patterns_found'] += asset_patterns['total_patterns']
                    
                    # Track top patterns
                    for pattern_name, pattern_data in asset_patterns['patterns'].items():
                        summary_stats['top_patterns'].append({
                            'asset': asset_key,
                            'pattern': pattern_name,
                            'confidence': pattern_data['confidence']
                        })
                        
            except Exception as e:
                logger.error(f"Error scanning patterns for {symbol}/{exchange}: {e}")
        
        # Sort top patterns by confidence
        summary_stats['top_patterns'].sort(key=lambda x: x['confidence'], reverse=True)
        summary_stats['top_patterns'] = summary_stats['top_patterns'][:10]  # Top 10
        
        return {
            'summary': summary_stats,
            'asset_patterns': all_patterns,
            'scan_timeframe': timeframe
        }

if __name__ == "__main__":
    # Example usage
    print("🤖 Enhanced Pattern Detection System")
    
    # Test single asset
    detector = EnhancedPatterns(symbol="BTC/USDT", exchange="binanceus")
    patterns = detector.scan_all_patterns_enhanced()
    print(f"BTC/USDT patterns: {patterns}")
    
    # Test all assets
    print("\n📊 Scanning all assets...")
    all_results = EnhancedPatternFactory.scan_all_assets()
    print(f"Market scan complete: {all_results['summary']}")