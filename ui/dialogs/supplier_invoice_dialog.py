from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFormLayout, QDoubleSpinBox, QDateEdit, QComboBox
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.supplier_invoice import SupplierInvoice, SupplierInvoiceItem
from app.models.product import Product
from app.models.supplier import Supplier
from ui.utils.widgets import SearchableComboBox

class SupplierInvoiceDialog(QDialog):
    def __init__(self, user, invoice: SupplierInvoice = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.invoice = invoice
        self.db_session = get_session()
        self.items = []
        
        self.setWindowTitle("Facture Fournisseur" if invoice else "Nouvelle Facture Fournisseur")
        self.setMinimumSize(1000, 700)
        self._setup_ui()
        
        if invoice:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.supplier_combo = SearchableComboBox()
        for s in self.db_session.query(Supplier).all():
            self.supplier_combo.addItem(s.name, s.id)
        form.addRow("Fournisseur * :", self.supplier_combo)
        
        self.ref_input = QLineEdit()
        form.addRow("N° Facture Fournisseur :", self.ref_input)
        
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        form.addRow("Date Facture :", self.date_input)
        
        layout.addLayout(form)
        
        # Items entry (Grid)
        entry_layout = QGridLayout()
        
        self.product_combo = SearchableComboBox()
        self.product_combo.setMinimumWidth(200)
        self._load_products()
        
        entry_layout.addWidget(QLabel("Produit:"), 0, 0)
        entry_layout.addWidget(self.product_combo, 0, 1, 1, 3)
        
        self.lot_input = QLineEdit()
        self.lot_input.setPlaceholderText("N° Lot")
        entry_layout.addWidget(QLabel("Lot:"), 0, 4)
        entry_layout.addWidget(self.lot_input, 0, 5)
        
        self.exp_input = QDateEdit()
        self.exp_input.setCalendarPopup(True)
        self.exp_input.setDisplayFormat("MM/yyyy")
        self.exp_input.setDate(QDate.currentDate().addYears(1))
        entry_layout.addWidget(QLabel("Péremp.:"), 0, 6)
        entry_layout.addWidget(self.exp_input, 0, 7)
        
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMaximum(999999)
        self.qty_spin.setValue(1)
        entry_layout.addWidget(QLabel("Qté:"), 1, 0)
        entry_layout.addWidget(self.qty_spin, 1, 1)
        
        self.uj_pct_spin = QDoubleSpinBox()
        self.uj_pct_spin.setMaximum(100)
        self.uj_pct_spin.setToolTip("Pourcentage d'Unités Gratuites")
        entry_layout.addWidget(QLabel("UJ %:"), 1, 2)
        entry_layout.addWidget(self.uj_pct_spin, 1, 3)
        
        self.uj_spin = QDoubleSpinBox()
        self.uj_spin.setMaximum(999999)
        entry_layout.addWidget(QLabel("UJ Qté:"), 1, 4)
        entry_layout.addWidget(self.uj_spin, 1, 5)
        
        # Auto-calculate UJ Qté when Qté or UJ % changes
        self.qty_spin.valueChanged.connect(self._calc_uj_qty)
        self.uj_pct_spin.valueChanged.connect(self._calc_uj_qty)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMaximum(9999999)
        entry_layout.addWidget(QLabel("PU HT:"), 2, 0)
        entry_layout.addWidget(self.price_spin, 2, 1)
        
        self.tva_spin = QDoubleSpinBox()
        self.tva_spin.setMaximum(100)
        self.tva_spin.setValue(19)
        entry_layout.addWidget(QLabel("TVA %:"), 2, 2)
        entry_layout.addWidget(self.tva_spin, 2, 3)
        
        self.remise_spin = QDoubleSpinBox()
        self.remise_spin.setMaximum(100)
        entry_layout.addWidget(QLabel("Remise %:"), 2, 4)
        entry_layout.addWidget(self.remise_spin, 2, 5)
        
        self.ppt_spin = QDoubleSpinBox()
        self.ppt_spin.setMaximum(9999999)
        entry_layout.addWidget(QLabel("PPT:"), 2, 6)
        entry_layout.addWidget(self.ppt_spin, 2, 7)
        
        add_btn = QPushButton("Ajouter Ligne")
        add_btn.clicked.connect(self._on_add)
        entry_layout.addWidget(add_btn, 1, 6, 1, 2) # spanning 2 columns
        
        layout.addLayout(entry_layout)
        
        # Grid
        self.table = QTableWidget(0, 14)
        self.table.setHorizontalHeaderLabels([
            "N°", "Réf.", "Désignation", "Lot", "Péremp.", "Qté", "UJ 🎁", "Prix U HT", 
            "TVA %", "Montant TVA", "Rem %", "Total TTC", "PPT", "Action"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        
        # Totals
        self.lbl_ht = QLabel("HT: 0.00")
        self.lbl_tva = QLabel("TVA: 0.00")
        self.lbl_ttc = QLabel("TTC: 0.00")
        
        t_layout = QHBoxLayout()
        t_layout.addStretch()
        t_layout.addWidget(self.lbl_ht)
        t_layout.addWidget(self.lbl_tva)
        t_layout.addWidget(self.lbl_ttc)
        layout.addLayout(t_layout)
        
        # Buttons
        b_layout = QHBoxLayout()
        b_layout.addStretch()
        
        self.btn_print = QPushButton("🖨️ Imprimer")
        self.btn_print.clicked.connect(self._on_print)
        self.btn_print.setEnabled(self.invoice is not None)
        b_layout.addWidget(self.btn_print)
        
        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.clicked.connect(self._on_save)
        b_layout.addWidget(self.btn_save)
        
        layout.addLayout(b_layout)

    def _load_products(self):
        self.product_combo.clear()
        for p in self.db_session.query(Product).all():
            self.product_combo.addItem(p.code + " - " + p.name, p.id)

    def _add_new_product(self):
        from ui.dialogs.product_dialog import ProductDialog
        dlg = ProductDialog(self.user, parent=self)
        if dlg.exec():
            self._load_products()

    def _calc_uj_qty(self):
        qty = self.qty_spin.value()
        pct = self.uj_pct_spin.value()
        if qty > 0 and pct > 0:
            self.uj_spin.setValue(qty * (pct / 100.0))
        elif pct == 0:
            self.uj_spin.setValue(0)

    def _on_add(self):
        pid = self.product_combo.currentData()
        if not pid: return
        p = self.db_session.query(Product).get(pid)
        qty = self.qty_spin.value()
        uj = self.uj_spin.value()
        pu_ht = self.price_spin.value()
        tva = self.tva_spin.value()
        remise = self.remise_spin.value()
        ppt = self.ppt_spin.value()
        
        lot = self.lot_input.text()
        exp = self.exp_input.date().toString("MM/yyyy")
        
        sub_ht = pu_ht * qty
        remise_amt = sub_ht * (remise / 100.0)
        net_ht = sub_ht - remise_amt
        tva_amt = net_ht * (tva / 100.0)
        ttc = net_ht + tva_amt
        
        self.items.append({
            "product_id": pid,
            "code": p.code,
            "name": p.name,
            "lot": lot,
            "exp": exp,
            "qty": qty,
            "uj": uj,
            "pu_ht": pu_ht,
            "tva": tva,
            "tva_amt": tva_amt,
            "remise": remise,
            "ttc": ttc,
            "ppt": ppt
        })
        self._refresh()

    def _refresh(self):
        self.table.setRowCount(0)
        tht = 0
        ttva = 0
        tttc = 0
        
        for i, item in enumerate(self.items):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(item["code"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["name"]))
            self.table.setItem(row, 3, QTableWidgetItem(item.get("lot", "")))
            self.table.setItem(row, 4, QTableWidgetItem(item.get("exp", "")))
            self.table.setItem(row, 5, QTableWidgetItem(f"{item['qty']:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{item.get('uj', 0):.2f}"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{item['pu_ht']:.2f}"))
            self.table.setItem(row, 8, QTableWidgetItem(f"{item['tva']:.2f}%"))
            self.table.setItem(row, 9, QTableWidgetItem(f"{item['tva_amt']:.2f}"))
            self.table.setItem(row, 10, QTableWidgetItem(f"{item.get('remise', 0):.2f}%"))
            self.table.setItem(row, 11, QTableWidgetItem(f"{item['ttc']:.2f}"))
            self.table.setItem(row, 12, QTableWidgetItem(f"{item.get('ppt', 0):.2f}"))
            
            d_btn = QPushButton("🗑️")
            d_btn.clicked.connect(lambda _, idx=i: self._on_del(idx))
            self.table.setCellWidget(row, 13, d_btn)
            
            tht += (item["pu_ht"] * item["qty"]) - (item["pu_ht"] * item["qty"] * (item.get("remise", 0) / 100.0))
            ttva += item["tva_amt"]
            tttc += item["ttc"]
            
        self.lbl_ht.setText(f"HT: {tht:.2f}")
        self.lbl_tva.setText(f"TVA: {ttva:.2f}")
        self.lbl_ttc.setText(f"TTC: {tttc:.2f}")

    def _on_del(self, idx):
        self.items.pop(idx)
        self._refresh()

    def _on_save(self):
        if not self.items: return
        supplier_id = self.supplier_combo.currentData()
        
        tht = sum(i["pu_ht"] * i["qty"] for i in self.items)
        ttva = sum(i["tva_amt"] for i in self.items)
        tttc = sum(i["ttc"] for i in self.items)
        
        if not self.invoice:
            self.invoice = SupplierInvoice(
                supplier_id=supplier_id,
                our_reference=self.ref_input.text(),
                invoice_date=self.date_input.date().toString("yyyy-MM-dd"),
                total_ht=tht,
                total_tva=ttva,
                total_ttc=tttc,
                status="VALIDATED"
            )
            self.db_session.add(self.invoice)
            self.db_session.flush()
        else:
            self.invoice.supplier_id = supplier_id
            self.invoice.our_reference = self.ref_input.text()
            self.invoice.invoice_date = self.date_input.date().toString("yyyy-MM-dd")
            self.invoice.total_ht = tht
            self.invoice.total_tva = ttva
            self.invoice.total_ttc = tttc
            
            # clear old items
            self.db_session.query(SupplierInvoiceItem).filter_by(supplier_invoice_id=self.invoice.id).delete()
            
        for i in self.items:
            it = SupplierInvoiceItem(
                supplier_invoice_id=self.invoice.id,
                product_id=i["product_id"],
                quantity=i["qty"],
                unit_price_ht=i["pu_ht"],
                tva_rate=i["tva"],
                tva_amount=i["tva_amt"],
                total_ht=(i["pu_ht"] * i["qty"]) - (i["pu_ht"] * i["qty"] * (i.get("remise", 0) / 100.0)),
                total_ttc=i["ttc"],
                remise_percent=i.get("remise", 0.0),
                ppt=i.get("ppt", 0.0),
                uj_quantity=i.get("uj", 0.0),
                lot_number=i.get("lot", ""),
                expiry_date=i.get("exp", "")
            )
            self.db_session.add(it)
            
        self.db_session.commit()
        QMessageBox.information(self, "Succès", "Facture enregistrée.")
        self.accept()

    def _load_data(self):
        idx = self.supplier_combo.findData(self.invoice.supplier_id)
        if idx >= 0: self.supplier_combo.setCurrentIndex(idx)
        self.ref_input.setText(self.invoice.our_reference or "")
        d = QDate.fromString(self.invoice.invoice_date, "yyyy-MM-dd")
        if d.isValid(): self.date_input.setDate(d)
        
        for item in self.invoice.items:
            self.items.append({
                "product_id": item.product_id,
                "code": item.product.code,
                "name": item.product.name,
                "qty": item.quantity,
                "uj": 0.0, # Not saved to DB previously
                "pu_ht": item.unit_price_ht,
                "tva": item.tva_rate,
                "tva_amt": item.tva_amount,
                "remise": item.remise_percent,
                "ttc": item.total_ttc,
                "ppt": float(item.designation.replace("PPT: ", "")) if item.designation and "PPT: " in item.designation else 0.0
            })
        self._refresh()

    def _on_print(self):
        if not self.invoice: return
        import os
        import tempfile
        from app.utils.pdf_exporter import PDFExporter
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer Facture Fournisseur",
            f"Facture_Fournisseur_{self.invoice.id}.pdf", "PDF (*.pdf)"
        )
        if file_path:
            # We need export_supplier_invoice_to_pdf in PDFExporter
            try:
                PDFExporter.export_supplier_invoice_to_pdf(file_path, self.db_session, self.invoice.id)
                QMessageBox.information(self, "Succès", "Document généré avec succès.")
                os.startfile(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur de génération : {e}")
