import sqlite3
import os

db_path = r'c:\VS CODE\Techathon\Techathon00\Offline-learning-engine\pune_content\metadata.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables:", cur.fetchall())
    
    # Check concept_mastery if it exists
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='concept_mastery';")
    if cur.fetchone()[0] > 0:
        cur.execute("PRAGMA table_info(concept_mastery);")
        print("concept_mastery info:", cur.fetchall())
    
    # Check interaction_log if it exists
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='interaction_log';")
    if cur.fetchone()[0] > 0:
        cur.execute("PRAGMA table_info(interaction_log);")
        print("interaction_log info:", cur.fetchall())
    
    conn.close()
