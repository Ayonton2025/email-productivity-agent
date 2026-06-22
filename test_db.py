import sqlite3

db_path = 'backend/local.db'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print('Tables in database:')
    for table in tables:
        print(f'  - {table[0]}')
    
    # Check if llm_provider_configs exists
    if any(t[0] == 'llm_provider_configs' for t in tables):
        cursor.execute('SELECT COUNT(*) FROM llm_provider_configs')
        count = cursor.fetchone()[0]
        print(f'\nLLM Provider Configs: {count} rows')
        if count > 0:
            cursor.execute('SELECT provider, is_enabled FROM llm_provider_configs LIMIT 5')
            rows = cursor.fetchall()
            for row in rows:
                print(f'  - {row[0]}: enabled={row[1]}')
    else:
        print('\n❌ llm_provider_configs table does not exist')
    conn.close()
except Exception as e:
    print(f'Error: {e}')
