from ui.utils.widgets import SearchableComboBox
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QMessageBox,
    QFormLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QGridLayout
)
from PySide6.QtCore import Qt, QDate
from app.services.sale_service import SaleService
from app.core.database import get_session
from app.core.exceptions import ValidationError
from app.constants import PaymentMethod

class ClientDocumentCreationDialog(QDialog):
    """Unified dialog to create a Sale (BL) or Invoice (Facture) directly from Client Fiche."""

    def __init__(self, user, client, parent=None):
        super().__init__(parent)
        self.user = user
        self.client = client
        self.db_session = get_session()
        self.sale_service = SaleService(self.db_session)
        
        self.items = []
        
        # Load default TVA
        from app.models.setting import Setting
        tva_setting = self.db_session.query(Setting).filter_by(key="default_tva").first()
        self.default_tva = float(tva_setting.value) if tva_setting else 19.0
        
        self.setWindowTitle(f"Nouveau Document - {client.name}")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        self.setWindowState(Qt.WindowMaximized)
        self._setup_ui()
        self._load_products()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        title = QLabel(f"Création de Document pour : {self.client.name} ({self.client.code})")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        from PySide6.QtWidgets import QComboBox
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type de document :"))
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems(["Bon de Livraison (BL)", "Facture (avec TVA)"])
        self.doc_type_combo.currentTextChanged.connect(self._on_doc_type_changed)
        type_layout.addWidget(self.doc_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Entry Form
        entry_frame = QFrame()
        entry_frame.setProperty("class", "card")
        grid = QGridLayout(entry_frame)
        
        grid.addWidget(QLabel("Produit *"), 0, 0)
        self.product_combo = SearchableComboBox()
        self.product_combo.currentIndexChanged.connect(self._on_product_selected)
        grid.addWidget(self.product_combo, 1, 0)
        
        grid.addWidget(QLabel("Désignation"), 0, 1)
        self.designation_input = QLineEdit()
        self.designation_input.setReadOnly(True)
        grid.addWidget(self.designation_input, 1, 1)
        
        grid.addWidget(QLabel("PPT"), 0, 2)
        self.ppt_spin = QDoubleSpinBox()
        self.ppt_spin.setMaximum(9999999)
        self.ppt_spin.setReadOnly(True)
        grid.addWidget(self.ppt_spin, 1, 2)
        
        grid.addWidget(QLabel("Prix Vente *"), 0, 3)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMaximum(9999999)
        grid.addWidget(self.price_spin, 1, 3)
        
        grid.addWidget(QLabel("Qté *"), 0, 4)
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMaximum(99999)
        self.qty_spin.setValue(1)
        self.qty_spin.valueChanged.connect(self._update_line_total)
        self.price_spin.valueChanged.connect(self._update_line_total)
        grid.addWidget(self.qty_spin, 1, 4)
        
        grid.addWidget(QLabel("Remise (%)"), 0, 5)
        self.remise_spin = QDoubleSpinBox()
        self.remise_spin.setMaximum(100)
        self.remise_spin.valueChanged.connect(self._update_line_total)
        grid.addWidget(self.remise_spin, 1, 5)
        
        grid.addWidget(QLabel("N° Lot"), 2, 0)
        self.lot_input = QLineEdit()
        grid.addWidget(self.lot_input, 3, 0)
        
        grid.addWidget(QLabel("Date Péremption"), 2, 1)
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(QDate.currentDate().addYears(1))
        grid.addWidget(self.expiry_input, 3, 1)
        
        grid.addWidget(QLabel("Total Ligne"), 2, 2)
        self.total_line_spin = QDoubleSpinBox()
        self.total_line_spin.setMaximum(99999999)
        self.total_line_spin.setReadOnly(True)
        grid.addWidget(self.total_line_spin, 3, 2)
        
        grid.addWidget(QLabel("Obs:"), 3, 2)
        self.obs_input = QLineEdit()
        grid.addWidget(self.obs_input, 3, 3)
        
        add_btn = QPushButton("Ajouter Ligne")
        add_btn.clicked.connect(self._on_add_item)
        add_btn.setMinimumHeight(35)
        grid.addWidget(add_btn, 3, 4, 1, 2)
        
        layout.addWidget(entry_frame)

        # Table
        self.table = QTableWidget()
        # Initialized dynamically in _on_doc_type_changed
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Totals
        totals_layout = QHBoxLayout()
        totals_layout.addStretch()
        
        totals_form = QFormLayout()
        
        self.subtotal_lbl = QLabel("0.00 DA")
        totals_form.addRow("Sous-total :", self.subtotal_lbl)
        
        self.tva_lbl = QLabel("0.00 DA")
        totals_form.addRow("TVA :", self.tva_lbl)
        
        self.net_lbl = QLabel("0.00 DA")
        self.net_lbl.setStyleSheet("font-weight: bold; font-size: 16px; color: #C0392B;")
        totals_form.addRow("Net à Payer :", self.net_lbl)
        
        totals_layout.addLayout(totals_form)
        layout.addLayout(totals_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Valider le Document")
        save_btn.setProperty("variant", "success")
        save_btn.clicked.connect(self._on_save)
        save_btn.setMinimumHeight(40)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        
        self._on_doc_type_changed(self.doc_type_combo.currentText())

    def _on_doc_type_changed(self, doc_type):
        is_facture = "Facture" in doc_type
        
        if is_facture:
            self.table.setColumnCount(12)
            self.table.setHorizontalHeaderLabels([
                "N°", "Réf.", "Désignation", "Qté", "UJ 🎁", "Prix U HT", 
                "TVA %", "Montant TVA", "Rem %", "Total TTC", "Obs", "Action"
            ])
            self.tva_lbl.parentWidget().show() if self.tva_lbl.parentWidget() else self.tva_lbl.show()
        else:
            self.table.setColumnCount(14)
            self.table.setHorizontalHeaderLabels([
                "N°", "Réf.", "Désignation", "N° Lot", "Exp.", "Qté", "UJ 🎁", 
                "Prix U HT", "Rem %", "Remise DA", "Total HT", "Obs", "Stock Actuel", "Action"
            ])
            self.tva_lbl.parentWidget().hide() if self.tva_lbl.parentWidget() else self.tva_lbl.hide()
            
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Désignation
            
        self._refresh_table()

    def _load_products(self):
        from app.models.product import Product
        self.product_combo.blockSignals(True)
        self.product_combo.addItem("--- Choisir un produit ---", None)
        products = self.db_session.query(Product).filter(Product.is_active == 1).order_by(Product.name).all()
        for p in products:
            self.product_combo.addItem(f"{p.code} - {p.name}", p.id)
        self.product_combo.blockSignals(False)

    def _on_product_selected(self):
        prod_id = self.product_combo.currentData()
        if not prod_id:
            return
        from app.models.product import Product
        p = self.db_session.query(Product).get(prod_id)
        if p:
            self.designation_input.setText(p.name)
            self.ppt_spin.setValue(getattr(p, 'ppt_price', 0.0) or 0.0)
            self.price_spin.setValue(p.selling_price)
            self.lot_input.setText(getattr(p, 'lot_number', '') or '')
            if getattr(p, 'expiry_date', None):
                try:
                    d = QDate.fromString(p.expiry_date, "yyyy-MM-dd")
                    if d.isValid():
                        self.expiry_input.setDate(d)
                except Exception:
                    pass
            self._update_line_total()

    def _update_line_total(self):
        qty = self.qty_spin.value()
        price = self.price_spin.value()
        remise_pct = self.remise_spin.value()
        
        sub = qty * price
        discount = sub * (remise_pct / 100.0)
        total = sub - discount
        self.total_line_spin.setValue(total)

    def _on_add_item(self):
        prod_id = self.product_combo.currentData()
        if not prod_id: return
        
        from app.models.product import Product
        p = self.db_session.query(Product).get(prod_id)
        if not p: return
        
        qty = self.qty_spin.value()
        if qty <= 0: return
        
        price = self.price_spin.value()
        remise_pct = self.remise_spin.value()
        
        sub = qty * price
        discount_amount = sub * (remise_pct / 100.0)
        line_total = sub - discount_amount
        
        product_tva = getattr(p, "tax_rate", 0.0) or 0.0
        tva_amount = line_total * (product_tva / 100.0)
        
        ug_pct = getattr(p, "ug_percent", 0.0) or 0.0
        uj_seuil = getattr(p, "uj_seuil", 0) or 0
        
        uj_qty = 0
        if uj_seuil == 0 or qty >= uj_seuil:
            uj_qty = int(qty * (ug_pct / 100.0))
        
        item = {
            "product_id": p.id,
            "product_code": p.code,
            "product_name": p.name,
            "ppt_price": self.ppt_spin.value(),
            "unit_price": price,
            "cost_price": p.cost_price,
            "quantity": qty,
            "uj_qty": uj_qty,
            "discount_pct": remise_pct,
            "discount_amount": discount_amount,
            "tax_rate": self.default_tva,
            "tax_amount": tva_amount,
            "line_total": line_total,
            "lot_number": self.lot_input.text(),
            "expiry_date": self.expiry_input.date().toString("yyyy-MM-dd"),
            "obs": self.obs_input.text(),
            "current_stock": p.stock.quantity if getattr(p, "stock", None) else 0.0
        }
        
        self.items.append(item)
        self._refresh_table()

        # Reset line inputs
        self.qty_spin.setValue(1)
        self.remise_spin.setValue(0)
        self.obs_input.clear()

    def _refresh_table(self):
        self.table.setRowCount(0)
        subtotal = 0.0
        total_tva = 0.0
        
        doc_type = self.doc_type_combo.currentText()
        is_facture = "Facture" in doc_type
        
        for idx, item in enumerate(self.items):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            from PySide6.QtGui import QColor
            qty_item = QTableWidgetItem(f"{item['quantity']:.2f}")
            qty_item.setBackground(QColor("#FFF9C4")) # Light Yellow
            uj_item = QTableWidgetItem(f"{item.get('uj_qty', 0)}")
            uj_item.setBackground(QColor("#FFE0B2")) # Light Amber
            total_item = QTableWidgetItem(f"{item['line_total']:.2f}")
            total_item.setBackground(QColor("#C8E6C9")) # Light Green

            if is_facture:
                self.table.setItem(row, 0, QTableWidgetItem(str(idx + 1)))
                self.table.setItem(row, 1, QTableWidgetItem(item["product_code"]))
                self.table.setItem(row, 2, QTableWidgetItem(item["product_name"]))
                self.table.setItem(row, 3, qty_item)
                self.table.setItem(row, 4, uj_item)
                self.table.setItem(row, 5, QTableWidgetItem(f"{item['unit_price']:.2f}"))
                self.table.setItem(row, 6, QTableWidgetItem(f"{item['tax_rate']:.2f}%"))
                self.table.setItem(row, 7, QTableWidgetItem(f"{item['tax_amount']:.2f}"))
                self.table.setItem(row, 8, QTableWidgetItem(f"{item['discount_pct']:.2f}%"))
                self.table.setItem(row, 9, total_item)
                self.table.setItem(row, 10, QTableWidgetItem(item.get("obs", "")))
                
                del_btn = QPushButton("🗑️")
                del_btn.clicked.connect(lambda checked, i=idx: self._on_delete_item(i))
                self.table.setCellWidget(row, 11, del_btn)
            else:
                self.table.setItem(row, 0, QTableWidgetItem(str(idx + 1)))
                self.table.setItem(row, 1, QTableWidgetItem(item["product_code"]))
                self.table.setItem(row, 2, QTableWidgetItem(item["product_name"]))
                self.table.setItem(row, 3, QTableWidgetItem(item["lot_number"]))
                self.table.setItem(row, 4, QTableWidgetItem(item["expiry_date"]))
                self.table.setItem(row, 5, qty_item)
                self.table.setItem(row, 6, uj_item)
                self.table.setItem(row, 7, QTableWidgetItem(f"{item['unit_price']:.2f}"))
                self.table.setItem(row, 8, QTableWidgetItem(f"{item['discount_pct']:.2f}%"))
                self.table.setItem(row, 9, QTableWidgetItem(f"{item['discount_amount']:.2f}"))
                self.table.setItem(row, 10, total_item)
                self.table.setItem(row, 11, QTableWidgetItem(item.get("obs", "")))
                self.table.setItem(row, 12, QTableWidgetItem(f"{item.get('current_stock', 0):.2f}"))
                
                del_btn = QPushButton("🗑️")
                del_btn.clicked.connect(lambda checked, i=idx: self._on_delete_item(i))
                self.table.setCellWidget(row, 13, del_btn)
            
            subtotal += item["line_total"]
            total_tva += item["tax_amount"] if is_facture else 0.0
            
        self.subtotal_lbl.setText(f"{subtotal:,.2f} DA".replace(",", " "))
        self.tva_lbl.setText(f"{total_tva:,.2f} DA".replace(",", " ") if is_facture else "0.00 DA")
        self.net_lbl.setText(f"{(subtotal + total_tva):,.2f} DA".replace(",", " "))

    def _on_delete_item(self, idx):
        if 0 <= idx < len(self.items):
            self.items.pop(idx)
            self._refresh_table()

    def _on_save(self):
        if not self.items:
            QMessageBox.warning(self, "Erreur", "Le document doit contenir au moins un article.")
            return

        doc_type = self.doc_type_combo.currentText()
        is_facture = "Facture" in doc_type

        subtotal = sum(i["line_total"] for i in self.items)
        tax_total = sum(i["tax_amount"] for i in self.items) if is_facture else 0.0
        net = subtotal + tax_total

        # 1. Create Sale (BL is the base for stock movement)
        sale_data = {
            "client_id": self.client.id,
            "subtotal": subtotal,
            "discount_amount": sum(i["discount_amount"] for i in self.items),
            "tax_total": tax_total,
            "total_amount": net,
            "paid_amount": 0.0,
            "payment_method": PaymentMethod.CREDIT.value,
            "items": self.items
        }

        try:
            # We bypass the strict debt creation if it's going to be an Invoice immediately,
            # or we let it create the Debt and then the Invoice absorbs it.
            sale = self.sale_service.process_sale(sale_data, self.user.id)
            
            # 2. If Facture, create Invoice
            if "Facture" in doc_type:
                from app.models.invoice import Invoice, InvoiceItem
                from datetime import datetime
                
                # Fetch next invoice number
                count = self.db_session.query(Invoice).count() + 1
                inv_num = f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{count}"
                
                invoice = Invoice(
                    invoice_number=inv_num,
                    client_id=self.client.id,
                    sale_id=sale.id,
                    subtotal=subtotal,
                    tax_total=tax_total,
                    discount_amount=sale_data["discount_amount"],
                    total_amount=net,
                    status="VALIDATED",
                    created_by=self.user.id
                )
                self.db_session.add(invoice)
                self.db_session.flush()
                
                for item in self.items:
                    inv_item = InvoiceItem(
                        invoice_id=invoice.id,
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        tax_rate=item["tax_rate"],
                        tax_amount=item["tax_amount"],
                        uj_qty=item.get("uj_qty", 0),
                        discount_amount=item["discount_amount"],
                        line_total=item["line_total"]
                    )
                    self.db_session.add(inv_item)
                
                # Re-map Debt from SALE to SALE_INVOICE
                from app.models.debt import Debt
                debt = self.db_session.query(Debt).filter_by(reference_type="SALE", reference_id=sale.id).first()
                if debt:
                    debt.reference_type = "SALE_INVOICE"
                    debt.reference_id = invoice.id
                    debt.total_amount = invoice.total_amount
                    debt.remaining_amount = invoice.total_amount
                    
                self.db_session.commit()
                QMessageBox.information(self, "Succès", "Facture générée avec succès.")
            else:
                QMessageBox.information(self, "Succès", "Bon de Livraison généré avec succès.")
                
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", f"Une erreur s'est produite lors de la sauvegarde : {str(e)}")
