# Archive Directory

This directory contains files that were moved from the project root during cleanup on October 22, 2025.

## Directory Structure

### old_tests/
Contains legacy test files that were used during development but are no longer needed:
- `test_enhanced_apis.py` - Early API testing script
- `test_multi_dimensional_training.py` - Training system test (duplicate)
- `test_multidimensional_training.py` - Training system test (main)

### old_scripts/
Contains legacy scripts and configuration files:
- `backtest.py` - Original backtesting script (superseded by enhanced system)
- `main.py` - Original main entry point (superseded by TradePulse IQ)
- `start_dashboard.sh` - Old dashboard startup script (superseded by systemd)
- `config.ini` - Legacy configuration file (superseded by .env files)
- `api-debug.html` - Development debugging interface
- `api-test.html` - API testing interface

### old_data_files/
Contains legacy data files that were used for testing:
- `market_data.csv` - Sample market data for development
- `active_patterns.json` - Legacy pattern configuration

## Cleanup Policy

These files are kept for reference but should not be needed for current system operation. They can be safely deleted after confirming the new TradePulse IQ system is stable and all functionality has been migrated.

## Restored File Locations

- `server_info.sh` → Moved to `ops/scripts/server_info.sh` (proper location)

---

*Archived during TradePulse IQ cleanup - October 22, 2025*