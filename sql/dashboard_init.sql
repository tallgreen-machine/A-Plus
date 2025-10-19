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
    cash DOUBLE PRECISION NOT NULL,
    equity DOUBLE PRECISION NOT NULL
);
