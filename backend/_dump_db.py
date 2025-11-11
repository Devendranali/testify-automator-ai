import sqlite3
from pathlib import Path
conn = sqlite3.connect("test.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(c.fetchall())
conn.close()
