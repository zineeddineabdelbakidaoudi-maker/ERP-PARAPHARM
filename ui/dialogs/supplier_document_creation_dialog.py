from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFormLayout, QDoubleSpinBox, QDateEdit, QComboBox
)
from PySide6.QtCore import Qt, QDate, Signal
from app.core.database import get_session
from app.models.supplier_invoice import SupplierInvoice, SupplierInvoiceItem
from app.models.purchase import Purchase, PurchaseItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.product import Product
from app.models.debt import Debt
from ui.utils.widgets import SearchableComboBox
import datetime

class SupplierDocumentCreationDialog(QWidget):
    accepted = Signal()
    rejected = Signal()

    def __init__(self, user, supplier, parent=None):
        super().__init__(parent)
        self.user = user
        self.supplier = supplier
        self.db_session = get_session()
        self.items = []
        
        self.setMinimumSize(900, 600)
        self._setup_ui()
        self._load_products()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        title = QLabel(f"Création de Document pour : {self.supplier.name} ({self.supplier.code})")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type de document :"))
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems(["Bon de Commande (BC)", "Bon de Réception (BR)", "Facture Fournisseur"])
        self.doc_type_combo.currentTextChanged.connect(self._refresh)
        type_layout.addWidget(self.doc_type_combo)
        
        type_layout.addWidget(QLabel("N° Document / Réf :"))
        self.ref_input = QLineEdit()
        type_layout.addWidget(self.ref_input)
        
        type_layout.addWidget(QLabel("Date :"))
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        type_layout.addWidget(self.date_input)
        
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Items entry (Grid)
        entry_layout = QGridLayout()
        
        self.product_combo = SearchableComboBox()
        self.product_combo.allow_new = True
        self.product_combo.setMinimumWidth(200)
        
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
        

        self.vente_spin = QDoubleSpinBox()
        self.vente_spin.setMaximum(9999999)
        entry_layout.addWidget(QLabel("PU Vente:"), 3, 0)
        entry_layout.addWidget(self.vente_spin, 3, 1)

        self.product_combo.currentIndexChanged.connect(self._on_product_selected)

        add_btn = QPushButton("Ajouter Ligne")
        add_btn.clicked.connect(self._on_add)
        entry_layout.addWidget(add_btn, 3, 6, 1, 2)

        
        layout.addLayout(entry_layout)
        
        # Grid
        self.table = QTableWidget(0, 15)
        self.table.setHorizontalHeaderLabels([
            "N°", "Réf.", "Désignation", "Lot", "Péremp.", "Qté", "UJ 🎁", "Prix U HT", 
            "TVA %", "Montant TVA", "Rem %", "Total TTC", "PU Vente", "PPT", "Action"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        
        # Totals
        self.lbl_ht = QLabel("HT: 0.00")
        self.lbl_ht.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.lbl_tva = QLabel("TVA: 0.00")
        self.lbl_tva.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.lbl_ttc = QLabel("TTC: 0.00")
        self.lbl_ttc.setStyleSheet("font-size: 18px; font-weight: bold; color: #D35400;")
        
        t_layout = QHBoxLayout()
        t_layout.addStretch()
        t_layout.addWidget(self.lbl_ht)
        t_layout.addSpacing(20)
        t_layout.addWidget(self.lbl_tva)
        t_layout.addSpacing(20)
        t_layout.addWidget(self.lbl_ttc)
        layout.addLayout(t_layout)
        
        # Buttons
        b_layout = QHBoxLayout()
        b_layout.addStretch()
        
        self.btn_cancel = QPushButton("Retour à la liste")
        self.btn_cancel.clicked.connect(self.rejected.emit)
        b_layout.addWidget(self.btn_cancel)
        
        self.btn_save = QPushButton("Enregistrer et Valider")
        self.btn_save.setProperty("variant", "primary")
        self.btn_save.clicked.connect(self._on_save)
        b_layout.addWidget(self.btn_save)
        
        layout.addLayout(b_layout)

    def _load_products(self):
        self.product_combo.clear()
        for p in self.db_session.query(Product).all():
            self.product_combo.addItem(p.code + " - " + p.name, p.id)

    def _on_product_selected(self, index):
        if index < 0:
            return
        pid = self.product_combo.itemData(index)
        if pid:
            p = self.db_session.query(Product).get(pid)
            if p:
                self.price_spin.setValue(p.cost_price or 0.0)
                self.vente_spin.setValue(p.selling_price or 0.0)
                if hasattr(self, 'tva_spin'):
                    self.tva_spin.setValue(p.tax_rate or 19.0)
                if hasattr(self, 'ppt_spin'):
                    self.ppt_spin.setValue(p.ppt_price or 0.0)

    def _calc_uj_qty(self):
        qty = self.qty_spin.value()
        pct = self.uj_pct_spin.value()
        if qty > 0 and pct > 0:
            self.uj_spin.setValue(qty * (pct / 100.0))
        elif pct == 0:
            self.uj_spin.setValue(0)

    def _on_add(self):
        text = self.product_combo.currentText().strip()
        idx = self.product_combo.findText(text, Qt.MatchFixedString)
        if idx < 0:
            # Maybe they just typed a part of the name but didn't select
            idx = self.product_combo.findText(text, Qt.MatchContains)
            
        if idx >= 0:
            pid = self.product_combo.itemData(idx)
        else:
            pid = None
        
        if not text:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner ou saisir un produit.")
            return

        qty = self.qty_spin.value()
        if qty <= 0: return

        pu_ht = self.price_spin.value()
        pu_vente = self.vente_spin.value()
        doc_type = self.doc_type_combo.currentText()
        is_facture = "Facture" in doc_type
        tva = self.tva_spin.value()
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

        
        lot = self.lot_input.text()
        exp = self.exp_input.date().toString("MM/yyyy")
        
        sub_ht = pu_ht * qty
        remise_amt = sub_ht * (remise / 100.0)
        net_ht = sub_ht - remise_amt
        tva_amt = net_ht * (tva / 100.0) if is_facture else 0.0
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
            "ppt": ppt,
            "pu_vente": pu_vente
        })
        self._refresh()

        self.qty_spin.setValue(1)
        self.remise_spin.setValue(0)
        self.lot_input.clear()

    def _refresh(self):
        is_facture = "Facture" in self.doc_type_combo.currentText()
        if hasattr(self, 'tva_spin'):
            pass #self.tva_spin.setVisible(is_facture)
        if hasattr(self, 'lbl_tva'):
            pass #self.lbl_tva.setVisible(is_facture)
        self.table.setRowCount(0)
        tht = 0
        ttva = 0
        tttc = 0
        
        is_facture = "Facture" in self.doc_type_combo.currentText()
        
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
            
            # If it's a BR, TVA is technically still recorded, but TTC calculation can vary
            # However, users enter TVA anyway
            self.table.setItem(row, 8, QTableWidgetItem(f"{item['tva']:.2f}%"))
            self.table.setItem(row, 9, QTableWidgetItem(f"{item['tva_amt']:.2f}"))
            self.table.setItem(row, 10, QTableWidgetItem(f"{item.get('remise', 0):.2f}%"))
            self.table.setItem(row, 11, QTableWidgetItem(f"{item['ttc']:.2f}"))
            self.table.setItem(row, 12, QTableWidgetItem(f"{item.get('pu_vente', 0):.2f}"))
            self.table.setItem(row, 13, QTableWidgetItem(f"{item.get('ppt', 0):.2f}"))
            
            d_btn = QPushButton("🗑️")
            d_btn.clicked.connect(lambda _, idx=i: self._on_del(idx))
            self.table.setCellWidget(row, 14, d_btn)
            
            net_ht = (item["pu_ht"] * item["qty"]) - (item["pu_ht"] * item["qty"] * (item.get("remise", 0) / 100.0))
            tht += net_ht
            if is_facture:
                ttva += item["tva_amt"]
                tttc += item["ttc"]
            else:
                # Some suppliers don't count TVA in BR totals unless it's a Facture, 
                # but let's just show TTC if they input TVA.
                ttva += item["tva_amt"]
                tttc += item["ttc"]
            
        self.lbl_ht.setText(f"HT: {tht:,.2f} DA".replace(",", " "))
        self.lbl_tva.setText(f"TVA: {ttva:,.2f} DA".replace(",", " "))
        self.lbl_ttc.setText(f"TTC: {tttc:,.2f} DA".replace(",", " "))

    def _on_del(self, idx):
        self.items.pop(idx)
        self._refresh()

    def _on_save(self):
        if not self.items: 
            QMessageBox.warning(self, "Erreur", "Veuillez ajouter au moins un produit.")
            return
            
        doc_type = self.doc_type_combo.currentText()
        is_facture = "Facture" in doc_type
        
        tht = 0
        ttva = 0
        tttc = 0
        for i in self.items:
            net_ht = (i["pu_ht"] * i["qty"]) - (i["pu_ht"] * i["qty"] * (i.get("remise", 0) / 100.0))
            tht += net_ht
            ttva += i["tva_amt"]
            tttc += i["ttc"]


        try:
            # Update product details
            for i in self.items:
                p = self.db_session.query(Product).get(i["product_id"])
                if p:
                    # Remove PUMP as requested by user - directly overwrite prices
                    p.cost_price = i["pu_ht"]
                    p.selling_price = i.get("pu_vente", p.selling_price)
                    p.tax_rate = i["tva"]
                    p.ppt_price = i.get("ppt", p.ppt_price)
            self.db_session.flush()

            if is_facture:

                # Create Facture Fournisseur
                inv = SupplierInvoice(
                    supplier_id=self.supplier.id,
                    our_reference=self.ref_input.text(),
                    invoice_date=self.date_input.date().toString("yyyy-MM-dd"),
                    total_ht=tht,
                    total_tva=ttva,
                    total_ttc=tttc,
                    status="VALIDATED"
                )
                self.db_session.add(inv)
                self.db_session.flush()
                
                for i in self.items:
                    it = SupplierInvoiceItem(
                        supplier_invoice_id=inv.id,
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
                    
                # Create Debt for Supplier
                debt = Debt(
                    entity_type="SUPPLIER",
                    entity_id=self.supplier.id,
                    reference_type="SUPPLIER_INVOICE",
                    reference_id=inv.id,
                    total_amount=tttc,
                    remaining_amount=tttc,
                    due_date=self.date_input.date().toString("yyyy-MM-dd")
                )
                self.db_session.add(debt)
                
            elif "Commande" in doc_type:
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
                    notes=""
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
                        line_total=i["ttc"]
                    )
                    self.db_session.add(it)
                
            else:
                # Create Bon de Réception (Purchase)
                import uuid
                ref = self.ref_input.text() or f"BR-{uuid.uuid4().hex[:6].upper()}"
                purch = Purchase(
                    purchase_number=ref,
                    supplier_id=self.supplier.id,
                    purchase_date=self.date_input.date().toString("yyyy-MM-dd HH:mm:ss"),
                    status="RECEIVED",
                    subtotal=tht,
                    discount_amount=tht - sum(i["pu_ht"]*i["qty"] for i in self.items),
                    tax_total=ttva,
                    total_amount=tttc,
                    created_by=self.user.id
                )
                self.db_session.add(purch)
                self.db_session.flush()
                
                for i in self.items:
                    net_ht = (i["pu_ht"] * i["qty"]) - (i["pu_ht"] * i["qty"] * (i.get("remise", 0) / 100.0))
                    it = PurchaseItem(
                        purchase_id=purch.id,
                        product_id=i["product_id"],
                        ordered_qty=i["qty"],
                        received_qty=i["qty"],
                        unit_cost=i["pu_ht"],
                        tva_rate=i["tva"],
                        tva_amount=i["tva_amt"],
                        remise_percent=i.get("remise", 0.0),
                        ppt=i.get("ppt", 0.0),
                        uj_quantity=i.get("uj", 0.0),
                        line_total=i["ttc"],
                        batch_number=i.get("lot", ""),
                        expiry_date=i.get("exp", "")
                    )
                    self.db_session.add(it)
                    
                # Update Stock
                for i in self.items:
                    from app.services.stock_service import StockService
                    from app.constants import MovementType
                    stock_service = StockService(self.db_session)
                    stock_service.record_movement(
                        product_id=i["product_id"],
                        movement_type=MovementType.PURCHASE_IN,
                        quantity=i["qty"],
                        user_id=self.user.id,
                        reference_type="PURCHASE",
                        reference_id=purch.id,
                        unit_cost=i["pu_ht"],
                        batch_number=i.get("lot", ""),
                        expiry_date=i.get("exp", "")
                    )
                
                # Debt
                debt = Debt(
                    entity_type="SUPPLIER",
                    entity_id=self.supplier.id,
                    reference_type="PURCHASE",
                    reference_id=purch.id,
                    total_amount=tttc,
                    remaining_amount=tttc,
                    due_date=self.date_input.date().toString("yyyy-MM-dd")
                )
                self.db_session.add(debt)

            self.db_session.commit()
            
            # Print Prompt
            reply = QMessageBox.question(
                self, "Imprimer", f"{doc_type} enregistré avec succès.\nVoulez-vous l'imprimer ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                from app.utils.pdf_exporter import PDFExporter
                from PySide6.QtWidgets import QFileDialog
                import os
                
                doc_name = "Facture" if is_facture else ("BC" if "Commande" in doc_type else "BR")
                doc_id = inv.id if is_facture else (bc.id if "Commande" in doc_type else purch.id)
                ref_str = self.ref_input.text() or f"{doc_name}-{doc_id}"
                
                d = QFileDialog.getSaveFileName(self, "Enregistrer PDF", f"{doc_name}_{ref_str}.pdf", "PDF (*.pdf)")
                if d[0]:
                    try:
                        if is_facture:
                            PDFExporter.export_supplier_invoice_to_pdf(d[0], self.db_session, doc_id)
                        else:
                            # Use a generic purchase exporter for both BR and BC
                            PDFExporter.export_purchase_to_pdf(d[0], self.db_session, doc_id, is_order=("Commande" in doc_type))
                        os.startfile(d[0])
                    except Exception as e:
                        QMessageBox.warning(self, "Erreur Impression", f"Impossible de générer le PDF: {e}")

            self.accepted.emit()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
