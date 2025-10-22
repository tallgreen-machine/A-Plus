-- Create the current_embeddings table
CREATE TABLE IF NOT EXISTS current_embeddings (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    embedding_json TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

-- Add model_id column if it doesn't exist
DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='current_embeddings' AND column_name='model_id') THEN
      ALTER TABLE current_embeddings ADD COLUMN model_id VARCHAR(50);
   END IF;
END;
$$;

-- Create an index on symbol and timestamp for faster lookups
CREATE INDEX IF NOT EXISTS idx_current_embeddings_symbol_timestamp ON current_embeddings(symbol, timestamp DESC);

-- Remove the old primary key constraint if it exists and isn't on 'id'
DO $$
DECLARE
    con_name TEXT;
BEGIN
   SELECT con.conname
   INTO con_name
   FROM pg_constraint con
   JOIN pg_attribute att ON att.attnum = ANY(con.conkey)
   WHERE con.conrelid = 'current_embeddings'::regclass
     AND con.contype = 'p'
     AND att.attname != 'id';

   IF con_name IS NOT NULL THEN
      EXECUTE 'ALTER TABLE current_embeddings DROP CONSTRAINT ' || quote_ident(con_name);
   END IF;
END;
$$;
