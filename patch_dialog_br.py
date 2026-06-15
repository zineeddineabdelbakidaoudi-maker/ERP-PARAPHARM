import sys

file_path = 'ui/dialogs/supplier_document_creation_dialog.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update combobox
content = content.replace(
    'self.product_combo = SearchableComboBox()\n        self.product_combo.setMinimumWidth(200)',
    'self.product_combo = SearchableComboBox()\n        self.product_combo.allow_new = True\n        self.product_combo.setMinimumWidth(200)'
)

# 2. Add PU Vente (Row 3)
pu_vente_ui = """
        self.vente_spin = QDoubleSpinBox()
        self.vente_spin.setMaximum(9999999)
        entry_layout.addWidget(QLabel("PU Vente:"), 3, 0)
        entry_layout.addWidget(self.vente_spin, 3, 1)

        add_btn = QPushButton("Ajouter Ligne")
        add_btn.clicked.connect(self._on_add)
        entry_layout.addWidget(add_btn, 3, 6, 1, 2)
"""
content = content.replace(
    '        add_btn = QPushButton("Ajouter Ligne")\n        add_btn.clicked.connect(self._on_add)\n        entry_layout.addWidget(add_btn, 1, 6, 1, 2)',
    pu_vente_ui
)

# 3. Update Table Columns (15 columns now)
content = content.replace(
    'self.table = QTableWidget(0, 14)',
    'self.table = QTableWidget(0, 15)'
)
content = content.replace(
    '"Total TTC", "PPT", "Action"',
    '"Total TTC", "PU Vente", "PPT", "Action"'
)

# 4. Update _on_add
new_on_add = """    def _on_add(self):
        pid = self.product_combo.currentData()
        text = self.product_combo.currentText().strip()
        
        if not text:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner ou saisir un produit.")
            return

        qty = self.qty_spin.value()
        if qty <= 0: return

        pu_ht = self.price_spin.value()
        pu_vente = self.vente_spin.value()
        doc_type = self.doc_type_combo.currentText()
        is_facture = "Facture" in doc_type
        tva = self.tva_spin.value() if is_facture else 0.0
        remise = self.remise_spin.value()
        ppt = self.ppt_spin.value()
        
        if not pid:
            # Dynamic creation of Product!
            import uuid
            code = f"PROD-{uuid.uuid4().hex[:6].upper()}"
            new_prod = Product(
                code=code,
                name=text,
                cost_price=pu_ht,
                selling_price=pu_vente if pu_vente > 0 else (pu_ht * 1.3),
                tax_rate=tva,
                ppt_price=ppt
            )
            self.db_session.add(new_prod)
            self.db_session.flush()
            pid = new_prod.id
            self._load_products()
            # Find and select it
            idx = self.product_combo.findData(pid)
            if idx >= 0:
                self.product_combo.setCurrentIndex(idx)
        
        p = self.db_session.query(Product).get(pid)
        
        uj = self.uj_spin.value()
"""
content = content.replace(
"""    def _on_add(self):
        pid = self.product_combo.currentData()
        if not pid: return
        p = self.db_session.query(Product).get(pid)
        qty = self.qty_spin.value()
        if qty <= 0: return
        uj = self.uj_spin.value()
        pu_ht = self.price_spin.value()
        doc_type = self.doc_type_combo.currentText()
        is_facture = "Facture" in doc_type
        tva = self.tva_spin.value() if is_facture else 0.0
        remise = self.remise_spin.value()
        ppt = self.ppt_spin.value()""",
    new_on_add
)

# 5. Update items dict
content = content.replace(
    '"ppt": ppt\n        })',
    '"ppt": ppt,\n            "pu_vente": pu_vente\n        })'
)

# 6. Update _refresh() to set pu_vente in the new column
content = content.replace(
    'self.table.setItem(row, 12, QTableWidgetItem(f"{item.get(\'ppt\', 0):.2f}"))',
    'self.table.setItem(row, 12, QTableWidgetItem(f"{item.get(\'pu_vente\', 0):.2f}"))\n            self.table.setItem(row, 13, QTableWidgetItem(f"{item.get(\'ppt\', 0):.2f}"))'
)

content = content.replace(
    'self.table.setCellWidget(row, 13, d_btn)',
    'self.table.setCellWidget(row, 14, d_btn)'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("patched")
