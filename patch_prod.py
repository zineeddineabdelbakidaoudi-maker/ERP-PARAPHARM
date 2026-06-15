import re

with open('ui/pages/products_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add AuditLog for Save product
if 'from app.models.setting import AuditLog' not in text:
    text = text.replace('from app.models.product import Product', 'from app.models.product import Product\nfrom app.models.setting import AuditLog')

audit_save = """        self.db_session.commit()
        try:
            from datetime import datetime
            action = "UPDATE_PRODUCT" if product_id else "CREATE_PRODUCT"
            audit = AuditLog(
                user_id=self.user.id,
                module="PRODUCT",
                action=action,
                description=f"{'Modification' if product_id else 'Création'} Produit {product.code} - {product.name}",
                entity_type="PRODUCT",
                entity_id=product.id,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self.db_session.add(audit)
            self.db_session.commit()
        except Exception:
            self.db_session.rollback()"""

text = re.sub(r'(\s+)self\.db_session\.commit\(\)(.*?)QMessageBox\.information\(self, "Succès", "Produit enregistré avec succès."\)',
              r'\1' + audit_save.strip() + r'\2QMessageBox.information(self, "Succès", "Produit enregistré avec succès.")', text, count=1, flags=re.DOTALL)

# Add AuditLog for Delete product
audit_del = """            self.db_session.commit()
            try:
                from datetime import datetime
                audit = AuditLog(
                    user_id=self.user.id,
                    module="PRODUCT",
                    action="DELETE_PRODUCT",
                    description=f"Suppression Produit {prod.code} - {prod.name}",
                    entity_type="PRODUCT",
                    entity_id=prod.id,
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                self.db_session.add(audit)
                self.db_session.commit()
            except Exception:
                self.db_session.rollback()"""

text = re.sub(r'(\s+)self\.db_session\.commit\(\)(.*?)QMessageBox\.information\(self, "Succès", "Produit supprimé"\)',
              r'\1' + audit_del.strip() + r'\2QMessageBox.information(self, "Succès", "Produit supprimé")', text, count=1, flags=re.DOTALL)

with open('ui/pages/products_page.py', 'w', encoding='utf-8') as f:
    f.write(text)
