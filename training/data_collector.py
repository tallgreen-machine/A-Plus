"""
DataCollector - Database-Only OHLCV Data Fetching for Training

Fetches market data for training from database ONLY:
1. Query database (market_data table)
2. Calculate technical indicators (ATR, SMA)
3. Apply data quality filtering

NEVER makes exchange API calls during training.
Use data backfill scripts to populate database before training.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
import asyncpg

log = logging.getLogger(__name__)


class DataCollector:
    """
    Fetches OHLCV data for strategy training from DATABASE ONLY.
    
    Database-only approach:
    1. Query market_data table
    2. Fail fast if data missing
    3. Never make exchange API calls
    
    Example:
        collector = DataCollector()
        df = await collector.fetch_ohlcv(
            symbol='BTC/USDT',
            exchange='binance',
            timeframe='5m',
            lookback_candles=1000
        )
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize DataCollector.
        
        Args:
            db_url: PostgreSQL connection URL
                   Default: Loaded from environment/config
        """
        self.db_url = db_url or self._get_db_url()
        log.info("DataCollector initialized (DATABASE-ONLY mode for training)")
    
    def _get_db_url(self) -> str:
        """Get database URL from environment variables or config."""
        import os
        from configparser import ConfigParser
        
        # Try DATABASE_URL first (full connection string)
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        # Try DB_* environment variables (trad.env format)
        db_host = os.getenv('DB_HOST')
        if db_host:
            db_user = os.getenv('DB_USER', 'traduser')
            db_password = os.getenv('DB_PASSWORD', '')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'trad')
            return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
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
                f"{db_config.get('database', 'trad')}"
            )
        
        # Default (production values)
        return "postgresql://traduser:TRAD123!@localhost:5432/trad"
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        lookback_candles: int,  # Changed from lookback_days to lookback_candles
        lookback_days: Optional[int] = None,  # Kept for backward compatibility
        end_date: Optional[datetime] = None,
        data_filter_config: Optional[Dict] = None  # NEW: Data quality filtering config
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data (database-first, API fallback) with optional quality filtering.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            exchange: Exchange name (e.g., 'binance')
            timeframe: Candlestick interval (e.g., '5m', '1h', '1d')
            lookback_candles: Number of candles of historical data (preferred)
            lookback_days: Days of historical data (deprecated, for backward compatibility)
            end_date: End date (default: now)
            data_filter_config: Data quality filtering settings (optional):
                {
                    'enable_filtering': True/False,
                    'min_volume_threshold': 0.1,
                    'min_price_movement_pct': 0.01,
                    'filter_flat_candles': True,
                    'preserve_high_volume_single_price': True
                }
        
        Returns:
            DataFrame with columns:
                - timestamp (int): Unix timestamp ms
                - open, high, low, close, volume (float)
                - atr (float): Average True Range
                - sma_20, sma_50 (float): Simple Moving Averages
        
        Raises:
            ValueError: If no data available (database + API)
        """
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Calculate start_date from candles
        # Timeframe to minutes mapping
        timeframe_minutes = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240,
            '1d': 1440, '1w': 10080
        }
        
        minutes_per_candle = timeframe_minutes.get(timeframe)
        if minutes_per_candle is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        # Calculate lookback period in days
        total_minutes = lookback_candles * minutes_per_candle
        lookback_days_calculated = int(total_minutes / 1440) + 1  # Add 1 day buffer
        
        start_date = end_date - timedelta(days=lookback_days_calculated)
        
        log.info(
            f"Fetching {symbol} on {exchange} {timeframe} "
            f"({lookback_candles} candles ≈ {lookback_days_calculated} days, "
            f"{start_date.date()} to {end_date.date()})"
        )
        
        # Step 1: Try database (fast)
        df = await self._fetch_from_database(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Step 2: TRAINING MODE - Database only, no API fallback
        # Training should NEVER make live exchange API calls
        if df.empty or len(df) < 100:
            raise ValueError(
                f"Insufficient data in database for training: {symbol} on {exchange} {timeframe} "
                f"(found {len(df)} candles, need at least 100). "
                f"Please run data backfill before training: "
                f"python data/historical_data_backfill.py --symbol {symbol} --exchange {exchange} --timeframe {timeframe}"
            )
        
        log.info(f"✅ Database: {len(df)} candles loaded (50ms)")
        
        # Validate data
        if df.empty:
            raise ValueError(
                f"No data available for {symbol} on {exchange} {timeframe}"
            )
        
        # Step 3: Limit to exact candle count requested (take most recent)
        if len(df) > lookback_candles:
            df = df.tail(lookback_candles).reset_index(drop=True)
            log.info(f"Limited to {lookback_candles} most recent candles")
        
        # Step 3.5: Apply data quality filtering (if enabled)
        if data_filter_config and data_filter_config.get('enable_filtering', False):
            log.info("🧹 Applying data quality filtering...")
            from training.data_cleaner import DataCleaner
            
            cleaner = DataCleaner(config=data_filter_config)
            df_before = df.copy()
            df, filter_stats = cleaner.clean(df)
            
            # Log filtering results
            log.info(
                f"✅ Filtered: {filter_stats['original_count']} → {filter_stats['filtered_count']} candles "
                f"({filter_stats['removed_count']} removed, {filter_stats['removed_pct']:.1f}%)"
            )
            log.info(f"   Data quality score: {filter_stats['data_quality_score']:.1f}%")
            
            # Check if we have enough data remaining
            if len(df) < 100:
                log.warning(
                    f"⚠️ Filtering removed too many candles! "
                    f"Only {len(df)} remaining (need ≥100). "
                    f"Consider relaxing filter thresholds or using longer lookback."
                )
                # Don't fail - use the filtered data we have
        
        # Step 4: Calculate indicators
        df = self._calculate_indicators(df)
        
        log.info(
            f"✅ Data ready: {len(df)} candles with indicators "
            f"({df['timestamp'].min()} to {df['timestamp'].max()})"
        )
        
        return df
    
    async def _fetch_from_database(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetch from market_data table.
        
        Schema:
            market_data (
                id BIGSERIAL PRIMARY KEY,
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                timeframe VARCHAR(10) NOT NULL,
                timestamp BIGINT NOT NULL,  -- Unix ms
                open NUMERIC(20,8) NOT NULL,
                high NUMERIC(20,8) NOT NULL,
                low NUMERIC(20,8) NOT NULL,
                close NUMERIC(20,8) NOT NULL,
                volume NUMERIC(20,8) NOT NULL,
                quote_volume NUMERIC(20,8),
                trade_count INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        
        Data coverage: 6 timeframes (1m, 5m, 15m, 1h, 4h, 1d), 1000 candles per symbol/timeframe
        """
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # TRAINING MODE: Fetch most recent N candles, regardless of date
        # Don't filter by start_date/end_date as data may not be real-time
        query = """
            SELECT 
                timestamp,
                open::FLOAT,
                high::FLOAT,
                low::FLOAT,
                close::FLOAT,
                volume::FLOAT
            FROM market_data
            WHERE 
                symbol = $1
                AND exchange = $2
                AND timeframe = $3
            ORDER BY timestamp DESC
            LIMIT $4
        """
        
        # Calculate how many candles to fetch based on lookback period
        # Add 20% buffer to account for potential data quality filtering
        minutes_per_candle = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240,
            '1d': 1440, '1w': 10080
        }.get(timeframe, 5)
        
        total_minutes = (end_date - start_date).total_seconds() / 60
        estimated_candles = int(total_minutes / minutes_per_candle * 1.2)  # 20% buffer
        
        try:
            conn = await asyncpg.connect(self.db_url)
            rows = await conn.fetch(
                query,
                symbol,
                exchange.lower(),
                timeframe,
                estimated_candles
            )
            await conn.close()
            
            if not rows:
                log.debug(f"Database: No data found for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(
                rows,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Reverse order since we fetched DESC (most recent first)
            df = df.sort_values('timestamp', ascending=True).reset_index(drop=True)
            
            log.debug(f"Database: {len(df)} candles retrieved")
            return df
            
        except Exception as e:
            log.error(f"Database fetch failed: {e}")
            return pd.DataFrame()
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators.
        
        Indicators:
        - ATR (14): Average True Range
        - SMA (20, 50): Simple Moving Averages
        
        Returns:
            DataFrame with added columns: atr, sma_20, sma_50
        """
        df = df.copy()
        
        # ATR (14-period)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()
        df.drop(columns=['tr'], inplace=True)
        
        # Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Fill NaN values (first rows won't have enough history)
        df['atr'].fillna(method='bfill', inplace=True)
        df['sma_20'].fillna(method='bfill', inplace=True)
        df['sma_50'].fillna(method='bfill', inplace=True)
        
        return df
    
    def fetch_ohlcv_sync(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        lookback_candles: int,
        lookback_days: Optional[int] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Synchronous wrapper for fetch_ohlcv.
        
        Useful for non-async contexts (Jupyter notebooks, scripts).
        """
        import asyncio
        
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - use create_task
            raise RuntimeError(
                "Already in async context. Use await fetch_ohlcv() instead."
            )
        
        return loop.run_until_complete(
            self.fetch_ohlcv(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                lookback_candles=lookback_candles,
                lookback_days=lookback_days,
                end_date=end_date
            )
        )


# Convenience function for quick usage
async def fetch_training_data(
    symbol: str,
    exchange: str = 'binance',
    timeframe: str = '5m',
    lookback_candles: int = 10000,
    lookback_days: Optional[int] = None
) -> pd.DataFrame:
    """
    Quick helper to fetch training data.
    
    Example:
        df = await fetch_training_data('BTC/USDT', lookback_candles=10000)
        df = await fetch_training_data('BTC/USDT', lookback_days=90)  # Legacy
    """
    collector = DataCollector()
    return await collector.fetch_ohlcv(
        symbol=symbol,
        exchange=exchange,
        timeframe=timeframe,
        lookback_candles=lookback_candles,
        lookback_days=lookback_days
    )
