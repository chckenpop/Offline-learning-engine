import sqlite3
import os

db_path = r'c:\VS CODE\Techathon\Techathon00\Offline-learning-engine\pune_content\metadata.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print("Tables:", tables)
    
    for table_name_tuple in tables:
        table_name = table_name_tuple[0]
        cur.execute(f"PRAGMA table_info({table_name});")
        print(f"\nSchema for {table_name}:", cur.fetchall())
        
        # Also check row count
        cur.execute(f"SELECT count(*) FROM {table_name}")
        print(f"Count for {table_name}:", cur.fetchone()[0])
    
    conn.close()
