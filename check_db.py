import sqlite3
c = sqlite3.connect('data/parafarm.db')
print([row for row in c.execute("SELECT id, name, description, unit FROM products LIMIT 10;").fetchall()])
