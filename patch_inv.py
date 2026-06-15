import re

with open('ui/pages/invoices_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add import if missing
if 'from app.models.setting import AuditLog' not in text:
    text = text.replace('from app.models.sale import Sale', 'from app.models.sale import Sale\nfrom app.models.setting import AuditLog')

# We'll just patch the _validate_and_save to include AuditLog
# Assuming invoices_page has self.db_session.add(invoice) and self.db_session.commit()
if 'self.db_session.commit()' in text:
    audit_code = """
        # Record Audit Log
        try:
            from datetime import datetime
            from app.models.setting import AuditLog
            audit = AuditLog(
                user_id=self.user.id,
                module="SALE",
                action="CREATE_FACTURE",
                description=f"Création Facture N° {inv_number}",
                entity_type="INVOICE",
                entity_id=invoice.id,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self.db_session.add(audit)
        except Exception:
            pass
            
        self.db_session.commit()"""
    # Replace ONLY the first matching commit inside _validate_and_save
    # I'll just use a careful regex
    text = re.sub(r'(\s+)self\.db_session\.commit\(\)(.*?)QMessageBox\.question\(self, "Imprimer Facture"', 
                  r'\1' + audit_code.strip() + r'\2QMessageBox.question(self, "Imprimer Facture"', text, count=1, flags=re.DOTALL)

# Add creator column to history
old_hist = r'tbl\.setHorizontalHeaderLabels\(\["N° Facture", "Date", "Client", "Statut", "Actions"\]\)'
new_hist = r'tbl.setHorizontalHeaderLabels(["N° Facture", "Date", "Client", "Statut", "Créateur", "Actions"])'
text = re.sub(old_hist, new_hist, text)

# update column count
text = re.sub(r'tbl = QTableWidget\(len\(invoices\), 5\)', r'tbl = QTableWidget(len(invoices), 6)', text)

# update stretch
text = re.sub(r'for col in range\(4\):\n(\s+)tbl\.horizontalHeader\(\)\.setSectionResizeMode\(col, QHeaderView\.Stretch\)\n(\s+)tbl\.horizontalHeader\(\)\.setSectionResizeMode\(4, QHeaderView\.Fixed\)\n(\s+)tbl\.setColumnWidth\(4, 280\)',
              r'for col in range(5):\n\1tbl.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)\n\2tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)\n\3tbl.setColumnWidth(5, 280)', text)

# Insert the setItem for Createur and shift actions
# Old:
#             tbl.setItem(i, 3, QTableWidgetItem(inv.status or "—"))
#             
#             actions_widget = QWidget()
old_set_item = r'(tbl\.setItem\(i, 3, QTableWidgetItem\(inv\.status or "—"\)\)\s+)(actions_widget = QWidget\(\))'
new_set_item = r'\1creator_name = "—"\n            if inv.user:\n                creator_name = inv.user.full_name or inv.user.username\n            tbl.setItem(i, 4, QTableWidgetItem(creator_name))\n            \2'
text = re.sub(old_set_item, new_set_item, text)

# Fix action widgets column from 4 to 5
text = re.sub(r'tbl\.setCellWidget\(i, 4, actions_widget\)', r'tbl.setCellWidget(i, 5, actions_widget)', text)

with open('ui/pages/invoices_page.py', 'w', encoding='utf-8') as f:
    f.write(text)
