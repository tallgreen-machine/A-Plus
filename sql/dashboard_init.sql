-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    direction VARCHAR(4) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    fill_cost DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION NOT NULL
);

-- Portfolio History Table
CREATE TABLE IF NOT EXISTS portfolio_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    wallet_id VARCHAR(255) NOT NULL,
    cash DOUBLE PRECISION NOT NULL,
    equity DOUBLE PRECISION NOT NULL
);

-- Ensure historic deployments have the wallet_id column (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='portfolio_history' AND column_name='wallet_id'
    ) THEN
        ALTER TABLE portfolio_history ADD COLUMN IF NOT EXISTS wallet_id VARCHAR(255) NOT NULL DEFAULT 'unknown';
    END IF;
END$$;

-- Symbol status table: tracks whether a requested symbol is available
CREATE TABLE IF NOT EXISTS symbol_status (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(32) NOT NULL, -- e.g. 'available', 'unavailable', 'unknown'
    reason TEXT NULL, -- optional explanation (exchange error, not listed, etc.)
    last_checked TIMESTAMPTZ NOT NULL DEFAULT now()
);
