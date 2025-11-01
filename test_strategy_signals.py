#!/usr/bin/env python3
"""
Diagnostic script to test CAPITULATION_REVERSAL and FAILED_BREAKDOWN strategies
with real market data to identify why they're not generating signals.
"""

import sys
import os
import asyncio
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.strategies.capitulation_reversal import CapitulationReversalStrategy
from training.strategies.failed_breakdown import FailedBreakdownStrategy
from training.data_collector import DataCollector


async def test_capitulation_reversal():
    """Test CAPITULATION_REVERSAL strategy with real data."""
    print("=" * 80)
    print("TESTING CAPITULATION_REVERSAL STRATEGY")
    print("=" * 80)
    
    # Get database URL
    db_user = os.getenv('DB_USER', 'traduser')
    db_password = os.getenv('DB_PASSWORD', 'TRAD123!')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'trad')
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fetch data
    print("\n1. Fetching market data...")
    collector = DataCollector(db_url=db_url)
    data = await collector.fetch_ohlcv(
        symbol='BTC/USDT',
        exchange='binanceus',
        timeframe='5m',
        lookback_candles=20000
    )
    
    if data is None or len(data) == 0:
        print("❌ ERROR: No data fetched")
        return
    
    print(f"✅ Fetched {len(data)} candles")
    print(f"   Date range: {pd.to_datetime(data['timestamp'].min(), unit='ms')} to {pd.to_datetime(data['timestamp'].max(), unit='ms')}")
    print(f"   Columns: {data.columns.tolist()}")
    
    # Test with default parameters
    print("\n2. Testing with DEFAULT parameters...")
    params = {
        'volume_explosion_threshold': 5.0,
        'price_velocity_threshold': 0.03,
        'atr_explosion_threshold': 2.5,
        'exhaustion_wick_ratio': 3.0,
        'rsi_extreme_threshold': 15,
        'rsi_divergence_lookback': 20,
        'orderbook_imbalance_threshold': 0.6,
        'consecutive_panic_candles': 3,
        'recovery_volume_threshold': 2.5,
        'atr_multiplier_sl': 1.5,
        'risk_reward_ratio': 2.5,
        'max_holding_periods': 50,
        'lookback_periods': 100
    }
    
    print(f"   Parameters: {params}")
    
    try:
        strategy = CapitulationReversalStrategy(params)
        signals = strategy.generate_signals(data)
        
        print(f"\n✅ Signal generation completed")
        print(f"   Total signals: {len(signals)}")
        
        if len(signals) > 0:
            buy_signals = signals[signals['signal'] == 'BUY']
            sell_signals = signals[signals['signal'] == 'SELL']
            hold_signals = signals[signals['signal'] == 'HOLD']
            
            print(f"   BUY signals: {len(buy_signals)}")
            print(f"   SELL signals: {len(sell_signals)}")
            print(f"   HOLD signals: {len(hold_signals)}")
            
            if len(buy_signals) > 0:
                print(f"\n   Sample BUY signal:")
                print(f"   {buy_signals.iloc[0].to_dict()}")
            
            if len(sell_signals) > 0:
                print(f"\n   Sample SELL signal:")
                print(f"   {sell_signals.iloc[0].to_dict()}")
        else:
            print("   ⚠️  No signals generated (empty DataFrame)")
            
    except Exception as e:
        print(f"\n❌ ERROR during signal generation:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test with RELAXED parameters
    print("\n3. Testing with RELAXED parameters...")
    relaxed_params = {
        'volume_explosion_threshold': 2.0,  # Lower (easier to trigger)
        'price_velocity_threshold': 0.01,  # Lower (easier to trigger)
        'atr_explosion_threshold': 1.5,  # Lower (easier to trigger)
        'exhaustion_wick_ratio': 1.5,  # Lower (easier to trigger)
        'rsi_extreme_threshold': 25,  # Higher (easier to trigger)
        'rsi_divergence_lookback': 20,
        'orderbook_imbalance_threshold': 0.5,  # Lower (easier to trigger)
        'consecutive_panic_candles': 2,  # Lower (easier to trigger)
        'recovery_volume_threshold': 1.5,  # Lower (easier to trigger)
        'atr_multiplier_sl': 1.5,
        'risk_reward_ratio': 2.0,
        'max_holding_periods': 50,
        'lookback_periods': 50  # Lower (start looking sooner)
    }
    
    print(f"   Parameters: {relaxed_params}")
    
    try:
        strategy = CapitulationReversalStrategy(relaxed_params)
        signals = strategy.generate_signals(data)
        
        print(f"\n✅ Signal generation completed")
        print(f"   Total signals: {len(signals)}")
        
        if len(signals) > 0:
            buy_signals = signals[signals['signal'] == 'BUY']
            sell_signals = signals[signals['signal'] == 'SELL']
            
            print(f"   BUY signals: {len(buy_signals)}")
            print(f"   SELL signals: {len(sell_signals)}")
            
            if len(buy_signals) > 0:
                print(f"\n   First BUY signal timestamp: {pd.to_datetime(buy_signals.iloc[0]['timestamp'], unit='ms')}")
                
    except Exception as e:
        print(f"\n❌ ERROR during signal generation:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_failed_breakdown():
    """Test FAILED_BREAKDOWN strategy with real data."""
    print("\n" + "=" * 80)
    print("TESTING FAILED_BREAKDOWN STRATEGY")
    print("=" * 80)
    
    # Get database URL
    db_user = os.getenv('DB_USER', 'traduser')
    db_password = os.getenv('DB_PASSWORD', 'TRAD123!')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'trad')
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fetch data
    print("\n1. Fetching market data...")
    collector = DataCollector(db_url=db_url)
    data = await collector.fetch_ohlcv(
        symbol='BTC/USDT',
        exchange='binanceus',
        timeframe='5m',
        lookback_candles=20000
    )
    
    if data is None or len(data) == 0:
        print("❌ ERROR: No data fetched")
        return
    
    print(f"✅ Fetched {len(data)} candles")
    
    # Test with default parameters
    print("\n2. Testing with DEFAULT parameters...")
    params = {
        'range_lookback_periods': 100,
        'range_tightness_threshold': 0.05,
        'breakdown_depth': 0.01,
        'breakdown_volume_threshold': 0.5,
        'spring_max_duration': 10,
        'recovery_volume_threshold': 3.0,
        'recovery_speed': 5,
        'orderbook_absorption_threshold': 3.0,
        'orderbook_monitoring_depth': 20,
        'large_trade_multiplier': 5.0,
        'smart_money_imbalance': 1.5,
        'accumulation_score_minimum': 0.7,
        'atr_multiplier_sl': 1.2,
        'risk_reward_ratio': 2.0,
        'max_holding_periods': 50
    }
    
    print(f"   Parameters: {params}")
    
    try:
        strategy = FailedBreakdownStrategy(params)
        signals = strategy.generate_signals(data)
        
        print(f"\n✅ Signal generation completed")
        print(f"   Total signals: {len(signals)}")
        
        if len(signals) > 0:
            buy_signals = signals[signals['signal'] == 'BUY']
            sell_signals = signals[signals['signal'] == 'SELL']
            
            print(f"   BUY signals: {len(buy_signals)}")
            print(f"   SELL signals: {len(sell_signals)}")
            
            if len(buy_signals) > 0:
                print(f"\n   Sample BUY signal:")
                print(f"   {buy_signals.iloc[0].to_dict()}")
                
    except Exception as e:
        print(f"\n❌ ERROR during signal generation:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test with RELAXED parameters
    print("\n3. Testing with RELAXED parameters...")
    relaxed_params = {
        'range_lookback_periods': 50,  # Lower (find ranges faster)
        'range_tightness_threshold': 0.10,  # Higher (allow wider ranges)
        'breakdown_depth': 0.005,  # Lower (smaller breakdowns count)
        'breakdown_volume_threshold': 0.3,  # Lower (weaker volume acceptable)
        'spring_max_duration': 15,  # Higher (allow longer springs)
        'recovery_volume_threshold': 2.0,  # Lower (weaker recovery acceptable)
        'recovery_speed': 10,  # Higher (allow slower recovery)
        'orderbook_absorption_threshold': 2.0,  # Lower
        'orderbook_monitoring_depth': 20,
        'large_trade_multiplier': 3.0,  # Lower
        'smart_money_imbalance': 1.2,  # Lower
        'accumulation_score_minimum': 0.5,  # Lower (less strict)
        'atr_multiplier_sl': 1.2,
        'risk_reward_ratio': 2.0,
        'max_holding_periods': 50
    }
    
    print(f"   Parameters: {relaxed_params}")
    
    try:
        strategy = FailedBreakdownStrategy(relaxed_params)
        signals = strategy.generate_signals(data)
        
        print(f"\n✅ Signal generation completed")
        print(f"   Total signals: {len(signals)}")
        
        if len(signals) > 0:
            buy_signals = signals[signals['signal'] == 'BUY']
            sell_signals = signals[signals['signal'] == 'SELL']
            
            print(f"   BUY signals: {len(buy_signals)}")
            print(f"   SELL signals: {len(sell_signals)}")
            
            if len(buy_signals) > 0:
                print(f"\n   First BUY signal timestamp: {pd.to_datetime(buy_signals.iloc[0]['timestamp'], unit='ms')}")
                
    except Exception as e:
        print(f"\n❌ ERROR during signal generation:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all diagnostic tests."""
    print("\n🔍 STRATEGY SIGNAL GENERATION DIAGNOSTICS")
    print("=" * 80)
    
    # Load environment from trad.env
    env_file = '/etc/trad/trad.env'
    if os.path.exists(env_file):
        print(f"Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    
    await test_capitulation_reversal()
    await test_failed_breakdown()
    
    print("\n" + "=" * 80)
    print("✅ DIAGNOSTICS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())
