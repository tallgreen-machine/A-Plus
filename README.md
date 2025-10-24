# TradePulse IQ - A+ Precision Trading Platform# TradePulse IQ - A+ Precision Trading Platform



**Precision-first trading system combining A-Plus financial strategies with ML parameter optimization for maximum confluence and minimal noise.****Precision-first trading system combining A-Plus financial strategies with ML parameter optimization for maximum confluence and minimal noise.**



> **V2 Dashboard Now Live!** Complete terminology refactor: Strategy→Configuration→Variable→Parameter hierarchy. Real database integration with `trained_configurations` table. See [GLOSSARY.md](./GLOSSARY.md) for terminology reference.> **V2 Dashboard Now Live!** Complete terminology refactor: Strategy→Configuration→Variable→Parameter hierarchy. Real database integration with `trained_configurations` table. See [GLOSSARY.md](./GLOSSARY.md) for terminology reference.



## 🎯 Core Philosophy: "Patience and Precision"## 🎯 Core Philosophy: "Patience and Precision"



**Quality over quantity** - We only trade high-confluence setups where multiple A+ conditions align perfectly. Our ML system doesn't generate signals; it optimizes the A+ strategy parameters for each asset to maximize precision.**Quality over quantity** - We only trade high-confluence setups where multiple A+ conditions align perfectly. Our ML system doesn't generate signals; it optimizes the A+ strategy parameters for each asset to maximize precision.



### Key Architectural Insight### Key Architectural Insight

> **"The ML system essentially creates custom-tuned versions of each A+ setup for every traded asset"**> **"The ML system essentially creates custom-tuned versions of each A+ setup for every traded asset"**



- **A+ Strategies**: Provide the core trading logic and setup identification- **A+ Strategies**: Provide the core trading logic and setup identification

- **ML Training**: Optimizes thresholds, timeframes, and parameters for each strategy per asset/exchange pair  - **ML Training**: Optimizes thresholds, timeframes, and parameters for each strategy per asset/exchange pair  

- **Execution**: Only trades when ML-optimized A+ conditions reach maximum confluence- **Execution**: Only trades when ML-optimized A+ conditions reach maximum confluence



---## 🚀 Production Deployment



## 🚀 Quick Start**Live Server**: `138.68.245.159` - TradePulse IQ Dashboard & API



### Production Server```bash

- **IP**: `138.68.245.159`# Deploy to production server

- **Dashboard**: http://138.68.245.159:8000SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh

- **API Docs**: http://138.68.245.159:8000/docs

- **SSH Access**: `ssh root@138.68.245.159`# Sync database schema

./ops/scripts/sync_schema.sh --dry-run  # Preview changes

### Deploy Application./ops/scripts/sync_schema.sh            # Apply changes

```bash

# Standard deployment (code + services)# Quick access commands

SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh./ops/scripts/server_info.sh



# Verify deployment# Verify deployment

curl http://138.68.245.159:8000/healthcurl http://138.68.245.159:8000/health

```

# Check service status

ssh root@138.68.245.159 "systemctl status trad-api.service trad-worker.service"- **Dashboard**: http://138.68.245.159:8000 (React frontend with real-time backend connection)

```- **API Docs**: http://138.68.245.159:8000/docs (30+ enhanced endpoints)

- **Database**: PostgreSQL with pgvector on localhost:5432

### Database Management

```bash📚 **Complete guides**: 

# Connect to production database (from server)- [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) - Application deployment

ssh root@138.68.245.159- [SCHEMA_MANAGEMENT.md](./docs/SCHEMA_MANAGEMENT.md) - Database schema management

source /etc/trad/trad.env

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"## 🏗️ System Architecture



# Apply schema changes### 1. A+ Strategy Foundation

./ops/scripts/sync_schema.sh --dry-run  # Preview changes**Core trading strategies based on exact A-Plus financial logic:**

./ops/scripts/sync_schema.sh            # Apply changes

- **HTF Sweep**: 1h→5m liquidity sweep + market structure shift confirmation

# Run migration- **Volume Breakout**: ATR-based consolidation + volume spike confirmation  

scp sql/migrations/011_migration.sql root@138.68.245.159:/srv/trad/sql/migrations/- **Divergence Capitulation**: Trend context + bullish divergence + volume confirmation

ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /srv/trad/sql/migrations/011_migration.sql"

```### 2. ML Parameter Optimization Engine

**Multi-dimensional training system that creates optimized strategy variants:**

### Database Connection Guidelines

```

**Always use these methods for database access:**Training Dimensions:

├── Symbol/Exchange Pairs (BTC/USDT on Binance, ETH/USDT on Coinbase, etc.)

1. **From Server (Recommended)**:├── Market Regimes (Bull, Bear, Sideways)

   ```bash├── Timeframes (1m, 5m, 15m, 1h, 4h, 1d)

   ssh root@138.68.245.159└── Strategy Parameters (ATR periods, volume thresholds, divergence sensitivity)

   source /etc/trad/trad.env

   PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT ..."Result: 54 unique combinations per asset = Custom-tuned A+ setups

   ``````



2. **For Migrations (Use postgres user)**:### 3. Enhanced Trading Infrastructure

   ```bash- **ExecutionCore**: OCO order management, position sizing, risk controls

   ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /path/to/migration.sql"- **TrainedAssetsManager**: ML model deployment and parameter optimization

   ```- **TradePulse IQ API**: 30+ endpoints for real-time monitoring and control

- **Risk Management**: Fixed percentage model with precise position calculations

3. **Common Queries**:

   ```bash### 4. Precision Trading Logic

   # List tables```python

   \dt# How strategies work with ML optimization:

   strategy = load_strategy("htf_sweep")

   # Describe tableml_params = trained_assets.get_optimized_parameters("BTC/USDT", "binance", "htf_sweep")

   \d trained_configurations

   # Apply A+ logic with ML-tuned thresholds

   # Check constraintsif strategy.check_confluence(market_data, **ml_params):

   SELECT conname FROM pg_constraint WHERE conrelid = 'trained_configurations'::regclass;    signal = strategy.generate_signal(entry_conditions=ml_params.entry_thresholds)

       execution_core.execute_trade(signal)  # Only on high-confidence setups

   # View recent configs```

   SELECT id, strategy_name, status, created_at FROM trained_configurations ORDER BY created_at DESC LIMIT 10;

   ```## 📁 Project Structure



### Development Workflow```

```bash├── api/                    # TradePulse IQ FastAPI Backend (30+ endpoints)

# 1. Make code changes locally│   ├── main.py            # FastAPI app with all routers

vim training/configuration_writer.py│   ├── portfolio.py       # Portfolio management & risk endpoints  

│   ├── trades.py          # Trade execution & history endpoints

# 2. Test locally if possible│   ├── patterns.py        # Strategy performance & trained assets

python -m training.configuration_writer│   ├── training.py        # ML training system endpoints

│   ├── analytics.py       # Market analysis & asset ranking

# 3. Deploy to production│   ├── exchanges.py       # Multi-exchange connection management

SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh│   └── static/           # React dashboard frontend files

├── core/                  # Core trading system components

# 4. Verify services│   ├── execution_core.py  # Enhanced execution with OCO orders

ssh root@138.68.245.159 "systemctl status trad-api.service trad-worker.service"│   ├── data_handler.py    # Market data management

```│   ├── event_system.py    # Event-driven architecture

│   └── signal_library.py  # Technical analysis library

---├── strategies/            # A+ Strategy implementations

│   ├── htf_sweep.py      # Higher timeframe liquidity sweep

## 🏗️ System Architecture│   ├── volume_breakout.py # ATR-based volume breakout  

│   ├── divergence_capitulation.py # Divergence + volume confirmation

### Production Services (systemd)│   └── base_strategy.py   # Strategy interface & common logic

```├── policy/               # ML Training & Model Management

trad-api.service        FastAPI backend (port 8000)│   ├── trained_assets.py # Multi-dimensional training system

trad-worker.service     RQ training worker (Redis queue)│   ├── pattern_library.py # Strategy parameter optimization

redis-server.service    Job queue (port 6379)│   └── reliability_engine.py # Model performance tracking

postgresql.service      Database (port 5432)├── shared/               # Common utilities

```│   └── db.py            # PostgreSQL connection & queries

├── ops/                  # Deployment & Operations

### Core Components│   ├── scripts/deploy_to_server.sh # Standard deployment

│   ├── systemd/         # Service configurations

#### 1. API Layer (`api/`)│   └── logrotate/       # Log management

FastAPI backend with 30+ endpoints:└── tradepulse-iq-dashboard/ # React Frontend Source

- **Portfolio**: Real-time equity, holdings, P&L    ├── App.tsx          # Main dashboard component

- **Trades**: Execution history, active positions    ├── services/realApi.ts # Backend API integration

- **Training**: ML training jobs, configuration management    └── components/      # UI components

- **Analytics**: Market analysis, strategy performance```

- **Exchanges**: Multi-exchange connections

## 🎮 TradePulse IQ Dashboard (V2)

#### 2. Training System (`training/`)

RQ-based async training with configuration persistence:**Next-generation React dashboard with real database integration and proper terminology.**

- **worker.py**: RQ worker processing training jobs

- **rq_jobs.py**: Job definitions for strategy optimization### V2 Major Changes ✨

- **configuration_writer.py**: Saves results to database- **Terminology Refactor**: Pattern→Strategy, TrainedAssets→TrainedConfigurations (see [GLOSSARY.md](./GLOSSARY.md))

- **backtest_engine.py**: Strategy backtesting- **Real Database Integration**: `trained_configurations` table with 70 columns, 10 indexes

- **Service Layer**: `tradepulse-v2/services/realApi.ts` connects to FastAPI backend (not mock data)

#### 3. Strategies (`strategies/`)- **Enhanced API**: 5 new endpoints in `api/training_configurations.py` for configuration CRUD

A+ trading strategy implementations:- **Schema Version**: 1.1.0 with auto-updating triggers

- **htf_sweep.py**: Higher timeframe liquidity sweeps

- **volume_breakout.py**: ATR-based volume breakouts### Terminology Hierarchy

- **divergence_capitulation.py**: Divergence + volume confirmation```

Strategy (LIQUIDITY_SWEEP_V3, HTF_SWEEP, VOLUME_BREAKOUT, DIVERGENCE_CAPITULATION)

#### 4. Database (`sql/`)  ↓

PostgreSQL schema management:Configuration (Strategy + Exchange + Pair + Timeframe + Regime + Variables)

- **schema.sql**: Master schema (source of truth)  ↓

- **migrations/**: Incremental changesVariable (pierce_depth, rejection_candles, volume_spike_threshold)

- **trained_configurations**: 70 columns, lifecycle management  ↓

Parameter (specific values: 0.18, 3, 2.8)

---```



## 📁 Project Structure### Key Features

- **Live Portfolio Monitoring**: Real-time equity, holdings, P&L tracking

```- **Strategy Performance**: Multi-dimensional strategy analytics per configuration

/workspaces/Trad/- **Trained Configurations**: Browse 13+ pre-trained configurations from database

├── api/                          # FastAPI backend- **Configuration Management**: Activate/deactivate configurations, view performance stats

│   ├── main.py                   # App entry + all routers- **Trade Management**: View active trades, history, and execution logs  

│   ├── training_v2.py            # RQ training endpoints- **Risk Management**: Portfolio risk metrics and position sizing

│   ├── training_configurations.py # Config CRUD- **Exchange Settings**: Multi-exchange connection testing and monitoring

│   └── static/                   # React frontend build- **Strategy Studio**: Placeholder for future AI-driven strategy creation

├── training/                     # Training system

│   ├── worker.py                 # RQ worker (moved from root)### API Integration Status ✅

│   ├── rq_jobs.py                # Job definitions- **Backend Connected**: `tradepulse-v2/services/realApi.ts` calls all 35+ API endpoints

│   ├── configuration_writer.py   # Database persistence- **Real Database**: PostgreSQL with `trained_configurations` table (schema v1.1.0)

│   ├── backtest_engine.py        # Strategy backtesting- **Data Transformation**: Automatic snake_case ↔ camelCase conversion

│   └── optimizers/               # Bayesian, grid, random- **Type Safety**: Full TypeScript types matching backend Pydantic models

├── strategies/                   # A+ strategy logic

│   ├── base_strategy.py### V2 Dashboard Architecture

│   ├── htf_sweep.py```

│   ├── volume_breakout.pytradepulse-v2/

│   └── divergence_capitulation.py├── App.tsx                          # Main dashboard (uses realApi)

├── core/                         # Core trading├── services/

│   ├── execution_core.py         # Order execution│   ├── realApi.ts                   # Real backend integration (PRODUCTION)

│   └── data_handler.py           # Market data│   └── mockApi.ts                   # Mock data (deprecated, for reference only)

├── sql/                          # Database├── components/

│   ├── schema.sql                # Master schema│   ├── StrategyPerformanceTable.tsx # Renamed from PatternPerformanceTable

│   ├── migrations/               # Schema changes│   ├── TrainedAssets.tsx           # Shows trained_configurations table

│   │   ├── 010_restore_lifecycle_status.sql│   ├── ExchangeSettings.tsx        # Exchange connection management

│   │   └── 011_remove_unique_configuration_constraint.sql│   └── StrategyStudio.tsx          # Future: AI strategy creation

│   └── dashboard_init.sql        # Dashboard tables├── types.ts                        # TypeScript definitions (Strategy*, not Pattern*)

├── ops/                          # Operations├── vite.config.ts                  # Builds to ../api/static/

│   ├── scripts/└── .env                            # VITE_API_URL configuration

│   │   ├── deploy_to_server.sh   # Standard deployment

│   │   ├── sync_schema.sh        # Schema managementBackend API (FastAPI):

│   │   └── health_check.sh       # Service verification├── api/training_configurations.py  # NEW: 5 CRUD endpoints

│   └── systemd/                  # Service files│   ├── GET    /api/training/configurations          # List with filters

│       ├── trad-api.service│   ├── GET    /api/training/configurations/{id}     # Get single config

│       └── trad-worker.service│   ├── POST   /api/training/configurations/{id}/activate

├── tradepulse-v2/                # React dashboard│   ├── POST   /api/training/configurations/{id}/deactivate

│   ├── App.tsx                   # Main component│   └── GET    /api/training/configurations/stats/summary

│   ├── services/realApi.ts       # Backend integration├── api/portfolio.py                # Portfolio & performance

│   ├── components/               # UI components├── api/trades.py                   # Trades & bot status

│   │   ├── TrainedAssets.tsx     # Configuration management├── api/strategies_api.py           # Strategy performance

│   │   ├── StrategyStudio.tsx    # Training interface└── api/exchanges.py                # Exchange connections

│   │   └── ...

│   └── vite.config.ts            # Builds to api/static/Database Schema v1.1.0:

└── docs/                         # Documentation└── trained_configurations          # NEW: 70 columns, 10 indexes

    ├── DEPLOYMENT_GUIDE.md       # Detailed deployment    ├── Core: id, strategy, exchange, pair, timeframe, status

    ├── SCHEMA_MANAGEMENT.md      # Database details    ├── Performance: net_profit, sharpe_ratio, win_rate, max_drawdown

    └── GLOSSARY.md               # Terminology guide    ├── Statistical: sample_size, confidence_interval, out_of_sample_sharpe

```    ├── Risk: max_position_size, correlation_threshold

    ├── Lifecycle: activation_date, death_signals, time_in_state

---    └── Metadata: created_at, updated_at (auto-trigger)

```

## 🗄️ Database Management

### Development & Deployment

### Schema Files```bash

- **`sql/schema.sql`**: Master schema (source of truth)# Build V2 dashboard

- **`sql/migrations/`**: Incremental migration scriptscd tradepulse-v2

- **`sql/schema_production_dump.sql`**: Reference snapshot (read-only)npm install

npm run build  # Outputs to ../api/static/

### Database Details

- **Host**: localhost (on server)# Deploy to production (includes V2 build)

- **Port**: 5432SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh

- **Database**: `trad`

- **User**: `traduser`# Access dashboard

- **Password**: `TRAD123!` (in `/etc/trad/trad.env`)open http://138.68.245.159:8000  # Served by FastAPI from api/static/

- **Owner**: `postgres` (for DDL operations)```



### Making Schema Changes### Breaking Changes from V1

- ❌ `Pattern*` types removed → Use `Strategy*` types

#### Method 1: Quick Changes (Development)- ❌ `mockApi.ts` deprecated → Use `realApi.ts` only

```bash- ❌ `trained_assets` table → Migrated to `trained_configurations`

# Edit master schema- ✅ All frontend imports updated to `realApi`

vim sql/schema.sql- ✅ Database migration 004 applied to production

- ✅ 13 seed configurations loaded for testing

# Sync to production

./ops/scripts/sync_schema.sh --dry-run  # Preview---

./ops/scripts/sync_schema.sh            # Apply

```## 🎮 TradePulse IQ Dashboard (V1 - Deprecated)



#### Method 2: Production Migrations (Recommended)**Legacy dashboard information retained for reference.**

```bash

# 1. Create migration script### V1 Dashboard Features (Legacy)

vim sql/migrations/012_add_new_column.sql- **Live Portfolio Monitoring**: Real-time equity, holdings, P&L tracking

- **Strategy Performance**: Multi-dimensional strategy analytics per asset

# 2. Test locally (if possible)- **AI Training Interface**: Start/monitor ML training sessions

psql -d trad -f sql/migrations/012_add_new_column.sql- **Trade Management**: View active trades, history, and execution logs  

- **Risk Management**: Portfolio risk metrics and position sizing

# 3. Deploy migration file- **Exchange Management**: Multi-exchange connection testing and monitoring

scp sql/migrations/012_add_new_column.sql root@138.68.245.159:/srv/trad/sql/migrations/

### V1 API Integration Status (Legacy)

# 4. Apply to production- **Backend Connected**: All 30+ API endpoints operational

ssh root@138.68.245.159 "sudo -u postgres psql -d trad -f /srv/trad/sql/migrations/012_add_new_column.sql"- **Real Database**: PostgreSQL with live portfolio and trade data

- **Authentication**: JWT-based security (currently disabled for development)

# 5. Update master schema- **Real-time Updates**: Live market data integration ready

vim sql/schema.sql  # Add the change

```---



### Migration Best Practices## 🧠 ML Training System



**Always use transactions:**### Multi-Dimensional Training Architecture

```sql**Training creates optimized A+ strategy variants across multiple dimensions:**

BEGIN;

```python

-- Your changes here# Training dimensions create asset-specific strategy optimization

ALTER TABLE trained_configurations ADD COLUMN new_field VARCHAR(50);training_job = TrainedAssetsManager.start_training(

CREATE INDEX idx_new_field ON trained_configurations(new_field);    symbols=["BTC/USDT", "ETH/USDT"],

    exchanges=["binance", "coinbase"], 

-- Rollback on error, commit on success    strategies=["htf_sweep", "volume_breakout", "divergence_capitulation"],

COMMIT;    market_regimes=["bull", "bear", "sideways"],

```    timeframes=["1m", "5m", "15m", "1h"]

)

**Make migrations idempotent:**

```sql# Result: Custom-tuned parameters for each combination

-- Good: Can run multiple times# Example: BTC/USDT + Binance + HTF_Sweep + Bull_Market + 15m timeframe

CREATE TABLE IF NOT EXISTS new_table (...);# Gets optimized: atr_period=21, volume_threshold=1.8x, sweep_confirmation=3_bars

ALTER TABLE trades ADD COLUMN IF NOT EXISTS new_column VARCHAR(50);```

DROP CONSTRAINT IF EXISTS old_constraint;

### Training Process

-- Bad: Will fail on second run1. **Historical Data Analysis**: Analyze past market conditions for each asset/exchange pair

CREATE TABLE new_table (...);2. **Strategy Backtesting**: Test A+ strategies with different parameter combinations  

ALTER TABLE trades ADD COLUMN new_column VARCHAR(50);3. **Regime Classification**: Identify bull/bear/sideways market conditions

```4. **Parameter Optimization**: Find optimal thresholds for maximum precision per regime

5. **Model Deployment**: Deploy optimized parameters for live trading

**Document changes:**

```sql### Available Training Endpoints

-- Migration 012: Add paper trading flag```bash

-- Reason: Need to differentiate between paper and live trades# Start multi-dimensional training

-- Impact: Adds nullable column, no data migration neededPOST /api/training/start-multi-dimensional

BEGIN;

ALTER TABLE trades ADD COLUMN IF NOT EXISTS is_paper BOOLEAN DEFAULT false;# Monitor training status  

COMMIT;GET /api/training/system-status

```

# Get optimized parameters for specific combination

### Common Database TasksGET /api/training/strategy-parameters/{symbol}/{exchange}/{strategy_id}

```

**View schema:**

```bash## ⚡ Core Strategy Implementation

# List tables

ssh root@138.68.245.159 "source /etc/trad/trad.env && PGPASSWORD=\"\$DB_PASSWORD\" psql -h localhost -U traduser -d trad -c '\\dt'"### 1. HTF Sweep Strategy

**Higher timeframe liquidity sweep with market structure confirmation:**

# Describe table

ssh root@138.68.245.159 "source /etc/trad/trad.env && PGPASSWORD=\"\$DB_PASSWORD\" psql -h localhost -U traduser -d trad -c '\\d trained_configurations'"```python

# A+ Logic: Look for liquidity sweeps that fail and reverse

# Check constraintsif htf_structure.sweep_detected() and htf_structure.sweep_failed():

ssh root@138.68.245.159 "source /etc/trad/trad.env && PGPASSWORD=\"\$DB_PASSWORD\" psql -h localhost -U traduser -d trad -c \"SELECT conname FROM pg_constraint WHERE conrelid = 'trained_configurations'::regclass;\""    if ml_params.confluence_confirmed(current_market_data):

```        signal = create_signal(

            direction="long" if sweep_direction == "down" else "short",

**Backup and restore:**            entry_price=ml_params.optimal_entry,

```bash            stop_loss=ml_params.optimal_stop,

# Create backup            take_profit=ml_params.optimal_target

ssh root@138.68.245.159 "sudo -u postgres pg_dump trad > /tmp/trad_backup_$(date +%Y%m%d).sql"        )

```

# Download backup

scp root@138.68.245.159:/tmp/trad_backup_*.sql ./backups/### 2. Volume Breakout Strategy  

**ATR-based consolidation with volume confirmation:**

# Restore from backup

scp backups/trad_backup_20251024.sql root@138.68.245.159:/tmp/```python

ssh root@138.68.245.159 "sudo -u postgres psql -d trad < /tmp/trad_backup_20251024.sql"# A+ Logic: Wait for tight consolidation then volume-confirmed breakout

```if consolidation.is_tight(atr_threshold=ml_params.atr_threshold):

    if volume.breakout_confirmed(volume_multiple=ml_params.volume_multiple):

---        signal = create_signal_with_ml_optimization(ml_params)

```

## 🎮 TradePulse V2 Dashboard

### 3. Divergence Capitulation Strategy

### Key Features**Trend context + bullish divergence + volume spike:**

- **Live Portfolio**: Real-time equity, holdings, P&L tracking

- **Trained Configurations**: Browse/activate ML-trained strategies```python

- **Strategy Performance**: Multi-dimensional analytics# A+ Logic: Divergence in downtrend with volume capitulation

- **Strategy Studio**: Start training jobs with configurable parametersif trend_context.is_downtrend() and divergence.is_bullish():

- **Trade Management**: View active trades and history    if volume.capitulation_detected(threshold=ml_params.capitulation_threshold):

- **Exchange Settings**: Multi-exchange connection management        signal = create_reversal_signal(ml_params)

```

### Development

```bash## 🔧 Risk Management & Position Sizing

# Install dependencies

cd tradepulse-v2### Fixed Percentage Risk Model

npm install**Precise position sizing based on account balance and stop loss distance:**



# Development mode```python

npm run dev  # Opens http://localhost:5173# Position sizing formula implemented in ExecutionCore

quantity = (account_balance * risk_percent) / abs(entry_price - stop_loss_price)

# Production build

npm run build  # Outputs to ../api/static/# Example: $100k account, 2% risk, BTC entry $50k, stop $48k

quantity = (100000 * 0.02) / abs(50000 - 48000) = 1.0 BTC

# Deploy```

cd ..

SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh### OCO Order Management

```**Simultaneous stop-loss and take-profit placement:**



### Architecture- **Native OCO**: Automatic detection and use of exchange OCO orders when available

- **Frontend**: React + TypeScript + Vite- **Emulated OCO**: Fallback system for exchanges without native OCO support

- **API Integration**: `services/realApi.ts` (real backend)- **Risk Controls**: Maximum position size, daily loss limits, correlation limits

- **Backend**: FastAPI serving from `api/static/`

- **Data Flow**: React → realApi → FastAPI → PostgreSQL## 🚀 Getting Started



---### 1. Production Access

```bash

## 🧠 ML Training System# Access live system

ssh root@138.68.245.159

### Training Architecture

Multi-dimensional training creates optimized strategy configurations:# Check services

sudo systemctl status trad-api.service

```sudo systemctl status trad.service

Training Dimensions:

├── Strategy (LIQUIDITY_SWEEP, HTF_SWEEP, VOLUME_BREAKOUT)# View logs

├── Symbol (BTC/USDT, ETH/USDT, etc.)sudo journalctl -u trad-api.service -f

├── Exchange (binanceus, kraken, coinbase)```

├── Timeframe (1m, 5m, 15m, 1h, 4h, 1d)

└── Regime (bull, bear, sideways)### 2. Development Setup

```bash

Result: Custom-tuned parameters for each combination# Clone repository

```git clone https://github.com/tallgreen-machine/Trad.git

cd Trad

### Lifecycle Stages

Training automatically assigns lifecycle stages based on performance:# Install dependencies

pip install -r requirements.txt

- **DISCOVERY**: New config, < 30 trades (max 2% allocation)pip install -r policy/requirements.txt

- **VALIDATION**: Growing confidence, 30-99 trades (max 5% allocation)

- **MATURE**: Proven, ≥100 trades + Sharpe≥1.5 (max 10% allocation)# Setup database

- **PAPER**: Poor performance, net_profit<0 or Sharpe<0.5 (0% allocation)docker-compose -f infra/compose.yml up -d

- **DECAY**: Previously good, now degrading (max 3% allocation)

# Start API server

### Training via UIuvicorn api.main:app --host 0.0.0.0 --port 8000

1. Open **Strategy Studio** tab```

2. Select strategy, symbol, exchange, timeframe, regime

3. Configure optimizer (Bayesian recommended)### 3. Start Paper Trading

4. Click "Start Training"```bash

5. Monitor progress in real-time# Configure paper trading mode

6. New configuration appears in **Trained Assets** within 5 secondsexport TRADING_MODE=paper

export RISK_PER_TRADE=0.02

### Training via API

```bash# Start trading bot

# Start training jobpython -m policy.run_trader

curl -X POST http://138.68.245.159:8000/api/v2/training/start \

  -H "Content-Type: application/json" \# Monitor via dashboard

  -d '{open http://localhost:8000

    "strategy": "LIQUIDITY_SWEEP",```

    "symbol": "BTC/USDT",

    "exchange": "binanceus",## 📈 Current Status

    "timeframe": "5m",

    "regime": "sideways",### ✅ Completed Features

    "optimizer": "bayesian",- **A+ Strategy Logic**: All three core strategies implemented with exact A-Plus logic

    "n_iterations": 50- **ML Parameter Optimization**: Multi-dimensional training system operational  

  }'- **TradePulse IQ Dashboard**: Full-stack deployment with real backend integration

- **Risk Management**: Fixed percentage model with OCO order support

# Check job status- **API Infrastructure**: 30+ endpoints with authentication and real-time data

curl http://138.68.245.159:8000/api/v2/training/jobs/{job_id}- **Production Deployment**: Live system running on DigitalOcean with PostgreSQL

```

### 🚧 Next Phase: Paper Trading

---- **Market Data Feeds**: Connect real-time price data for all supported assets

- **Strategy Activation**: Enable paper trading mode for all A+ strategies

## ⚡ A+ Strategy Implementations- **Performance Tracking**: Begin collecting real strategy performance metrics

- **ML Model Training**: Start training on live market data for parameter optimization

### 1. HTF Sweep Strategy

Higher timeframe liquidity sweep with market structure confirmation:### 🔮 Future Enhancements

- **Live Trading**: Transition from paper to live trading with real funds

```python- **Multi-Exchange Support**: Expand beyond single exchange to portfolio diversification  

# A+ Logic: Failed sweep = reversal opportunity- **Advanced Risk Management**: Portfolio-level risk controls and correlation analysis

if htf_structure.sweep_detected() and htf_structure.sweep_failed():- **Strategy Manager UI**: External configuration interface for strategy parameters

    if ml_params.confluence_confirmed(market_data):

        return create_signal(entry=ml_params.optimal_entry)---

```

**Built with precision. Optimized with intelligence. Executed with confidence.**

### 2. Volume Breakout Strategy

ATR-based consolidation with volume confirmation:*TradePulse IQ - Where A-Plus financial logic meets machine learning optimization.*

	- Policy (DRL Trader): acts using embeddings + LLM signals, executes via exchange API

```python

# A+ Logic: Tight range + volume spike = breakout	This repo includes infra (PostgreSQL + pgvector), SQL schema, and Python stubs for each layer.

if consolidation.is_tight(atr_threshold=ml_params.atr):

    if volume.spike_confirmed(multiple=ml_params.volume_multiple):	## Structure

        return create_signal(entry=ml_params.optimal_entry)

```	- infra/

		- compose.yml (Postgres + pgvector)

### 3. Divergence Capitulation Strategy		- init/ (SQL executed at DB startup)

Trend context + divergence + volume capitulation:	- sql/

		- 000_init.sql (schema reference; also applied at container init)

```python	- shared/

# A+ Logic: Divergence in downtrend + volume spike = reversal		- db.py (Postgres connection helper)

if trend_context.is_downtrend() and divergence.is_bullish():		- logging.py (JSON logging helper)

    if volume.capitulation_detected(threshold=ml_params.threshold):	- meta_controller/

        return create_reversal_signal(entry=ml_params.optimal_entry)		- requirements.txt

```		- run_metacontroller.py (stub)

		- llm_memory.py (stub)

---		- llm_tools.py (stub)

		- config.py (stub)

## 🔧 Service Management	- encoder/

		- requirements.txt

### View Logs		- encoder_model.py (stub)

```bash		- train_encoder.py (stub)

# API logs		- run_encoder.py (stub)

ssh root@138.68.245.159 "journalctl -u trad-api.service -f"- policy/

	- requirements.txt

# Worker logs	- trading_env.py (stub)

ssh root@138.68.245.159 "journalctl -u trad-worker.service -f"	- train.py (stub)

ssh root@138.68.245.159 "tail -f /var/log/trad-worker.log"	- run_trader.py (stub)

	- backfill_ohlcv.py (Kraken OHLCV seeding)

# All services- config/

ssh root@138.68.245.159 "journalctl -f"	- .env.example (environment variables template)

```	- wallets.json (multi-wallet configurations)

- Makefile (venv setup, install, infra helpers)

### Restart Services

```bash## Quick start (overview)

# Restart API only

ssh root@138.68.245.159 "systemctl restart trad-api.service"1) Copy and edit environment variables



# Restart worker only	 Duplicate `config/.env.example` to `config/.env` and fill secrets (OpenAI, Kraken).

ssh root@138.68.245.159 "systemctl restart trad-worker.service"	 Duplicate `config/wallets.json` and add your exchange API keys for each wallet.



# Restart all2) Database setup

ssh root@138.68.245.159 "systemctl restart trad-api.service trad-worker.service"

```	Option A: Use existing PostgreSQL on the host (preferred if already running)

		- Ensure pgvector extension is installed on your server

### Check Status		- Set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD in `config/.env`

```bash		- Apply schema:

# Service status		  - make db-apply-schema-host

ssh root@138.68.245.159 "systemctl status trad-api.service trad-worker.service"

		Option B: Start a local Postgres with Docker Compose (if you don’t already run Postgres)

# Health check

curl http://138.68.245.159:8000/health		- Use Docker Compose in `infra/` to start the database; it will auto-create tables.

		- If port 5432 is in use, either stop your host Postgres or edit `infra/compose.yml` to bind 127.0.0.1:55432:5432 and set DB_PORT=55432 in `config/.env`.

# Redis status

ssh root@138.68.245.159 "redis-cli ping"	3) Create Python virtual environments and install deps for each layer

```

		 - meta_controller (LLM)

---		 - encoder (representation)

		 - policy (DRL)

## 📚 Additional Documentation

	4) Seed market_data from Kraken (optional but recommended)

- **[DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md)**: Complete deployment procedures

- **[SCHEMA_MANAGEMENT.md](./docs/SCHEMA_MANAGEMENT.md)**: Database schema details		 Set `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` in `config/.env`, then run the backfill script to load 5m candles for BTC/USDT and ETH/USDT.

- **[GLOSSARY.md](./GLOSSARY.md)**: Terminology reference

- **[RQ_JOB_QUEUE_ARCHITECTURE.md](./docs/RQ_JOB_QUEUE_ARCHITECTURE.md)**: Training worker architecture	5) Run stubs to verify wiring

- **[SERVER_CONNECTION.md](./docs/SERVER_CONNECTION.md)**: SSH setup guide

		 - Meta-controller: writes defaults to `policy_config` and `market_state`

---		 - Encoder: writes placeholder embeddings to `current_embeddings`

		 - Policy: loads embeddings + config, builds observation, and no-ops actions

## 🎯 Development Guidelines

	Notes

### Code Organization

- Keep related functionality together (e.g., `worker.py` in `training/`)	- All timestamps are UTC. Scheduling is expected via cron with offsets (e.g., encoder at minute N, policy at N+1; meta-controller hourly).

- Use consistent import paths	- Embeddings are initially stored in Postgres for simplicity; can add Parquet later.

- Document database access patterns in code comments	- Kraken symbols sometimes differ; if BTC/USDT is unavailable, try BTC/USD or XBT/USDT.

	- This is a scaffold; replace stubs with production logic iteratively.

### Database Changes

1. Always use migrations for production changes	## Try it

2. Test migrations locally if possible

3. Use transactions (BEGIN/COMMIT)	These commands assume GNU Make is available and you’re in the repo root.

4. Make migrations idempotent (IF EXISTS, IF NOT EXISTS)

5. Document WHY, not just WHAT	1) Infra + envs



### Deployment	```bash

1. Use standard deployment script: `./ops/scripts/deploy_to_server.sh`	cp config/.env.example config/.env

2. Verify services after deployment	## If using existing Postgres: set DB_* in config/.env and apply schema

3. Check logs for errors	make db-apply-schema-host

4. Test critical functionality	## If using Docker Postgres instead:

	# make infra-up

### Consistency is Key	make venv-meta venv-encoder venv-policy

- Always connect to DB the same way (use documented methods)	make install-meta

- Follow established patterns for new code	make install-encoder

- Update documentation when adding features	make install-policy

- Keep README.md as single source of truth for quick reference	```



---	2) Initialize configs and seed data



**Built with precision. Optimized with intelligence. Executed with confidence.**	```bash

	# Write default policy_config and market_state

*TradePulse IQ - Where A-Plus financial logic meets machine learning optimization.*	make run-meta


	# Backfill candles from Kraken (requires API keys in config/.env)
	. .venv_policy/bin/activate && python policy/backfill_ohlcv.py
	```

	3) Embeddings + training stubs

	```bash
	make run-encoder
	make train-policy
	make run-trader
	```

	If `market_data` has rows, `run-encoder` will write `current_embeddings`, and the policy stubs will build observations.
