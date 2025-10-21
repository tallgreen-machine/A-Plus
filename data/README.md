# Data Collection and Exchange Integration

This directory contains all data collection, exchange integration, and market data processing components.

## Files

- **`enhanced_data_collector.py`** - Multi-timeframe data collector with real exchange integration
- **`real_exchange_data_collector.py`** - Real-time exchange data collection system 
- **`exchange_data_collector.py`** - Base exchange data collection functionality
- **`historical_data_backfill.py`** - Historical data backfill system for large datasets
- **`exchange_capabilities_checker.py`** - Analyzer for exchange data type capabilities

## Usage

These modules collect real market data from multiple exchanges across different timeframes and store it in the enhanced database schema for ML training and strategy backtesting.

## Key Features

- Multi-timeframe collection (1m, 5m, 15m, 1h, 4h, 1d)
- Rate limiting and error handling 
- Real exchange integration with 6+ exchanges
- Historical data backfill capabilities
- Database-first architecture for fast ML training