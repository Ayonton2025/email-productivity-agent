import sqlite3
db_path = 'backend/local.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='llm_provider_configs'")
result = cursor.fetchone()
if result:
    print("SUCCESS: llm_provider_configs table exists")
    cursor.execute("SELECT COUNT(*) FROM llm_provider_configs")
    count = cursor.fetchone()[0]
    print(f"Provider configs count: {count}")
else:
    print("ERROR: llm_provider_configs table NOT found")
conn.close()
