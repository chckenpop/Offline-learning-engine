import sqlite3,os
DB=os.path.join('..','database','progress.db')
print('DB exists', os.path.exists(DB))
conn=sqlite3.connect(DB)
cur=conn.cursor()
try:
    cur.execute('SELECT content_id,type,version FROM installed_content')
    rows=cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('Error reading installed_content:',e)
conn.close()
