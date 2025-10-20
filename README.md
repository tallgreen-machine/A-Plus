# Trad

Hybrid trading AI system with three layers:

- Meta-controller (LLM Strategist): sets market regime, conviction, reward weights, and risk limits
- Representation (Encoder): turns raw market data into dense embeddings per asset
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
	# Trad

	Hybrid trading AI system with three layers:

	- Meta-controller (LLM Strategist): sets market regime, conviction, reward weights, and risk limits
	- Representation (Encoder): turns raw market data into dense embeddings per asset
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
