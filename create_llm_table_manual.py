import sqlite3
import os

db_path = 'backend/local.db'
if not os.path.exists(db_path):
    print(f"Creating new database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Try the CREATE TABLE statement
create_stmt = """
CREATE TABLE IF NOT EXISTS llm_provider_configs (
    id VARCHAR NOT NULL PRIMARY KEY,
    provider VARCHAR NOT NULL UNIQUE,
    display_name VARCHAR NOT NULL,
    is_enabled BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 100,
    model VARCHAR,
    endpoint VARCHAR,
    api_keys_encrypted JSON DEFAULT '[]',
    additional_headers JSON DEFAULT '{}',
    extra_config JSON DEFAULT '{}',
    max_retries INTEGER DEFAULT 2,
    backoff_seconds FLOAT DEFAULT 0.8,
    timeout_seconds INTEGER DEFAULT 30,
    is_healthy BOOLEAN DEFAULT FALSE,
    last_error TEXT,
    last_checked_at TIMESTAMP,
    updated_by VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

try:
    cursor.execute(create_stmt)
    conn.commit()
    print("SUCCESS: Table created or already exists")
    
    # Check if table exists now
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='llm_provider_configs'")
    result = cursor.fetchone()
    if result:
        print("CONFIRMED: llm_provider_configs table now exists")
    else:
        print("ERROR: Table still doesn't exist after CREATE TABLE")
        
except Exception as e:
    print(f"ERROR executing CREATE TABLE: {e}")
finally:
    conn.close()
