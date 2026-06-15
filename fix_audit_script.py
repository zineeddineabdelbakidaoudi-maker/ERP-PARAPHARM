import os
import sqlite3
import time

def fix_db():
    print("Fixing database schema...")
    for _ in range(5):
        try:
            conn = sqlite3.connect('data/parafarm.db')
            c = conn.cursor()
            try:
                c.execute('ALTER TABLE exonerations_tva ADD COLUMN date_fin VARCHAR(20)')
                c.execute('ALTER TABLE exonerations_tva ADD COLUMN montant_plafonne FLOAT DEFAULT 0.0')
                conn.commit()
            except: pass
            
            try:
                c.execute('ALTER TABLE clients ADD COLUMN last_reminder_date VARCHAR(20)')
                conn.commit()
            except: pass
            
            conn.close()
            print("DB fixed!")
            break
        except sqlite3.OperationalError:
            time.sleep(1)

def fix_models():
    print("Fixing app/models/client.py...")
    with open("app/models/client.py", "r", encoding="utf-8") as f:
        content = f.read()
    if "last_reminder_date" not in content:
        content = content.replace('is_deleted = Column(Integer, default=0)', 'is_deleted = Column(Integer, default=0)\n    last_reminder_date = Column(String(20), nullable=True)')
        with open("app/models/client.py", "w", encoding="utf-8") as f:
            f.write(content)

fix_db()
fix_models()
