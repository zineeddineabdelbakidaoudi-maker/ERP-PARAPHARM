import sqlite3
import os

db_path = 'data/parafarm.db'

if not os.path.exists(db_path):
    print("Database not found at data/parafarm.db")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    # Check if column exists
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "ug_percent" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN ug_percent FLOAT DEFAULT 0.0")
        conn.commit()
        print("Column 'ug_percent' added to 'products' table successfully!")
    else:
        print("Column 'ug_percent' already exists.")
except Exception as e:
    print(f"Error updating database: {e}")
finally:
    if 'conn' in locals():
        conn.close()
