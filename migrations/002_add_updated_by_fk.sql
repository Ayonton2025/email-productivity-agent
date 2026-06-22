-- Migration: Add foreign key constraint for llm_provider_configs.updated_by -> users.id
-- Run with psql or your DB migration tooling.

BEGIN;

-- Ensure the column exists before adding the constraint (safe when model was previously altered)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='llm_provider_configs' AND column_name='updated_by'
    ) THEN
        -- Add constraint if it does not already exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'llm_provider_configs' AND tc.constraint_type = 'FOREIGN KEY' AND kcu.column_name = 'updated_by'
        ) THEN
            ALTER TABLE llm_provider_configs
            ADD CONSTRAINT fk_llm_updated_by_users
            FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL;
        END IF;
    END IF;
END$$;

COMMIT;
