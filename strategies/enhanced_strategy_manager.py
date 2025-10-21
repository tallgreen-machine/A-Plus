#!/usr/bin/env python3
"""
Enhanced Strategy Manager
Manages both traditional and ML-enhanced trading strategies with intelligent selection
"""

import importlib
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from utils.logger import log as logger
from core.event_system import SignalEvent


class EnhancedStrategyManager:
    """
    Manages and coordinates traditional and ML-enhanced trading strategies
    """
    
    def __init__(self):
        self.traditional_strategies = {}
        self.enhanced_strategies = {}
        self.active_strategies = set()
        self.strategy_performance = {}
        self.ml_available = True
        
        # Initialize strategies
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize both traditional and enhanced strategy sets"""
        try:
            # Traditional strategies
            self._load_traditional_strategies()
            
            # Enhanced strategies (with ML)
            self._load_enhanced_strategies()
            
            logger.info(f"✅ Strategy Manager initialized:")
            logger.info(f"   📊 Traditional strategies: {len(self.traditional_strategies)}")
            logger.info(f"   🧠 Enhanced strategies: {len(self.enhanced_strategies)}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing strategies: {e}")
            self.ml_available = False
    
    def _load_traditional_strategies(self):
        """Load traditional strategy implementations"""
        traditional_configs = {
            'divergence_capitulation': {
                'module': 'strategies.divergence_capitulation',
                'class': 'DivergenceCapitulation'
            },
            'htf_sweep': {
                'module': 'strategies.htf_sweep',
                'class': 'HTFSweep'
            },
            'volume_breakout': {
                'module': 'strategies.volume_breakout',
                'class': 'VolumeBreakout'
            }
        }
        
        for strategy_name, config in traditional_configs.items():
            try:
                module = importlib.import_module(config['module'])
                strategy_class = getattr(module, config['class'])
                self.traditional_strategies[strategy_name] = {
                    'class': strategy_class,
                    'config': config
                }
                logger.info(f"✅ Loaded traditional strategy: {strategy_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to load traditional strategy {strategy_name}: {e}")
    
    def _load_enhanced_strategies(self):
        """Load ML-enhanced strategy implementations"""
        enhanced_configs = {
            'enhanced_divergence_capitulation': {
                'module': 'strategies.enhanced_divergence_capitulation',
                'class': 'EnhancedDivergenceCapitulation'
            },
            'enhanced_htf_sweep': {
                'module': 'strategies.enhanced_htf_sweep',
                'class': 'EnhancedHTFSweep'
            },
            'enhanced_volume_breakout': {
                'module': 'strategies.enhanced_volume_breakout',
                'class': 'EnhancedVolumeBreakout'
            }
        }
        
        for strategy_name, config in enhanced_configs.items():
            try:
                module = importlib.import_module(config['module'])
                strategy_class = getattr(module, config['class'])
                self.enhanced_strategies[strategy_name] = {
                    'class': strategy_class,
                    'config': config
                }
                logger.info(f"✅ Loaded enhanced strategy: {strategy_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to load enhanced strategy {strategy_name}: {e}")
                # If enhanced strategies fail, we can still use traditional ones
    
    def activate_strategies(self, strategy_names: List[str], prefer_enhanced: bool = True):
        """Activate specific strategies for trading"""
        self.active_strategies.clear()
        
        for name in strategy_names:
            # Try enhanced first if preferred and available
            if prefer_enhanced and self.ml_available:
                enhanced_name = f"enhanced_{name}" if not name.startswith('enhanced_') else name
                if enhanced_name in self.enhanced_strategies:
                    self.active_strategies.add(enhanced_name)
                    logger.info(f"🧠 Activated enhanced strategy: {enhanced_name}")
                    continue
            
            # Fall back to traditional strategy
            traditional_name = name.replace('enhanced_', '') if name.startswith('enhanced_') else name
            if traditional_name in self.traditional_strategies:
                self.active_strategies.add(traditional_name)
                logger.info(f"📊 Activated traditional strategy: {traditional_name}")
            else:
                logger.warning(f"⚠️ Strategy not found: {name}")
        
        logger.info(f"🎯 Total active strategies: {len(self.active_strategies)}")
    
    def check_signals(self, symbol: str, data: dict) -> List[SignalEvent]:
        """Check for signals from all active strategies"""
        signals = []
        
        for strategy_name in self.active_strategies:
            try:
                # Get strategy instance
                strategy_instance = self._get_strategy_instance(strategy_name, symbol, data)
                
                if strategy_instance:
                    # Check for signal
                    signal = strategy_instance.check_signal()
                    
                    if signal:
                        # Add strategy metadata
                        if not hasattr(signal, 'metadata'):
                            signal.metadata = {}
                        
                        signal.metadata.update({
                            'strategy_manager': 'EnhancedStrategyManager',
                            'strategy_type': 'enhanced' if strategy_name in self.enhanced_strategies else 'traditional',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        signals.append(signal)
                        logger.info(f"📡 Signal generated by {strategy_name}: {signal.signal_type} {symbol}")
                        
            except Exception as e:
                logger.error(f"❌ Error checking signal for {strategy_name} on {symbol}: {e}")
        
        return signals
    
    def _get_strategy_instance(self, strategy_name: str, symbol: str, data: dict):
        """Get strategy instance for signal checking"""
        try:
            # Check if it's an enhanced strategy
            if strategy_name in self.enhanced_strategies:
                strategy_class = self.enhanced_strategies[strategy_name]['class']
            elif strategy_name in self.traditional_strategies:
                strategy_class = self.traditional_strategies[strategy_name]['class']
            else:
                logger.error(f"Strategy not found: {strategy_name}")
                return None
            
            # Create instance
            return strategy_class(symbol, data)
            
        except Exception as e:
            logger.error(f"Error creating strategy instance {strategy_name}: {e}")
            return None
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get performance statistics for all strategies"""
        performance = {}
        
        for strategy_name in list(self.enhanced_strategies.keys()) + list(self.traditional_strategies.keys()):
            if strategy_name in self.strategy_performance:
                performance[strategy_name] = self.strategy_performance[strategy_name]
            else:
                performance[strategy_name] = {
                    'signals_generated': 0,
                    'successful_signals': 0,
                    'total_profit': 0.0,
                    'win_rate': 0.0,
                    'avg_confidence': 0.0
                }
        
        return performance
    
    def update_strategy_performance(self, strategy_id: str, profit: float, success: bool, confidence: float):
        """Update performance tracking for strategies"""
        if strategy_id not in self.strategy_performance:
            self.strategy_performance[strategy_id] = {
                'signals_generated': 0,
                'successful_signals': 0,
                'total_profit': 0.0,
                'win_rate': 0.0,
                'avg_confidence': 0.0,
                'confidences': []
            }
        
        perf = self.strategy_performance[strategy_id]
        perf['signals_generated'] += 1
        perf['total_profit'] += profit
        perf['confidences'].append(confidence)
        
        if success:
            perf['successful_signals'] += 1
        
        # Update calculated metrics
        perf['win_rate'] = perf['successful_signals'] / perf['signals_generated']
        perf['avg_confidence'] = sum(perf['confidences']) / len(perf['confidences'])
        
        # Keep only last 100 confidences for memory efficiency
        if len(perf['confidences']) > 100:
            perf['confidences'] = perf['confidences'][-100:]
    
    def get_strategy_recommendation(self, market_conditions: Dict[str, Any]) -> List[str]:
        """Recommend strategies based on current market conditions"""
        recommendations = []
        
        # Analyze market conditions
        volatility = market_conditions.get('volatility', 'medium')
        trend = market_conditions.get('trend', 'neutral')
        volume = market_conditions.get('volume', 'normal')
        
        # Strategy recommendations based on conditions
        if volatility == 'high':
            if self.ml_available:
                recommendations.extend(['enhanced_divergence_capitulation', 'enhanced_htf_sweep'])
            else:
                recommendations.extend(['divergence_capitulation', 'htf_sweep'])
        
        if volume == 'high' and trend in ['up', 'strong_up']:
            if self.ml_available:
                recommendations.append('enhanced_volume_breakout')
            else:
                recommendations.append('volume_breakout')
        
        if trend == 'sideways':
            if self.ml_available:
                recommendations.extend(['enhanced_htf_sweep', 'enhanced_divergence_capitulation'])
            else:
                recommendations.extend(['htf_sweep', 'divergence_capitulation'])
        
        # Default to all strategies if no specific conditions
        if not recommendations:
            if self.ml_available:
                recommendations = list(self.enhanced_strategies.keys())
            else:
                recommendations = list(self.traditional_strategies.keys())
        
        # Remove duplicates and return
        return list(set(recommendations))
    
    def get_active_strategies_info(self) -> Dict[str, Any]:
        """Get information about currently active strategies"""
        info = {}
        
        for strategy_name in self.active_strategies:
            strategy_type = 'enhanced' if strategy_name in self.enhanced_strategies else 'traditional'
            
            info[strategy_name] = {
                'type': strategy_type,
                'ml_enabled': strategy_type == 'enhanced',
                'performance': self.strategy_performance.get(strategy_name, {}),
                'active': True
            }
        
        return info
    
    def force_traditional_mode(self):
        """Force use of traditional strategies only (disable ML)"""
        logger.warning("🔄 Forcing traditional strategy mode (ML disabled)")
        self.ml_available = False
        
        # Convert active enhanced strategies to traditional
        new_active = set()
        for strategy_name in self.active_strategies:
            if strategy_name.startswith('enhanced_'):
                traditional_name = strategy_name.replace('enhanced_', '')
                if traditional_name in self.traditional_strategies:
                    new_active.add(traditional_name)
            else:
                new_active.add(strategy_name)
        
        self.active_strategies = new_active
        logger.info(f"✅ Converted to traditional strategies: {self.active_strategies}")
    
    def enable_ml_mode(self):
        """Re-enable ML enhanced strategies"""
        logger.info("🧠 Enabling ML enhanced strategy mode")
        self.ml_available = True
        
        # Convert active traditional strategies to enhanced if available
        new_active = set()
        for strategy_name in self.active_strategies:
            enhanced_name = f"enhanced_{strategy_name}"
            if enhanced_name in self.enhanced_strategies:
                new_active.add(enhanced_name)
            else:
                new_active.add(strategy_name)
        
        self.active_strategies = new_active
        logger.info(f"✅ Converted to enhanced strategies: {self.active_strategies}")


# Global instance
strategy_manager = EnhancedStrategyManager()