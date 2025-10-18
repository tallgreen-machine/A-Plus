-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- market_data: OHLCV per symbol and timestamp
CREATE TABLE IF NOT EXISTS market_data (
  symbol TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  open NUMERIC(18,8) NOT NULL,
  high NUMERIC(18,8) NOT NULL,
  low NUMERIC(18,8) NOT NULL,
  close NUMERIC(18,8) NOT NULL,
  volume NUMERIC(28,8) NOT NULL,
  PRIMARY KEY(symbol, ts)
);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_ts_desc ON market_data(symbol, ts DESC);

-- news_sentiment: optional news stream with sentiment
CREATE TABLE IF NOT EXISTS news_sentiment (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL,
  source TEXT,
  symbol TEXT,
  sentiment_score REAL,
  topic TEXT,
  summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_news_sentiment_ts_desc ON news_sentiment(ts DESC);
CREATE INDEX IF NOT EXISTS idx_news_sentiment_symbol_ts_desc ON news_sentiment(symbol, ts DESC);

-- onchain_data: chain metrics over time
CREATE TABLE IF NOT EXISTS onchain_data (
  chain TEXT NOT NULL,
  metric TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  value NUMERIC(28,8) NOT NULL,
  PRIMARY KEY(chain, metric, ts)
);

-- memory_logs: LLM strategist reflections with embedding
-- Adjust vector dimension to match chosen embedding model
CREATE TABLE IF NOT EXISTS memory_logs (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  strategy_text TEXT NOT NULL,
  strategy_embedding VECTOR(1536) NOT NULL,
  tags JSONB NOT NULL DEFAULT '{}'::jsonb,
  outcome_text TEXT,
  outcome_metrics JSONB NOT NULL DEFAULT '{}'::jsonb
);
-- ivfflat index for vector similarity (enable after ANALYZE and sufficient rows)
-- CREATE INDEX IF NOT EXISTS idx_memory_logs_embedding ON memory_logs USING ivfflat (strategy_embedding vector_l2_ops) WITH (lists = 100);

-- market_state: single-row bridge for regime/conviction
CREATE TABLE IF NOT EXISTS market_state (
  id SMALLINT PRIMARY KEY DEFAULT 1,
  current_regime TEXT NOT NULL CHECK (current_regime IN ('BEARISH','NEUTRAL','BULLISH')),
  conviction REAL NOT NULL CHECK (conviction >= -1.0 AND conviction <= 1.0),
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO market_state (id, current_regime, conviction) VALUES (1, 'NEUTRAL', 0.0)
  ON CONFLICT (id) DO NOTHING;

-- policy_config: single-row control panel for DRL
CREATE TABLE IF NOT EXISTS policy_config (
  id SMALLINT PRIMARY KEY DEFAULT 1,
  reward_weights JSONB NOT NULL,
  risk_params JSONB NOT NULL,
  active_strategies JSONB NOT NULL,
  config_version BIGINT NOT NULL DEFAULT 1,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO policy_config (id, reward_weights, risk_params, active_strategies)
VALUES (
  1,
  '{"sharpe":0.6, "pnl":0.3, "drawdown":-0.1, "turnover":-0.1}',
  '{"max_pos":0.15, "daily_loss_stop":-0.05, "pause":false}',
  '["breakout","mean_revert"]'
) ON CONFLICT (id) DO NOTHING;

-- current_embeddings: per-asset embeddings at timestamp
-- Adjust vector dimension to match encoder model
CREATE TABLE IF NOT EXISTS current_embeddings (
  symbol TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  embedding VECTOR(128) NOT NULL,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY(symbol, ts)
);
CREATE INDEX IF NOT EXISTS idx_current_embeddings_ts_desc ON current_embeddings(ts DESC);
CREATE INDEX IF NOT EXISTS idx_current_embeddings_symbol_ts_desc ON current_embeddings(symbol, ts DESC);
