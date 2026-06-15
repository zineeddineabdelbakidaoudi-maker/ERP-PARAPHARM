import sys

file_path = 'ui/dialogs/supplier_document_creation_dialog.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add "Bon de Commande (BC)" to combo box options
content = content.replace(
    'self.doc_type_combo.addItems(["Bon de Réception (BR)", "Facture Fournisseur"])',
    'self.doc_type_combo.addItems(["Bon de Commande (BC)", "Bon de Réception (BR)", "Facture Fournisseur"])'
)

# 2. In _on_add_product, force tva to 0 if not Facture
content = content.replace(
    '        tva = self.tva_spin.value()\n',
    '        doc_type = self.doc_type_combo.currentText()\n        is_facture = "Facture" in doc_type\n        tva = self.tva_spin.value() if is_facture else 0.0\n'
)

# 3. Ensure saving logic handles "BC" correctly
# We need to import PurchaseOrder, PurchaseOrderItem
content = content.replace(
    'from app.models.purchase import Purchase, PurchaseItem',
    'from app.models.purchase import Purchase, PurchaseItem\nfrom app.models.purchase_order import PurchaseOrder, PurchaseOrderItem'
)

save_bc_logic = """
            if "Commande" in doc_type:
                # Create PurchaseOrder
                import uuid
                ref = self.ref_input.text() or f"BC-{uuid.uuid4().hex[:6].upper()}"
                bc = PurchaseOrder(
                    order_number=ref,
                    supplier_id=self.supplier.id,
                    order_date=self.date_input.date().toString("yyyy-MM-dd HH:mm:ss"),
                    status="PENDING",
                    subtotal=tht,
                    discount_amount=tht - sum(i["pu_ht"]*i["qty"] for i in self.items),
                    tax_total=0.0,
                    total_amount=tht,
                    notes=self.obs_input.toPlainText()
                )
                self.db_session.add(bc)
                self.db_session.flush()

                for i in self.items:
                    it = PurchaseOrderItem(
                        purchase_order_id=bc.id,
                        product_id=i["product_id"],
                        quantity=i["qty"],
                        unit_price=i["pu_ht"],
                        tax_rate=0.0,
                        discount_amount=i["pu_ht"]*i["qty"] - (i["pu_ht"]*i["qty"] * (1 - i["remise"]/100.0)),
                        line_total=i["total"]
                    )
                    self.db_session.add(it)

            elif "Réception" in doc_type:
"""

content = content.replace(
    '            if "Réception" in doc_type:',
    save_bc_logic
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("patched")
