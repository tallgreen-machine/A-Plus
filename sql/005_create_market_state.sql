-- Create the market_state table
CREATE TABLE IF NOT EXISTS market_state (
    id SERIAL PRIMARY KEY,
    current_regime VARCHAR(50) NOT NULL,
    conviction DOUBLE PRECISION NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Insert a default row so the app can start
INSERT INTO market_state (id, current_regime, conviction)
VALUES (1, 'ranging', 0.5)
ON CONFLICT (id) DO NOTHING;
