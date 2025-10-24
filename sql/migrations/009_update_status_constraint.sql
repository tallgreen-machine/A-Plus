-- Migration 009: Update status constraint for trained_configurations
-- Description: Add new workflow status values (CANDIDATE, ACTIVE, ARCHIVED)
--              while maintaining backward compatibility with legacy values
-- Date: 2025-10-24
-- Author: TradePulse IQ System
--
-- New Workflow:
--   CANDIDATE (new training) -> ACTIVE (user activated) -> ARCHIVED (decommissioned)
-- Legacy Values (maintained for compatibility):
--   DISCOVERY, VALIDATION, MATURE, DECAY, PAPER

BEGIN;

-- Drop old constraint
ALTER TABLE trained_configurations 
DROP CONSTRAINT IF EXISTS valid_status;

-- Add new constraint with all status values
-- Primary: CANDIDATE, ACTIVE, PAPER, ARCHIVED
-- Legacy: DISCOVERY, VALIDATION, MATURE, DECAY (backward compatibility)
ALTER TABLE trained_configurations
ADD CONSTRAINT valid_status CHECK (
    status IN ('CANDIDATE', 'ACTIVE', 'PAPER', 'ARCHIVED', 
               'DISCOVERY', 'VALIDATION', 'MATURE', 'DECAY')
);

-- Add index on status for efficient filtering
CREATE INDEX IF NOT EXISTS idx_trained_configurations_status 
ON trained_configurations(status) 
WHERE status IN ('CANDIDATE', 'ACTIVE');

COMMIT;
