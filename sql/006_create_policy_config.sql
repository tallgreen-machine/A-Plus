-- Create the policy_config table
CREATE TABLE IF NOT EXISTS policy_config (
    id SERIAL PRIMARY KEY,
    reward_weights TEXT NOT NULL,
    risk_params TEXT NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Insert a default row so the app can start
INSERT INTO policy_config (id, reward_weights, risk_params)
VALUES (1, '{"profit": 1.0, "risk": 1.0}', '{"max_drawdown": 0.1}')
ON CONFLICT (id) DO NOTHING;
