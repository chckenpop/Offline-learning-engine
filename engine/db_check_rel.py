import sqlite3
import os

# Go up one level from 'engine' to 'Offline-learning-engine'
engine_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(engine_dir, "..", "pune_content", "metadata.db")
db_path = os.path.abspath(db_path)

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
else:
    print(f"Found DB at {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print("Tables:", tables)
    
    for table_name_tuple in tables:
        table_name = table_name_tuple[0]
        cur.execute(f"PRAGMA table_info({table_name});")
        print(f"\nSchema for {table_name}:", cur.fetchall())
    
    conn.close()
