-- Migration 010: Restore lifecycle-only status constraint
-- Date: 2025-10-24
-- Description: Remove CANDIDATE/ACTIVE/ARCHIVED from status field, restore to lifecycle stages only
--              Activation is controlled by is_active boolean, not status field

BEGIN;

-- Drop the current constraint
ALTER TABLE trained_configurations 
DROP CONSTRAINT IF EXISTS valid_status;

-- Recreate constraint with lifecycle stages only
ALTER TABLE trained_configurations
ADD CONSTRAINT valid_status CHECK (status IN ('DISCOVERY', 'VALIDATION', 'MATURE', 'DECAY', 'PAPER'));

-- Update any existing 'ACTIVE' or 'CANDIDATE' statuses to appropriate lifecycle stages
-- ACTIVE configs likely came from activation - preserve their original lifecycle or default to VALIDATION
UPDATE trained_configurations 
SET status = 'VALIDATION'
WHERE status = 'ACTIVE' OR status = 'CANDIDATE' OR status = 'ARCHIVED';

-- Confirm updated rows
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_count
    FROM trained_configurations
    WHERE status NOT IN ('DISCOVERY', 'VALIDATION', 'MATURE', 'DECAY', 'PAPER');
    
    IF updated_count > 0 THEN
        RAISE EXCEPTION 'Migration failed: % rows still have invalid status values', updated_count;
    END IF;
    
    RAISE NOTICE 'Migration 010 completed successfully. All status values are now valid lifecycle stages.';
END $$;

COMMIT;
