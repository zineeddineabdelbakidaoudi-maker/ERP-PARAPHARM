import sqlite3
import os

db_path = 'data/parafarm.db'

def run_migration():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Update products table for CHANGE 3 (UJ logic)
    cursor.execute("PRAGMA table_info(products)")
    columns = [info[1] for info in cursor.fetchall()]
    if "uj_seuil" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN uj_seuil INTEGER DEFAULT 0")
        print("Added uj_seuil to products.")
    
    if "ppt_price" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN ppt_price FLOAT DEFAULT 0.0")
        print("Added ppt_price to products.")
        
    cursor.execute("PRAGMA table_info(sale_items)")
    si_columns = [info[1] for info in cursor.fetchall()]
    if "uj_qty" not in si_columns:
        cursor.execute("ALTER TABLE sale_items ADD COLUMN uj_qty INTEGER DEFAULT 0")
        print("Added uj_qty to sale_items.")
        
    cursor.execute("PRAGMA table_info(invoice_items)")
    ii_columns = [info[1] for info in cursor.fetchall()]
    if "uj_qty" not in ii_columns:
        cursor.execute("ALTER TABLE invoice_items ADD COLUMN uj_qty INTEGER DEFAULT 0")
        print("Added uj_qty to invoice_items.")

    # 2. Create supplier_invoices tables for CHANGE 2
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            our_reference TEXT,
            supplier_id INTEGER,
            reception_id INTEGER,
            invoice_date TEXT,
            due_date TEXT,
            total_ht FLOAT,
            total_tva FLOAT,
            total_ttc FLOAT,
            payment_mode TEXT,
            status TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
        )
    """)
    print("Checked/Created supplier_invoices table.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_invoice_id INTEGER,
            product_id INTEGER,
            designation TEXT,
            quantity FLOAT,
            unit_price_ht FLOAT,
            tva_rate FLOAT,
            tva_amount FLOAT,
            total_ht FLOAT,
            total_ttc FLOAT,
            remise_percent FLOAT,
            FOREIGN KEY(supplier_invoice_id) REFERENCES supplier_invoices(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)
    print("Checked/Created supplier_invoice_items table.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    run_migration()
