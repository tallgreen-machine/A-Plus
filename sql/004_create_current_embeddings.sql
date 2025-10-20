-- Create the current_embeddings table
CREATE TABLE IF NOT EXISTS current_embeddings (
    symbol VARCHAR(20) PRIMARY KEY,
    embedding_json TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);
