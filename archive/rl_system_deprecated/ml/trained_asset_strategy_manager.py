#!/usr/bin/env python3
"""
Trained Asset Strategy Manager
Manages ML-enhanced strategies using per-token-exchange trained models
"""

import importlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd

from ml.trained_assets_manager import trained_assets_manager
from utils.logger import log as logger
from core.event_system import SignalEvent


class TrainedAssetStrategyManager:
    """
    Manages strategies that use trained ML models per token-exchange combination
    
    Key Features:
    - Auto-selects best exchange for each symbol based on ML model availability
    - Falls back to traditional strategies if no trained assets available
    - Dynamically adapts to new token-exchange combinations
    """
    
    def __init__(self):
        self.assets_manager = trained_assets_manager
        self.active_strategies = {}
        self.strategy_configs = {}
        self.exchange_preferences = {}
        
        # Initialize strategy configurations
        self._initialize_strategy_configs()
        
        # Discover optimal exchange-symbol combinations
        self._discover_optimal_combinations()
        
        logger.info(f"🎯 Trained Asset Strategy Manager initialized")
        logger.info(f"   🧠 Available trained assets: {len(self.assets_manager.trained_assets)}")
        logger.info(f"   🔗 Optimal combinations: {len(self.exchange_preferences)}")
    
    def _initialize_strategy_configs(self):
        """Initialize available strategy configurations"""
        self.strategy_configs = {
            'trained_asset_divergence_capitulation': {
                'module': 'strategies.trained_asset_divergence_capitulation',
                'class': 'TrainedAssetDivergenceCapitulation',
                'required_patterns': ['divergence_strength'],
                'recommended_patterns': ['liquidity_sweep', 'fair_value_gap']
            },
            # Future trained asset strategies can be added here
        }
    
    def _discover_optimal_combinations(self):
        """Discover optimal exchange-symbol combinations based on trained asset availability"""
        
        # Get all available combinations from trained assets
        for asset_key, asset in self.assets_manager.trained_assets.items():
            symbol = asset.symbol
            exchange = asset.exchange
            
            if symbol not in self.exchange_preferences:
                self.exchange_preferences[symbol] = {
                    'primary': None,
                    'alternatives': [],
                    'asset_scores': {}
                }
            
            # Calculate asset score based on accuracy and training samples
            asset_score = asset.accuracy * (1 + min(1.0, asset.training_samples / 1000))
            
            if exchange not in self.exchange_preferences[symbol]['asset_scores']:
                self.exchange_preferences[symbol]['asset_scores'][exchange] = []
            
            self.exchange_preferences[symbol]['asset_scores'][exchange].append(asset_score)
        
        # Determine primary exchange for each symbol
        for symbol, prefs in self.exchange_preferences.items():
            exchange_avg_scores = {}
            
            for exchange, scores in prefs['asset_scores'].items():
                exchange_avg_scores[exchange] = sum(scores) / len(scores)
            
            # Sort by average score
            sorted_exchanges = sorted(exchange_avg_scores.items(), key=lambda x: x[1], reverse=True)
            
            if sorted_exchanges:
                prefs['primary'] = sorted_exchanges[0][0]
                prefs['alternatives'] = [ex for ex, _ in sorted_exchanges[1:]]
        
        logger.info(f"📊 Optimal exchange preferences discovered:")
        for symbol, prefs in self.exchange_preferences.items():
            primary = prefs['primary']
            if primary:
                score = prefs['asset_scores'][primary]
                avg_score = sum(score) / len(score)
                logger.info(f"   {symbol}: {primary} (score: {avg_score:.3f}, {len(score)} assets)")
    
    def get_optimal_exchange(self, symbol: str) -> Optional[str]:
        """Get the optimal exchange for a symbol based on trained asset performance"""
        if symbol in self.exchange_preferences:
            return self.exchange_preferences[symbol]['primary']
        
        # Fallback to most common exchange in available combinations
        exchanges = [combo[1] for combo in self.assets_manager.available_combinations if combo[0] == symbol]
        if exchanges:
            return max(set(exchanges), key=exchanges.count)
        
        return None
    
    def get_alternative_exchanges(self, symbol: str) -> List[str]:
        """Get alternative exchanges for a symbol"""
        if symbol in self.exchange_preferences:
            return self.exchange_preferences[symbol]['alternatives']
        return []
    
    def activate_strategies_for_symbols(self, symbols: List[str], 
                                     strategy_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Activate trained asset strategies for given symbols"""
        
        if strategy_types is None:
            strategy_types = list(self.strategy_configs.keys())
        
        activation_results = {
            'activated': {},
            'failed': {},
            'fallbacks': {}
        }
        
        for symbol in symbols:
            optimal_exchange = self.get_optimal_exchange(symbol)
            
            if not optimal_exchange:
                logger.warning(f"⚠️ No optimal exchange found for {symbol}")
                activation_results['failed'][symbol] = "No exchange available"
                continue
            
            symbol_strategies = {}
            
            for strategy_type in strategy_types:
                config = self.strategy_configs[strategy_type]
                
                # Check if required trained assets are available
                assets_available = self._check_required_assets(symbol, optimal_exchange, config)
                
                if assets_available:
                    try:
                        # Create strategy instance
                        strategy_instance = self._create_strategy_instance(
                            strategy_type, symbol, optimal_exchange
                        )
                        
                        if strategy_instance:
                            strategy_key = f"{strategy_type}_{symbol}_{optimal_exchange}"
                            self.active_strategies[strategy_key] = {
                                'instance': strategy_instance,
                                'symbol': symbol,
                                'exchange': optimal_exchange,
                                'strategy_type': strategy_type,
                                'created': datetime.now().isoformat()
                            }
                            symbol_strategies[strategy_type] = optimal_exchange
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to activate {strategy_type} for {symbol}/{optimal_exchange}: {e}")
                        activation_results['failed'][f"{symbol}_{strategy_type}"] = str(e)
                else:
                    logger.warning(f"⚠️ Required assets not available for {strategy_type} on {symbol}/{optimal_exchange}")
                    activation_results['failed'][f"{symbol}_{strategy_type}"] = "Missing required assets"
            
            if symbol_strategies:
                activation_results['activated'][symbol] = symbol_strategies
                logger.info(f"✅ Activated strategies for {symbol}: {symbol_strategies}")
            
        return activation_results
    
    def _check_required_assets(self, symbol: str, exchange: str, config: Dict[str, Any]) -> bool:
        """Check if required trained assets are available for a strategy"""
        required_patterns = config.get('required_patterns', [])
        
        for pattern in required_patterns:
            asset_key = self.assets_manager._get_asset_key(symbol, exchange, pattern)
            if asset_key not in self.assets_manager.trained_assets:
                return False
        
        return True
    
    def _create_strategy_instance(self, strategy_type: str, symbol: str, exchange: str):
        """Create a strategy instance"""
        try:
            config = self.strategy_configs[strategy_type]
            
            module = importlib.import_module(config['module'])
            strategy_class = getattr(module, config['class'])
            
            # Create instance with exchange parameter
            return strategy_class(symbol, {}, exchange=exchange)
            
        except Exception as e:
            logger.error(f"Error creating strategy instance {strategy_type}: {e}")
            return None
    
    def check_signals_for_all_active(self) -> List[SignalEvent]:
        """Check for signals from all active strategies"""
        signals = []
        
        for strategy_key, strategy_info in self.active_strategies.items():
            try:
                strategy_instance = strategy_info['instance']
                signal = strategy_instance.check_signal()
                
                if signal:
                    # Add strategy manager metadata
                    if not hasattr(signal, 'metadata'):
                        signal.metadata = {}
                    
                    signal.metadata.update({
                        'strategy_manager': 'TrainedAssetStrategyManager',
                        'exchange': strategy_info['exchange'],
                        'strategy_key': strategy_key,
                        'trained_asset_enhanced': True,
                        'check_timestamp': datetime.now().isoformat()
                    })
                    
                    signals.append(signal)
                    logger.info(f"📡 Signal generated by {strategy_key}: {signal.signal_type} {signal.symbol}")
                    
            except Exception as e:
                logger.error(f"❌ Error checking signal for {strategy_key}: {e}")
        
        return signals
    
    def check_signals_for_symbol(self, symbol: str) -> List[SignalEvent]:
        """Check for signals from strategies for a specific symbol"""
        signals = []
        
        for strategy_key, strategy_info in self.active_strategies.items():
            if strategy_info['symbol'] == symbol:
                try:
                    strategy_instance = strategy_info['instance']
                    signal = strategy_instance.check_signal()
                    
                    if signal:
                        if not hasattr(signal, 'metadata'):
                            signal.metadata = {}
                        
                        signal.metadata.update({
                            'strategy_manager': 'TrainedAssetStrategyManager',
                            'exchange': strategy_info['exchange'],
                            'strategy_key': strategy_key,
                            'trained_asset_enhanced': True,
                            'check_timestamp': datetime.now().isoformat()
                        })
                        
                        signals.append(signal)
                        logger.info(f"📡 Signal for {symbol}: {signal.signal_type} by {strategy_key}")
                        
                except Exception as e:
                    logger.error(f"❌ Error checking signal for {strategy_key}: {e}")
        
        return signals
    
    def train_assets_for_active_strategies(self, force_retrain: bool = False):
        """Train or update ML assets for all active strategies"""
        logger.info(f"🚀 Training assets for active strategies...")
        
        symbols_to_train = set()
        exchanges_to_train = set()
        
        for strategy_info in self.active_strategies.values():
            symbols_to_train.add(strategy_info['symbol'])
            exchanges_to_train.add(strategy_info['exchange'])
        
        logger.info(f"   📊 Symbols: {sorted(symbols_to_train)}")
        logger.info(f"   🏢 Exchanges: {sorted(exchanges_to_train)}")
        
        trained_count = 0
        
        for symbol in symbols_to_train:
            for exchange in exchanges_to_train:
                # Check if this combination exists in our data
                if (symbol, exchange) in self.assets_manager.available_combinations:
                    for pattern_type in self.assets_manager.pattern_types:
                        asset = self.assets_manager.train_asset(
                            symbol, exchange, pattern_type, min_samples=200
                        )
                        if asset:
                            trained_count += 1
        
        logger.info(f"✅ Training completed: {trained_count} assets trained")
        
        # Refresh optimal combinations after training
        self._discover_optimal_combinations()
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all active strategies"""
        summary = {
            'total_active_strategies': len(self.active_strategies),
            'symbols': set(),
            'exchanges': set(),
            'strategy_types': set(),
            'asset_coverage': {},
            'exchange_distribution': {}
        }
        
        for strategy_info in self.active_strategies.values():
            summary['symbols'].add(strategy_info['symbol'])
            summary['exchanges'].add(strategy_info['exchange'])
            summary['strategy_types'].add(strategy_info['strategy_type'])
            
            # Exchange distribution
            exchange = strategy_info['exchange']
            if exchange not in summary['exchange_distribution']:
                summary['exchange_distribution'][exchange] = 0
            summary['exchange_distribution'][exchange] += 1
        
        # Convert sets to sorted lists
        summary['symbols'] = sorted(list(summary['symbols']))
        summary['exchanges'] = sorted(list(summary['exchanges']))
        summary['strategy_types'] = sorted(list(summary['strategy_types']))
        
        # Asset coverage
        for symbol in summary['symbols']:
            exchange = self.get_optimal_exchange(symbol)
            if exchange:
                coverage = 0
                for pattern in self.assets_manager.pattern_types:
                    asset_key = self.assets_manager._get_asset_key(symbol, exchange, pattern)
                    if asset_key in self.assets_manager.trained_assets:
                        coverage += 1
                
                summary['asset_coverage'][f"{exchange}/{symbol}"] = {
                    'coverage': coverage,
                    'total_patterns': len(self.assets_manager.pattern_types),
                    'coverage_pct': coverage / len(self.assets_manager.pattern_types) * 100
                }
        
        return summary


# Global instance
trained_asset_strategy_manager = TrainedAssetStrategyManager()