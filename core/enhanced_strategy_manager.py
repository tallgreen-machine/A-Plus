#!/usr/bin/env python3
"""
Enhanced Strategy Manager - Orchestrates ML-enhanced and traditional strategies
Provides intelligent strategy selection based on trained assets and market conditions
"""

import sys
import os
sys.path.append('/workspaces/Trad')
sys.path.append('/srv/trad')

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Import traditional strategies
from strategies.divergence_capitulation import DivergenceCapitulation
from strategies.htf_sweep import HTFSweep
from strategies.volume_breakout import VolumeBreakout

# Import enhanced strategies
from strategies.enhanced_strategies import (
    EnhancedDivergenceCapitulation, 
    EnhancedHTFSweep, 
    EnhancedVolumeBreakout,
    EnhancedStrategyFactory
)

# Import ML components
from ml.pattern_ml_engine import PatternMLEngine
from ml.enhanced_pattern_library import EnhancedPatternFactory

from core.event_system import SignalEvent
from shared.db import get_db_conn
from utils.logger import log as logger

@dataclass
class StrategyResult:
    """Result from strategy execution"""
    strategy_name: str
    signal: Optional[SignalEvent]
    confidence: float
    enhancement_type: str  # 'TRADITIONAL', 'ML_ENHANCED'
    execution_time: float
    metadata: Dict[str, Any]

class EnhancedStrategyManager:
    """
    Manages both traditional and ML-enhanced strategies
    Intelligently selects best strategy based on trained asset availability
    """
    
    def __init__(self):
        self.db_conn = get_db_conn()
        self.ml_engine = PatternMLEngine()
        self.available_strategies = self._initialize_strategies()
        
    def _initialize_strategies(self) -> Dict[str, type]:
        """Initialize available strategy classes"""
        return {
            # Traditional strategies
            'divergence_capitulation': DivergenceCapitulation,
            'htf_sweep': HTFSweep,
            'volume_breakout': VolumeBreakout,
            
            # Enhanced strategies  
            'enhanced_divergence_capitulation': EnhancedDivergenceCapitulation,
            'enhanced_htf_sweep': EnhancedHTFSweep,
            'enhanced_volume_breakout': EnhancedVolumeBreakout
        }
    
    def get_available_assets(self) -> List[Tuple[str, str]]:
        """Get all available symbol-exchange combinations"""
        return self.ml_engine.get_available_assets()
    
    def load_asset_data(self, symbol: str, exchange: str, 
                       timeframes: List[str] = ['1h', '4h', '1d']) -> Dict[str, pd.DataFrame]:
        """
        Load market data for a specific asset across multiple timeframes
        """
        data = {}
        
        for timeframe in timeframes:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data_enhanced
                    WHERE symbol = %s AND exchange = %s AND timeframe = %s
                    ORDER BY timestamp DESC
                    LIMIT 200
                """, (symbol, exchange, timeframe))
                
                rows = cur.fetchall()
                
                if rows:
                    df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    # Sort by timestamp ascending for strategy logic
                    df = df.sort_values('timestamp', ascending=True).reset_index(drop=True)
                    data[timeframe] = df
                else:
                    logger.warning(f"No data found for {symbol}/{exchange} on {timeframe}")
                    data[timeframe] = pd.DataFrame()
        
        return data
    
    def has_trained_model(self, symbol: str, exchange: str, timeframe: str = '5m') -> bool:
        """Check if we have a trained ML model for this asset"""
        key = (symbol, exchange, timeframe)
        return key in self.ml_engine.trained_assets or self.ml_engine._load_trained_asset(symbol, exchange, timeframe)
    
    def execute_strategy(self, strategy_name: str, symbol: str, exchange: str, 
                        data: Dict[str, pd.DataFrame]) -> StrategyResult:
        """
        Execute a specific strategy for an asset
        """
        start_time = datetime.now()
        
        try:
            # Determine if we should use enhanced version
            use_enhanced = False
            if strategy_name in ['divergence_capitulation', 'htf_sweep', 'volume_breakout']:
                if self.has_trained_model(symbol, exchange):
                    strategy_name = f"enhanced_{strategy_name}"
                    use_enhanced = True
            
            # Get strategy class
            strategy_class = self.available_strategies.get(strategy_name)
            if not strategy_class:
                raise ValueError(f"Unknown strategy: {strategy_name}")
            
            # Create strategy instance
            if use_enhanced or strategy_name.startswith('enhanced_'):
                strategy = strategy_class(symbol, data, exchange)
                enhancement_type = 'ML_ENHANCED'
            else:
                strategy = strategy_class(symbol, data)
                enhancement_type = 'TRADITIONAL'
            
            # Execute strategy
            signal = strategy.check_signal()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            confidence = signal.confidence if signal else 0.0
            
            result = StrategyResult(
                strategy_name=strategy_name,
                signal=signal,
                confidence=confidence,
                enhancement_type=enhancement_type,
                execution_time=execution_time,
                metadata={
                    'symbol': symbol,
                    'exchange': exchange,
                    'has_trained_model': self.has_trained_model(symbol, exchange),
                    'data_timeframes': list(data.keys())
                }
            )
            
            if signal:
                logger.info(f"✅ Strategy {strategy_name} generated signal for {symbol}/{exchange}: "
                           f"{signal.signal_type} confidence {confidence:.2f}")
            else:
                logger.debug(f"📊 Strategy {strategy_name} - no signal for {symbol}/{exchange}")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error executing strategy {strategy_name} for {symbol}/{exchange}: {e}")
            
            return StrategyResult(
                strategy_name=strategy_name,
                signal=None,
                confidence=0.0,
                enhancement_type='ERROR',
                execution_time=execution_time,
                metadata={'error': str(e)}
            )
    
    def run_all_strategies_for_asset(self, symbol: str, exchange: str) -> List[StrategyResult]:
        """
        Run all available strategies for a specific asset
        """
        logger.info(f"🎯 Running all strategies for {symbol}/{exchange}")
        
        # Load data for this asset
        data = self.load_asset_data(symbol, exchange)
        
        if not any(not df.empty for df in data.values()):
            logger.warning(f"No data available for {symbol}/{exchange}")
            return []
        
        # Base strategy names (enhanced versions will be auto-selected if trained models exist)
        base_strategies = ['divergence_capitulation', 'htf_sweep', 'volume_breakout']
        
        results = []
        for strategy_name in base_strategies:
            result = self.execute_strategy(strategy_name, symbol, exchange, data)
            results.append(result)
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def scan_market_opportunities(self) -> Dict[str, Any]:
        """
        Scan all available assets for trading opportunities
        Returns comprehensive market overview with best signals
        """
        logger.info("🔍 Scanning market for opportunities...")
        
        available_assets = self.get_available_assets()
        all_results = []
        
        enhanced_count = 0
        traditional_count = 0
        total_signals = 0
        
        for symbol, exchange in available_assets:
            try:
                asset_results = self.run_all_strategies_for_asset(symbol, exchange)
                all_results.extend(asset_results)
                
                for result in asset_results:
                    if result.enhancement_type == 'ML_ENHANCED':
                        enhanced_count += 1
                    elif result.enhancement_type == 'TRADITIONAL':
                        traditional_count += 1
                    
                    if result.signal:
                        total_signals += 1
                        
            except Exception as e:
                logger.error(f"Error scanning {symbol}/{exchange}: {e}")
        
        # Find best signals
        signals_found = [r for r in all_results if r.signal and r.confidence > 0.6]
        signals_found.sort(key=lambda x: x.confidence, reverse=True)
        
        # Get top 10 signals
        top_signals = signals_found[:10]
        
        summary = {
            'scan_timestamp': datetime.now().isoformat(),
            'total_assets_scanned': len(available_assets),
            'total_strategy_executions': len(all_results),
            'enhanced_strategies_used': enhanced_count,
            'traditional_strategies_used': traditional_count,
            'total_signals_generated': total_signals,
            'high_confidence_signals': len(signals_found),
            'top_signals': [
                {
                    'symbol': result.metadata['symbol'],
                    'exchange': result.metadata['exchange'],
                    'strategy': result.strategy_name,
                    'signal_type': result.signal.signal_type,
                    'confidence': result.confidence,
                    'price': result.signal.price,
                    'target': result.signal.price_target,
                    'stop_loss': result.signal.stop_loss,
                    'enhancement': result.enhancement_type
                }
                for result in top_signals
            ]
        }
        
        logger.info(f"🎯 Market scan complete: {total_signals} signals from {len(available_assets)} assets "
                   f"({enhanced_count} enhanced, {traditional_count} traditional)")
        
        return summary
    
    def train_all_models(self) -> Dict[str, Any]:
        """
        Train ML models for all available assets
        """
        logger.info("🤖 Training ML models for all assets...")
        
        # Train pattern recognition models
        trained_assets = self.ml_engine.train_all_assets()
        
        summary = {
            'training_timestamp': datetime.now().isoformat(),
            'models_trained': len(trained_assets),
            'asset_summary': self.ml_engine.get_asset_summary()
        }
        
        logger.info(f"🎯 Training complete: {len(trained_assets)} models trained")
        
        return summary
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status including trained models and available strategies
        """
        available_assets = self.get_available_assets()
        
        # Count trained models
        trained_models = 0
        for symbol, exchange in available_assets:
            if self.has_trained_model(symbol, exchange):
                trained_models += 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'available_assets': len(available_assets),
            'trained_models': trained_models,
            'training_coverage': f"{trained_models}/{len(available_assets)} ({trained_models/len(available_assets)*100:.1f}%)",
            'available_strategies': list(self.available_strategies.keys()),
            'enhanced_strategies': [k for k in self.available_strategies.keys() if k.startswith('enhanced_')],
            'traditional_strategies': [k for k in self.available_strategies.keys() if not k.startswith('enhanced_')],
            'ml_engine_status': 'active',
            'database_connection': 'active' if self.db_conn else 'inactive'
        }

if __name__ == "__main__":
    # Example usage
    manager = EnhancedStrategyManager()
    
    # Get system status
    status = manager.get_system_status()
    print(f"System Status: {status}")
    
    # Train models (if needed)
    print("\n🤖 Training ML models...")
    training_result = manager.train_all_models()
    print(f"Training Result: {training_result}")
    
    # Scan market
    print("\n🔍 Scanning market opportunities...")
    market_scan = manager.scan_market_opportunities()
    print(f"Market Scan: {market_scan}")