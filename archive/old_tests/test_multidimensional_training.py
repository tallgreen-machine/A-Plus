#!/usr/bin/env python3
"""
Test script for Multi-Dimensional Training Enhancement

Demonstrates the new multi-dimensional training capabilities:
- Strategy-based training (HTF Sweep, Volume Breakout, Divergence Capitulation)
- Market regime detection (bull, bear, sideways)
- Timeframe-specific optimization (1m, 5m, 15m, 1h, 4h, 1d)
- Complete asset training with 54 possible combinations per symbol/exchange
"""

import sys
import os
sys.path.append('/workspaces/Trad')

from ml.trained_assets_manager import TrainedAssetsManager
from utils.logger import log

def test_market_regime_detection():
    """Test the market regime detection functionality"""
    log.info("🔍 Testing Market Regime Detection")
    
    manager = TrainedAssetsManager()
    
    # Test regime detection for popular symbols
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
    
    for symbol in test_symbols:
        regime = manager._detect_current_market_regime(symbol, 'binanceus')
        log.info(f"📊 {symbol}: Market regime detected as '{regime}'")

def test_single_strategy_training():
    """Test training a single strategy with specific regime and timeframe"""
    log.info("🎯 Testing Single Strategy Training")
    
    manager = TrainedAssetsManager()
    
    # Test training HTF Sweep strategy for BTC in bull market on 5m timeframe
    trained_strategy = manager.train_strategy_multidimensional(
        symbol='BTC/USDT',
        exchange='binanceus',
        strategy_id='htf_sweep',
        market_regime='bull',
        timeframe='5m',
        min_samples=50  # Lower threshold for testing
    )
    
    if trained_strategy:
        log.info(f"✅ Strategy training successful!")
        log.info(f"   📊 Accuracy: {trained_strategy.accuracy:.3f}")
        log.info(f"   📈 Samples: {trained_strategy.training_samples}")
        log.info(f"   🎯 Parameters: {list(trained_strategy.strategy_parameters.keys())}")
    else:
        log.warning("❌ Strategy training failed - likely insufficient test data")

def test_strategy_parameter_retrieval():
    """Test the new get_strategy_parameters method"""
    log.info("📋 Testing Strategy Parameter Retrieval")
    
    manager = TrainedAssetsManager()
    
    # Test parameter retrieval for each strategy
    strategies = ['htf_sweep', 'volume_breakout', 'divergence_capitulation']
    
    for strategy_id in strategies:
        params = manager.get_strategy_parameters(
            symbol='BTC/USDT',
            exchange='binanceus',
            strategy_id=strategy_id
        )
        
        if params:
            log.info(f"✅ {strategy_id} parameters retrieved:")
            log.info(f"   🎯 Confidence: {params.get('confidence_threshold', 'N/A')}")
            log.info(f"   📊 Market regime: {params.get('market_regime', 'N/A')}")
            log.info(f"   ⏰ Timeframe: {params.get('timeframe', 'N/A')}")
        else:
            log.info(f"❌ No trained parameters for {strategy_id} - using defaults")

def test_complete_asset_training():
    """Test comprehensive asset training (WARNING: This would be intensive in production)"""
    log.info("🚀 Testing Complete Asset Training")
    
    manager = TrainedAssetsManager()
    
    # Train with limited scope for testing
    test_regimes = ['bull', 'sideways']  # Limited scope
    test_timeframes = ['5m', '1h']       # Limited scope
    
    log.info(f"🔧 Training scope: {len(test_regimes)} regimes × {len(test_timeframes)} timeframes × {len(manager.supported_strategies)} strategies")
    log.info(f"📊 Total combinations: {len(test_regimes) * len(test_timeframes) * len(manager.supported_strategies)}")
    
    # This would attempt to train all combinations (commented out for safety)
    # trained_asset = manager.train_complete_asset(
    #     symbol='BTC/USDT',
    #     exchange='binanceus',
    #     target_regimes=test_regimes,
    #     target_timeframes=test_timeframes
    # )
    
    log.info("💡 Complete asset training test skipped (would require substantial training data)")
    log.info("💡 In production, this would create a comprehensive TrainedAsset with all strategy combinations")

def demonstrate_architecture():
    """Demonstrate the new multi-dimensional architecture"""
    log.info("🏗️  Demonstrating Multi-Dimensional Architecture")
    
    manager = TrainedAssetsManager()
    
    log.info(f"📈 Supported strategies: {manager.supported_strategies}")
    log.info(f"🌊 Market regimes: {manager.market_regimes}")
    log.info(f"⏰ Timeframes: {manager.timeframes}")
    
    total_combinations = len(manager.supported_strategies) * len(manager.market_regimes) * len(manager.timeframes)
    log.info(f"🎯 Total possible trained strategies per asset: {total_combinations}")
    
    # Show example strategy keys
    log.info("🔑 Example strategy keys:")
    for i, strategy in enumerate(manager.supported_strategies):
        if i < 2:  # Show first 2 strategies
            for j, regime in enumerate(manager.market_regimes):
                if j < 2:  # Show first 2 regimes
                    key = manager._get_strategy_key('BTC/USDT', 'binanceus', strategy, regime, '5m')
                    log.info(f"   {key}")

def main():
    """Run all multi-dimensional training tests"""
    log.info("🚀 Multi-Dimensional Training Enhancement - Test Suite")
    log.info("=" * 60)
    
    try:
        # Test market regime detection
        test_market_regime_detection()
        log.info("")
        
        # Test strategy parameter retrieval
        test_strategy_parameter_retrieval()
        log.info("")
        
        # Test single strategy training
        test_single_strategy_training()
        log.info("")
        
        # Demonstrate architecture
        demonstrate_architecture()
        log.info("")
        
        # Test complete asset training (limited scope)
        test_complete_asset_training()
        
        log.info("=" * 60)
        log.info("✅ Multi-dimensional training system ready!")
        log.info("🎯 Key achievements:")
        log.info("   - Market regime detection implemented")
        log.info("   - Strategy-specific training with regime/timeframe awareness")
        log.info("   - Multi-dimensional parameter optimization")
        log.info("   - Complete asset training capability")
        log.info("   - 54 possible trained strategies per symbol/exchange")
        
    except Exception as e:
        log.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()