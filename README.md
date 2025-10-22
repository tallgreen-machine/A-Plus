# TradePulse IQ - A+ Precision Trading Platform

**Precision-first trading system combining A-Plus financial strategies with ML parameter optimization for maximum confluence and minimal noise.**

## 🎯 Core Philosophy: "Patience and Precision"

**Quality over quantity** - We only trade high-confluence setups where multiple A+ conditions align perfectly. Our ML system doesn't generate signals; it optimizes the A+ strategy parameters for each asset to maximize precision.

### Key Architectural Insight
> **"The ML system essentially creates custom-tuned versions of each A+ setup for every traded asset"**

- **A+ Strategies**: Provide the core trading logic and setup identification
- **ML Training**: Optimizes thresholds, timeframes, and parameters for each strategy per asset/exchange pair  
- **Execution**: Only trades when ML-optimized A+ conditions reach maximum confluence

## 🚀 Production Deployment

**Live Server**: `138.68.245.159` - TradePulse IQ Dashboard & API

```bash
# Deploy to production server
SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh

# Sync database schema
./ops/scripts/sync_schema.sh --dry-run  # Preview changes
./ops/scripts/sync_schema.sh            # Apply changes

# Quick access commands
./ops/scripts/server_info.sh

# Verify deployment
curl http://138.68.245.159:8000/health
```

- **Dashboard**: http://138.68.245.159:8000 (React frontend with real-time backend connection)
- **API Docs**: http://138.68.245.159:8000/docs (30+ enhanced endpoints)
- **Database**: PostgreSQL with pgvector on localhost:5432

📚 **Complete guides**: 
- [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) - Application deployment
- [SCHEMA_MANAGEMENT.md](./docs/SCHEMA_MANAGEMENT.md) - Database schema management

## 🏗️ System Architecture

### 1. A+ Strategy Foundation
**Core trading strategies based on exact A-Plus financial logic:**

- **HTF Sweep**: 1h→5m liquidity sweep + market structure shift confirmation
- **Volume Breakout**: ATR-based consolidation + volume spike confirmation  
- **Divergence Capitulation**: Trend context + bullish divergence + volume confirmation

### 2. ML Parameter Optimization Engine
**Multi-dimensional training system that creates optimized strategy variants:**

```
Training Dimensions:
├── Symbol/Exchange Pairs (BTC/USDT on Binance, ETH/USDT on Coinbase, etc.)
├── Market Regimes (Bull, Bear, Sideways)
├── Timeframes (1m, 5m, 15m, 1h, 4h, 1d)
└── Strategy Parameters (ATR periods, volume thresholds, divergence sensitivity)

Result: 54 unique combinations per asset = Custom-tuned A+ setups
```

### 3. Enhanced Trading Infrastructure
- **ExecutionCore**: OCO order management, position sizing, risk controls
- **TrainedAssetsManager**: ML model deployment and parameter optimization
- **TradePulse IQ API**: 30+ endpoints for real-time monitoring and control
- **Risk Management**: Fixed percentage model with precise position calculations

### 4. Precision Trading Logic
```python
# How strategies work with ML optimization:
strategy = load_strategy("htf_sweep")
ml_params = trained_assets.get_optimized_parameters("BTC/USDT", "binance", "htf_sweep")

# Apply A+ logic with ML-tuned thresholds
if strategy.check_confluence(market_data, **ml_params):
    signal = strategy.generate_signal(entry_conditions=ml_params.entry_thresholds)
    execution_core.execute_trade(signal)  # Only on high-confidence setups
```

## 📁 Project Structure

```
├── api/                    # TradePulse IQ FastAPI Backend (30+ endpoints)
│   ├── main.py            # FastAPI app with all routers
│   ├── portfolio.py       # Portfolio management & risk endpoints  
│   ├── trades.py          # Trade execution & history endpoints
│   ├── patterns.py        # Strategy performance & trained assets
│   ├── training.py        # ML training system endpoints
│   ├── analytics.py       # Market analysis & asset ranking
│   ├── exchanges.py       # Multi-exchange connection management
│   └── static/           # React dashboard frontend files
├── core/                  # Core trading system components
│   ├── execution_core.py  # Enhanced execution with OCO orders
│   ├── data_handler.py    # Market data management
│   ├── event_system.py    # Event-driven architecture
│   └── signal_library.py  # Technical analysis library
├── strategies/            # A+ Strategy implementations
│   ├── htf_sweep.py      # Higher timeframe liquidity sweep
│   ├── volume_breakout.py # ATR-based volume breakout  
│   ├── divergence_capitulation.py # Divergence + volume confirmation
│   └── base_strategy.py   # Strategy interface & common logic
├── policy/               # ML Training & Model Management
│   ├── trained_assets.py # Multi-dimensional training system
│   ├── pattern_library.py # Strategy parameter optimization
│   └── reliability_engine.py # Model performance tracking
├── shared/               # Common utilities
│   └── db.py            # PostgreSQL connection & queries
├── ops/                  # Deployment & Operations
│   ├── scripts/deploy_to_server.sh # Standard deployment
│   ├── systemd/         # Service configurations
│   └── logrotate/       # Log management
└── tradepulse-iq-dashboard/ # React Frontend Source
    ├── App.tsx          # Main dashboard component
    ├── services/realApi.ts # Backend API integration
    └── components/      # UI components
```

## 🎮 TradePulse IQ Dashboard

**Real-time trading dashboard with full backend integration:**

### Key Features
- **Live Portfolio Monitoring**: Real-time equity, holdings, P&L tracking
- **Strategy Performance**: Multi-dimensional strategy analytics per asset
- **AI Training Interface**: Start/monitor ML training sessions
- **Trade Management**: View active trades, history, and execution logs  
- **Risk Management**: Portfolio risk metrics and position sizing
- **Exchange Management**: Multi-exchange connection testing and monitoring

### API Integration Status ✅
- **Backend Connected**: All 30+ API endpoints operational
- **Real Database**: PostgreSQL with live portfolio and trade data
- **Authentication**: JWT-based security (currently disabled for development)
- **Real-time Updates**: Live market data integration ready

## 🧠 ML Training System

### Multi-Dimensional Training Architecture
**Training creates optimized A+ strategy variants across multiple dimensions:**

```python
# Training dimensions create asset-specific strategy optimization
training_job = TrainedAssetsManager.start_training(
    symbols=["BTC/USDT", "ETH/USDT"],
    exchanges=["binance", "coinbase"], 
    strategies=["htf_sweep", "volume_breakout", "divergence_capitulation"],
    market_regimes=["bull", "bear", "sideways"],
    timeframes=["1m", "5m", "15m", "1h"]
)

# Result: Custom-tuned parameters for each combination
# Example: BTC/USDT + Binance + HTF_Sweep + Bull_Market + 15m timeframe
# Gets optimized: atr_period=21, volume_threshold=1.8x, sweep_confirmation=3_bars
```

### Training Process
1. **Historical Data Analysis**: Analyze past market conditions for each asset/exchange pair
2. **Strategy Backtesting**: Test A+ strategies with different parameter combinations  
3. **Regime Classification**: Identify bull/bear/sideways market conditions
4. **Parameter Optimization**: Find optimal thresholds for maximum precision per regime
5. **Model Deployment**: Deploy optimized parameters for live trading

### Available Training Endpoints
```bash
# Start multi-dimensional training
POST /api/training/start-multi-dimensional

# Monitor training status  
GET /api/training/system-status

# Get optimized parameters for specific combination
GET /api/training/strategy-parameters/{symbol}/{exchange}/{strategy_id}
```

## ⚡ Core Strategy Implementation

### 1. HTF Sweep Strategy
**Higher timeframe liquidity sweep with market structure confirmation:**

```python
# A+ Logic: Look for liquidity sweeps that fail and reverse
if htf_structure.sweep_detected() and htf_structure.sweep_failed():
    if ml_params.confluence_confirmed(current_market_data):
        signal = create_signal(
            direction="long" if sweep_direction == "down" else "short",
            entry_price=ml_params.optimal_entry,
            stop_loss=ml_params.optimal_stop,
            take_profit=ml_params.optimal_target
        )
```

### 2. Volume Breakout Strategy  
**ATR-based consolidation with volume confirmation:**

```python
# A+ Logic: Wait for tight consolidation then volume-confirmed breakout
if consolidation.is_tight(atr_threshold=ml_params.atr_threshold):
    if volume.breakout_confirmed(volume_multiple=ml_params.volume_multiple):
        signal = create_signal_with_ml_optimization(ml_params)
```

### 3. Divergence Capitulation Strategy
**Trend context + bullish divergence + volume spike:**

```python
# A+ Logic: Divergence in downtrend with volume capitulation
if trend_context.is_downtrend() and divergence.is_bullish():
    if volume.capitulation_detected(threshold=ml_params.capitulation_threshold):
        signal = create_reversal_signal(ml_params)
```

## 🔧 Risk Management & Position Sizing

### Fixed Percentage Risk Model
**Precise position sizing based on account balance and stop loss distance:**

```python
# Position sizing formula implemented in ExecutionCore
quantity = (account_balance * risk_percent) / abs(entry_price - stop_loss_price)

# Example: $100k account, 2% risk, BTC entry $50k, stop $48k
quantity = (100000 * 0.02) / abs(50000 - 48000) = 1.0 BTC
```

### OCO Order Management
**Simultaneous stop-loss and take-profit placement:**

- **Native OCO**: Automatic detection and use of exchange OCO orders when available
- **Emulated OCO**: Fallback system for exchanges without native OCO support
- **Risk Controls**: Maximum position size, daily loss limits, correlation limits

## 🚀 Getting Started

### 1. Production Access
```bash
# Access live system
ssh root@138.68.245.159

# Check services
sudo systemctl status trad-api.service
sudo systemctl status trad.service

# View logs
sudo journalctl -u trad-api.service -f
```

### 2. Development Setup
```bash
# Clone repository
git clone https://github.com/tallgreen-machine/Trad.git
cd Trad

# Install dependencies
pip install -r requirements.txt
pip install -r policy/requirements.txt

# Setup database
docker-compose -f infra/compose.yml up -d

# Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 3. Start Paper Trading
```bash
# Configure paper trading mode
export TRADING_MODE=paper
export RISK_PER_TRADE=0.02

# Start trading bot
python -m policy.run_trader

# Monitor via dashboard
open http://localhost:8000
```

## 📈 Current Status

### ✅ Completed Features
- **A+ Strategy Logic**: All three core strategies implemented with exact A-Plus logic
- **ML Parameter Optimization**: Multi-dimensional training system operational  
- **TradePulse IQ Dashboard**: Full-stack deployment with real backend integration
- **Risk Management**: Fixed percentage model with OCO order support
- **API Infrastructure**: 30+ endpoints with authentication and real-time data
- **Production Deployment**: Live system running on DigitalOcean with PostgreSQL

### 🚧 Next Phase: Paper Trading
- **Market Data Feeds**: Connect real-time price data for all supported assets
- **Strategy Activation**: Enable paper trading mode for all A+ strategies
- **Performance Tracking**: Begin collecting real strategy performance metrics
- **ML Model Training**: Start training on live market data for parameter optimization

### 🔮 Future Enhancements
- **Live Trading**: Transition from paper to live trading with real funds
- **Multi-Exchange Support**: Expand beyond single exchange to portfolio diversification  
- **Advanced Risk Management**: Portfolio-level risk controls and correlation analysis
- **Strategy Manager UI**: External configuration interface for strategy parameters

---

**Built with precision. Optimized with intelligence. Executed with confidence.**

*TradePulse IQ - Where A-Plus financial logic meets machine learning optimization.*
	- Policy (DRL Trader): acts using embeddings + LLM signals, executes via exchange API

	This repo includes infra (PostgreSQL + pgvector), SQL schema, and Python stubs for each layer.

	## Structure

	- infra/
		- compose.yml (Postgres + pgvector)
		- init/ (SQL executed at DB startup)
	- sql/
		- 000_init.sql (schema reference; also applied at container init)
	- shared/
		- db.py (Postgres connection helper)
		- logging.py (JSON logging helper)
	- meta_controller/
		- requirements.txt
		- run_metacontroller.py (stub)
		- llm_memory.py (stub)
		- llm_tools.py (stub)
		- config.py (stub)
	- encoder/
		- requirements.txt
		- encoder_model.py (stub)
		- train_encoder.py (stub)
		- run_encoder.py (stub)
- policy/
	- requirements.txt
	- trading_env.py (stub)
	- train.py (stub)
	- run_trader.py (stub)
	- backfill_ohlcv.py (Kraken OHLCV seeding)
- config/
	- .env.example (environment variables template)
	- wallets.json (multi-wallet configurations)
- Makefile (venv setup, install, infra helpers)

## Quick start (overview)

1) Copy and edit environment variables

	 Duplicate `config/.env.example` to `config/.env` and fill secrets (OpenAI, Kraken).
	 Duplicate `config/wallets.json` and add your exchange API keys for each wallet.

2) Database setup

	Option A: Use existing PostgreSQL on the host (preferred if already running)
		- Ensure pgvector extension is installed on your server
		- Set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD in `config/.env`
		- Apply schema:
		  - make db-apply-schema-host

		Option B: Start a local Postgres with Docker Compose (if you don’t already run Postgres)

		- Use Docker Compose in `infra/` to start the database; it will auto-create tables.
		- If port 5432 is in use, either stop your host Postgres or edit `infra/compose.yml` to bind 127.0.0.1:55432:5432 and set DB_PORT=55432 in `config/.env`.

	3) Create Python virtual environments and install deps for each layer

		 - meta_controller (LLM)
		 - encoder (representation)
		 - policy (DRL)

	4) Seed market_data from Kraken (optional but recommended)

		 Set `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` in `config/.env`, then run the backfill script to load 5m candles for BTC/USDT and ETH/USDT.

	5) Run stubs to verify wiring

		 - Meta-controller: writes defaults to `policy_config` and `market_state`
		 - Encoder: writes placeholder embeddings to `current_embeddings`
		 - Policy: loads embeddings + config, builds observation, and no-ops actions

	Notes

	- All timestamps are UTC. Scheduling is expected via cron with offsets (e.g., encoder at minute N, policy at N+1; meta-controller hourly).
	- Embeddings are initially stored in Postgres for simplicity; can add Parquet later.
	- Kraken symbols sometimes differ; if BTC/USDT is unavailable, try BTC/USD or XBT/USDT.
	- This is a scaffold; replace stubs with production logic iteratively.

	## Try it

	These commands assume GNU Make is available and you’re in the repo root.

	1) Infra + envs

	```bash
	cp config/.env.example config/.env
	## If using existing Postgres: set DB_* in config/.env and apply schema
	make db-apply-schema-host
	## If using Docker Postgres instead:
	# make infra-up
	make venv-meta venv-encoder venv-policy
	make install-meta
	make install-encoder
	make install-policy
	```

	2) Initialize configs and seed data

	```bash
	# Write default policy_config and market_state
	make run-meta

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
