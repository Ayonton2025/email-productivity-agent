-- Migration: Fix email uid column integer overflow
-- Description: Change the uid column from INTEGER (int32) to BIGINT (int64)
--              to support Gmail's internalDate values in milliseconds
--              e.g., 1770336136000 exceeds int32 max (~2.1 billion)
-- Date: 2026-02-06

BEGIN;

-- Alter the uid column type from INTEGER to BIGINT
ALTER TABLE emails ALTER COLUMN uid TYPE BIGINT;

COMMIT;
