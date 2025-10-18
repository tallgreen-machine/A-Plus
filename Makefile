.PHONY: help infra-up infra-down db-psql db-psql-host db-apply-schema-host venv-meta venv-encoder venv-policy install-meta install-encoder install-policy run-meta run-encoder train-encoder train-policy run-trader

PROJECT_ROOT:=$(shell pwd)

help:
	@echo "Targets:"
	@echo "  infra-up         - start Postgres+pgvector via docker compose"
	@echo "  infra-down       - stop infra"
	@echo "  db-psql          - open psql shell in container"
	@echo "  db-psql-host     - open psql to existing Postgres using config/.env"
	@echo "  db-apply-schema-host - apply schema to existing Postgres using config/.env"
	@echo "  venv-meta        - create venv for meta_controller"
	@echo "  venv-encoder     - create venv for encoder"
	@echo "  venv-policy      - create venv for policy"
	@echo "  install-meta     - install meta_controller requirements"
	@echo "  install-encoder  - install encoder requirements"
	@echo "  install-policy   - install policy requirements"
	@echo "  run-meta         - run meta_controller stub"
	@echo "  run-encoder      - run encoder stub"
	@echo "  train-encoder    - save placeholder encoder.pth"
	@echo "  train-policy     - train stub PPO and save model"
	@echo "  run-trader       - run trader stub"

infra-up:
	cd infra && docker compose up -d

infra-down:
	cd infra && docker compose down

db-psql:
	docker exec -it trad_db psql -U trad -d trad

db-psql-host:
	set -a; . config/.env; set +a; \
	psql -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d $$DB_NAME

db-apply-schema-host:
	set -a; . config/.env; set +a; \
	psql -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d $$DB_NAME -f infra/init/000_init.sql

venv-meta:
	# Prefer virtualenv (bundles pip); fallback to venv --without-pip (Python 3.13 ensurepip issues)
	if command -v virtualenv >/dev/null 2>&1; then \
		virtualenv -p python3 .venv_meta; \
	else \
		python3 -m venv --without-pip .venv_meta; \
	fi

venv-encoder:
	if command -v virtualenv >/dev/null 2>&1; then \
		virtualenv -p python3 .venv_encoder; \
	else \
		python3 -m venv --without-pip .venv_encoder; \
	fi

venv-policy:
	if command -v virtualenv >/dev/null 2>&1; then \
		virtualenv -p python3 .venv_policy; \
	else \
		python3 -m venv --without-pip .venv_policy; \
	fi

install-meta: venv-meta
	. .venv_meta/bin/activate && \
		( python -m pip --version || ( curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && python /tmp/get-pip.py ) ); \
		python -m pip install -U pip setuptools wheel; \
		python -m pip install -r meta_controller/requirements.txt

install-encoder: venv-encoder
	. .venv_encoder/bin/activate && \
		( python -m pip --version || ( curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && python /tmp/get-pip.py ) ); \
		export PIP_NO_CACHE_DIR=1; \
		python -m pip install -U pip setuptools wheel; \
		python -m pip install --only-binary=:all: --no-cache-dir numpy pandas typing-extensions; \
		python -m pip install --index-url https://download.pytorch.org/whl/cpu --no-cache-dir torch==2.9.0; \
		python -m pip install --only-binary=:all: --no-cache-dir psycopg2-binary python-dotenv

install-policy: venv-policy
	. .venv_policy/bin/activate && \
		( python -m pip --version || ( curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && python /tmp/get-pip.py ) ); \
		export PIP_NO_CACHE_DIR=1; \
		python -m pip install -U pip setuptools wheel; \
		python -m pip install --only-binary=:all: --no-cache-dir numpy pandas typing-extensions; \
		python -m pip install --index-url https://download.pytorch.org/whl/cpu --no-cache-dir torch==2.9.0; \
		python -m pip install --only-binary=:all: --no-cache-dir gymnasium stable-baselines3 psycopg2-binary ccxt python-dotenv

run-meta: install-meta
	. .venv_meta/bin/activate && PYTHONPATH="$(PROJECT_ROOT)" python -m meta_controller.run_metacontroller

run-encoder: install-encoder
	. .venv_encoder/bin/activate && PYTHONPATH="$(PROJECT_ROOT)" python -m encoder.run_encoder

train-encoder: install-encoder
	. .venv_encoder/bin/activate && PYTHONPATH="$(PROJECT_ROOT)" python -m encoder.train_encoder

train-policy: install-policy
	. .venv_policy/bin/activate && PYTHONPATH="$(PROJECT_ROOT)" python -m policy.train

run-trader: install-policy
	. .venv_policy/bin/activate && PYTHONPATH="$(PROJECT_ROOT)" python -m policy.run_trader
