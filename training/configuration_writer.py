"""
ConfigurationWriter - V3 JSON Generation and Database Persistence

Creates V3 configuration JSON from training results and saves to database.

Responsibilities:
1. Generate V3 JSON template with all required fields
2. Assign lifecycle stage based on metrics (DISCOVERY/VALIDATION/MATURE/PAPER)
3. Calculate confidence scores
4. Insert into trained_configurations table
5. Set appropriate circuit breakers

Output stored in trained_configurations table for V2 UI consumption.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging
import asyncpg
import hashlib
import numpy as np

from .backtest_engine import BacktestResult
from .validator import ValidationResult

log = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj


class ConfigurationWriter:
    """
    Writes training results to database as V3 configurations.
    
    Example:
        writer = ConfigurationWriter()
        
        config_id = await writer.save_configuration(
            strategy='LIQUIDITY_SWEEP',
            symbol='BTC/USDT',
            exchange='binance',
            timeframe='5m',
            parameters={'pierce_depth': 0.002, ...},
            backtest_result=backtest_result,
            validation_result=validation_result,
            optimizer='bayesian'
        )
        
        print(f"Configuration saved: {config_id}")
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize ConfigurationWriter.
        
        Args:
            db_url: PostgreSQL connection URL (default: from config)
        """
        self.db_url = db_url or self._get_db_url()
        log.info("ConfigurationWriter initialized")
    
    def _get_db_url(self) -> str:
        """Get database URL from config."""
        import os
        from configparser import ConfigParser
        
        # Try environment variable first
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        # Fall back to config.ini
        config = ConfigParser()
        config.read('config.ini')
        
        if 'database' in config:
            db_config = config['database']
            return (
                f"postgresql://{db_config.get('user', 'traduser')}:"
                f"{db_config.get('password', '')}@"
                f"{db_config.get('host', 'localhost')}:"
                f"{db_config.get('port', '5432')}/"
                f"{db_config.get('database', 'traddb')}"
            )
        
        return "postgresql://traduser:tradpass@localhost:5432/traddb"
    
    async def save_configuration(
        self,
        strategy: str,
        symbol: str,
        exchange: str,
        timeframe: str,
        parameters: Dict[str, Any],
        backtest_result: BacktestResult,
        validation_result: Optional[ValidationResult] = None,
        optimizer: str = 'bayesian',
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save training result as V3 configuration to database.
        
        Args:
            strategy: Strategy name (e.g., 'LIQUIDITY_SWEEP')
            symbol: Trading pair (e.g., 'BTC/USDT')
            exchange: Exchange name (e.g., 'binance')
            timeframe: Timeframe (e.g., '5m')
            parameters: Strategy parameters dict
            backtest_result: BacktestResult from training
            validation_result: Optional ValidationResult from walk-forward
            optimizer: Optimizer used ('grid', 'random', 'bayesian')
            metadata: Optional additional metadata
        
        Returns:
            config_id: Generated configuration ID
        """
        log.info(f"Saving configuration: {strategy} {symbol} {exchange} {timeframe}")
        
        # Generate configuration ID
        config_id = self._generate_config_id(strategy, symbol, exchange, timeframe)
        
        # Determine lifecycle stage
        lifecycle_stage = self._determine_lifecycle_stage(
            backtest_result.metrics,
            validation_result
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            backtest_result.metrics,
            validation_result
        )
        
        # Build V3 JSON
        config_json = self._build_v3_json(
            config_id=config_id,
            strategy=strategy,
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            parameters=parameters,
            backtest_result=backtest_result,
            validation_result=validation_result,
            lifecycle_stage=lifecycle_stage,
            confidence_score=confidence_score,
            optimizer=optimizer,
            metadata=metadata
        )
        
        # Insert into database
        await self._insert_to_database(config_json, lifecycle_stage)
        
        log.info(
            f"✅ Configuration saved: {config_id} "
            f"({lifecycle_stage}, confidence={confidence_score:.2f})"
        )
        
        return config_id
    
    def _generate_config_id(
        self,
        strategy: str,
        symbol: str,
        exchange: str,
        timeframe: str
    ) -> str:
        """
        Generate unique configuration ID.
        
        Format: STRATEGY_V3_YYYYMMDD_HHMMSS_HASH
        Example: LIQUIDITY_SWEEP_V3_20251023_145632_a1b2c3
        """
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y%m%d_%H%M%S')
        
        # Create hash from strategy + symbol + exchange + timeframe + timestamp
        hash_input = f"{strategy}_{symbol}_{exchange}_{timeframe}_{timestamp.timestamp()}"
        hash_short = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        
        config_id = f"{strategy}_V3_{date_str}_{hash_short}"
        
        return config_id
    
    def _determine_lifecycle_stage(
        self,
        metrics: Dict[str, float],
        validation_result: Optional[ValidationResult]
    ) -> str:
        """
        Determine lifecycle stage based on metrics.
        
        Stages:
        - PAPER: Negative profit or failed validation
        - DISCOVERY: < 30 trades, untested
        - VALIDATION: 30-100 trades, passing validation
        - MATURE: > 100 trades, strong metrics, validated
        - DECAY: (not assigned during training)
        
        Returns:
            Lifecycle stage name
        """
        total_trades = metrics.get('total_trades', 0)
        net_profit = metrics.get('net_profit_pct', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        win_rate = metrics.get('gross_win_rate', 0)
        
        # PAPER: Failing configurations
        if net_profit < 0 or sharpe < 0.5:
            return 'PAPER'
        
        # Check validation if available
        if validation_result:
            if validation_result.overfitting_detected:
                return 'PAPER'
            
            if validation_result.stability_score < 0.5:
                return 'PAPER'
        
        # DISCOVERY: Small sample, unproven
        if total_trades < 30:
            return 'DISCOVERY'
        
        # MATURE: Large sample + strong metrics + validated
        if (total_trades >= 100 and 
            sharpe >= 1.5 and 
            win_rate >= 0.50 and
            validation_result is not None):
            return 'MATURE'
        
        # VALIDATION: Medium sample, validated
        if validation_result is not None:
            return 'VALIDATION'
        
        # Default: DISCOVERY
        return 'DISCOVERY'
    
    def _calculate_confidence_score(
        self,
        metrics: Dict[str, float],
        validation_result: Optional[ValidationResult]
    ) -> float:
        """
        Calculate confidence score (0-1) for configuration.
        
        Factors:
        - Sample size (more trades = higher confidence)
        - Sharpe ratio (risk-adjusted returns)
        - Win rate
        - Validation stability (if available)
        
        Returns:
            Confidence score 0.0 to 1.0
        """
        # Component 1: Sample size confidence (0-0.3)
        total_trades = metrics.get('total_trades', 0)
        sample_confidence = min(total_trades / 200, 1.0) * 0.3
        
        # Component 2: Sharpe confidence (0-0.3)
        sharpe = max(metrics.get('sharpe_ratio', 0), 0)
        sharpe_confidence = min(sharpe / 3.0, 1.0) * 0.3
        
        # Component 3: Win rate confidence (0-0.2)
        win_rate = metrics.get('gross_win_rate', 0)
        winrate_confidence = win_rate * 0.2
        
        # Component 4: Validation stability (0-0.2)
        if validation_result:
            validation_confidence = validation_result.stability_score * 0.2
        else:
            validation_confidence = 0.0
        
        confidence = (
            sample_confidence +
            sharpe_confidence +
            winrate_confidence +
            validation_confidence
        )
        
        return round(confidence, 4)
    
    def _build_v3_json(
        self,
        config_id: str,
        strategy: str,
        symbol: str,
        exchange: str,
        timeframe: str,
        parameters: Dict[str, Any],
        backtest_result: BacktestResult,
        validation_result: Optional[ValidationResult],
        lifecycle_stage: str,
        confidence_score: float,
        optimizer: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build V3 configuration JSON.
        
        Returns:
            Complete V3 JSON dict
        """
        timestamp = datetime.now(timezone.utc)
        
        # Base structure
        config = {
            "configId": config_id,
            "version": "3.0.0",
            "strategy": strategy,
            "createdAt": timestamp.isoformat(),
            
            "metadata": {
                "model_version": "3.0.0",
                "discovery_date": timestamp.isoformat(),
                "engine_hash": hashlib.md5(f"{optimizer}_{timestamp}".encode()).hexdigest()[:16],
                "runtime_env": "training_v2",
                "optimizer": optimizer,
                **(metadata or {})
            },
            
            "context": {
                "pair": symbol,
                "exchange": exchange,
                "timeframe": timeframe
            },
            
            "parameters": parameters,
            
            "performance": {
                "gross_WR": backtest_result.metrics.get('gross_win_rate', 0),
                "avg_win": backtest_result.metrics.get('avg_win_pct', 0),
                "avg_loss": backtest_result.metrics.get('avg_loss_pct', 0),
                "exchange_fees": 0.1,  # Default 0.1%
                "est_slippage": 0.05,  # Default 0.05%
                "actual_slippage": 0.05,
                "NET_PROFIT": backtest_result.metrics.get('net_profit_pct', 0),
                "sample_size": backtest_result.metrics.get('total_trades', 0)
            },
            
            "statistical_validation": {
                "sharpe_ratio": backtest_result.metrics.get('sharpe_ratio', 0),
                "calmar_ratio": backtest_result.metrics.get('calmar_ratio', 0),
                "sortino_ratio": backtest_result.metrics.get('sortino_ratio', 0),
                "p_value": 0.05,  # Placeholder (future: statistical testing)
                "z_score": 0.0,
                "monte_carlo_var": 0.0,
                "stability_score": validation_result.stability_score if validation_result else 0.0,
                "drawdown_duration": 0,
                "trade_clustering": 0.0,
                "rolling_30d_sharpe": backtest_result.metrics.get('sharpe_ratio', 0),
                "lifetime_sharpe_ratio": backtest_result.metrics.get('sharpe_ratio', 0)
            },
            
            "execution_metrics": {
                "fill_rate": 1.0,  # Assumed 100% for backtest
                "partial_fill_rate": 0.0,
                "time_to_fill_ms": 100,
                "slippage_vs_mid_bps": 5,
                "adverse_selection_score": 0.0,
                "post_trade_drift_1m": 0.0,
                "post_trade_drift_5m": 0.0,
                "rejection_rate": 0.0
            },
            
            "lifecycle": {
                "current_stage": lifecycle_stage,
                "max_allocation_pct": self._get_stage_allocation(lifecycle_stage),
                "confidence_score": confidence_score,
                "last_updated": timestamp.isoformat()
            },
            
            "circuit_breakers": self._get_default_circuit_breakers(lifecycle_stage),
            
            "validation": {}
        }
        
        # Add validation info if available
        if validation_result:
            config["validation"] = {
                "method": "walk_forward",
                "total_windows": validation_result.aggregate_metrics.get('total_windows', 0),
                "test_sharpe_ratio": validation_result.aggregate_metrics.get('test_sharpe_ratio', 0),
                "test_win_rate": validation_result.aggregate_metrics.get('test_win_rate', 0),
                "test_net_profit_pct": validation_result.aggregate_metrics.get('test_net_profit_pct', 0),
                "overfitting_detected": validation_result.overfitting_detected,
                "overfitting_reasons": validation_result.overfitting_reasons,
                "stability_score": validation_result.stability_score
            }
        
        return config
    
    def _get_stage_allocation(self, stage: str) -> float:
        """Get maximum allocation percentage for lifecycle stage."""
        allocations = {
            'PAPER': 0.0,
            'DISCOVERY': 2.0,
            'VALIDATION': 5.0,
            'MATURE': 10.0,
            'DECAY': 3.0
        }
        return allocations.get(stage, 2.0)
    
    def _get_default_circuit_breakers(self, stage: str) -> Dict[str, Any]:
        """Get default circuit breaker settings for lifecycle stage."""
        # More conservative for early stages
        if stage in ['PAPER', 'DISCOVERY']:
            return {
                "max_daily_loss_pct": 1.0,
                "max_position_size_pct": 2.0,
                "max_drawdown_pct": 5.0,
                "max_consecutive_losses": 3,
                "daily_trade_limit": 5,
                "cooldown_after_loss_minutes": 60,
                "min_sharpe_ratio": 1.0
            }
        elif stage == 'VALIDATION':
            return {
                "max_daily_loss_pct": 2.0,
                "max_position_size_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "max_consecutive_losses": 5,
                "daily_trade_limit": 10,
                "cooldown_after_loss_minutes": 30,
                "min_sharpe_ratio": 0.8
            }
        else:  # MATURE
            return {
                "max_daily_loss_pct": 3.0,
                "max_position_size_pct": 10.0,
                "max_drawdown_pct": 15.0,
                "max_consecutive_losses": 7,
                "daily_trade_limit": 20,
                "cooldown_after_loss_minutes": 15,
                "min_sharpe_ratio": 0.5
            }
    
    async def _insert_to_database(
        self,
        config_json: Dict[str, Any],
        lifecycle_stage: str
    ):
        """
        Insert configuration to trained_configurations table.
        
        Maps V2 training results to comprehensive production schema.
        Schema has 70+ columns including lifecycle, regime, execution metrics, etc.
        """
        try:
            db_url = self.get_db_url()
            conn = await asyncpg.connect(db_url)
            
            # Extract and convert values
            perf = config_json['performance']
            stats = config_json['statistical_validation']
            params = config_json['parameters']
            
            # Map to existing schema columns
            query = """
                INSERT INTO trained_configurations (
                    strategy_name,
                    exchange,
                    pair,
                    timeframe,
                    regime,
                    status,
                    is_active,
                    parameters_json,
                    gross_win_rate,
                    avg_win,
                    avg_loss,
                    net_profit,
                    sample_size,
                    sharpe_ratio,
                    calmar_ratio,
                    sortino_ratio,
                    created_at,
                    updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                )
                RETURNING id
            """
            
            # Use 'sideways' as default regime for now (regime detection not yet implemented)
            regime = config_json.get('context', {}).get('regime', 'sideways')
            
            result = await conn.fetchval(
                query,
                config_json['strategy'],  # strategy_name
                config_json['context']['exchange'],  # exchange
                config_json['context']['pair'],  # pair
                config_json['context']['timeframe'],  # timeframe
                regime,  # regime
                lifecycle_stage,  # status (maps to lifecycle_stage)
                False,  # is_active (not yet activated)
                json.dumps(convert_numpy_types(params)),  # parameters_json
                float(perf.get('gross_WR', 0)) / 100.0,  # gross_win_rate (convert % to decimal)
                float(perf.get('avg_win_pct', 0)),  # avg_win
                float(perf.get('avg_loss_pct', 0)),  # avg_loss
                float(perf.get('NET_PROFIT', 0)),  # net_profit
                int(perf.get('sample_size', 0)),  # sample_size
                float(stats.get('sharpe_ratio', 0)),  # sharpe_ratio
                float(stats.get('calmar_ratio', 0)),  # calmar_ratio
                float(stats.get('sortino_ratio', 0)),  # sortino_ratio
                datetime.now(timezone.utc),  # created_at
                datetime.now(timezone.utc)  # updated_at
            )
            
            await conn.close()
            
            log.debug(f"Configuration inserted to database: ID={result}, {config_json['configId']}")
            
        except Exception as e:
            log.error(f"Database insert failed: {e}")
            raise
    
    def save_configuration_sync(self, **kwargs) -> str:
        """
        Synchronous wrapper for save_configuration.
        
        Useful for non-async contexts.
        """
        import asyncio
        
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError(
                "Already in async context. Use await save_configuration() instead."
            )
        
        return loop.run_until_complete(self.save_configuration(**kwargs))
