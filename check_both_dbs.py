import sqlite3
import os

for db_name in ['local.db', 'email_agent.db']:
    db_path = f'backend/{db_name}'
    if not os.path.exists(db_path):
        print(f"{db_path}: FILE DOES NOT EXIST")
        continue
    
    print(f"\n=== Checking {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
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
    except Exception as e:
        print(f"Error: {e}")
