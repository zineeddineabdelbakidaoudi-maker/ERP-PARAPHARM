import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import config
config.load()
from app.core.database import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    print("Database path:", config.db_path)
    res = conn.execute(text("PRAGMA table_info(supplier_invoices);")).fetchall()
    print("Columns in supplier_invoices:")
    for r in res:
        print(r)
    
    # Let's add the missing columns
    try:
        conn.execute(text("ALTER TABLE supplier_invoices ADD COLUMN is_deleted INTEGER DEFAULT 0 NOT NULL;"))
        print("Added is_deleted")
    except Exception as e:
        print("is_deleted:", e)
        
    try:
        conn.execute(text("ALTER TABLE supplier_invoices ADD COLUMN deleted_at TEXT;"))
        print("Added deleted_at")
    except Exception as e:
        print("deleted_at:", e)
    
    conn.commit()
