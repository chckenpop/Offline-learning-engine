import sqlite3, os
DB = os.path.join(os.path.dirname(__file__), '..', 'pune_content', 'metadata.db')
print('DB exists', os.path.exists(DB))
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    cur.execute('SELECT id, type, version FROM cached_content')
    rows = cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('Error reading cached_content:', e)
conn.close()
