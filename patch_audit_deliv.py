import re

with open('ui/pages/deliveries_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add import if missing
if 'from app.models.setting import AuditLog' not in text:
    text = text.replace('from app.models.sale import Sale', 'from app.models.sale import Sale\nfrom app.models.setting import AuditLog')

# Insert AuditLog when saving
audit_log = """        self.db_session.add(new_debt)

        # Record Audit Log
        from datetime import datetime
        audit = AuditLog(
            user_id=self.user.id,
            module="SALE",
            action="CREATE_BL",
            description=f"Création BL N° {bl_number} (Client: {self.selected_client.name if self.selected_client else ''})",
            entity_type="SALE",
            entity_id=sale.id,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.db_session.add(audit)

        self.db_session.commit()"""

text = text.replace('        self.db_session.add(new_debt)\n        self.db_session.commit()', audit_log)

with open('ui/pages/deliveries_page.py', 'w', encoding='utf-8') as f:
    f.write(text)
