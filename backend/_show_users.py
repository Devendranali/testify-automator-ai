import sqlite3
conn = sqlite3.connect("test.db")
cur = conn.cursor()
cur.execute("PRAGMA table_info('users')")
print(cur.fetchall())
cur.execute("SELECT id, email, organization FROM users")
print(cur.fetchall())
conn.close()
