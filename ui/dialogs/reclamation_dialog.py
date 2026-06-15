from ui.utils.widgets import SearchableComboBox
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QMessageBox,
    QFormLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.reclamation import Reclamation, ReclamationItem
from datetime import datetime

class ReclamationDialog(QDialog):
    def __init__(self, user, parent=None, is_client=True, reclamation=None):
        super().__init__(parent)
        self.user = user
        self.is_client = is_client
        self.reclamation = reclamation
        self.db_session = get_session()
        self.items = []
        
        title_prefix = "Modifier" if reclamation else "Nouveau"
        title_suffix = "Client" if is_client else "Fournisseur"
        self.setWindowTitle(f"{title_prefix} Bon de Réclamation {title_suffix}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form_layout = QFormLayout(form_frame)
        
        self.entity_combo = SearchableComboBox()
        form_layout.addRow("Entité" if self.is_client else "Fournisseur", self.entity_combo)
        
        self.reason_input = QTextEdit()
        self.reason_input.setMaximumHeight(60)
        form_layout.addRow("Raison de la réclamation *", self.reason_input)
        
        layout.addWidget(form_frame)
        
        # Product Entry
        entry_h = QHBoxLayout()
        entry_h.addWidget(QLabel("Produit:"))
        self.product_combo = SearchableComboBox()
        entry_h.addWidget(self.product_combo)
        
        entry_h.addWidget(QLabel("Qté:"))
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(99999)
        entry_h.addWidget(self.qty_spin)
        
        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self._on_add_item)
        entry_h.addWidget(add_btn)
        
        layout.addLayout(entry_h)
        
        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Produit", "Quantité", "Prix U.", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.total_lbl = QLabel("Total : 0.00 DA")
        self.total_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        btn_layout.addWidget(self.total_lbl)
        
        btn_layout.addStretch()
        
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        
        save = QPushButton("Enregistrer")
        save.setProperty("variant", "success")
        save.clicked.connect(self._on_save)
        btn_layout.addWidget(save)
        
        layout.addLayout(btn_layout)

    def _load_data(self):
        from app.models.product import Product
        prods = self.db_session.query(Product).all()
        self.product_combo.addItem("--- Choisir Produit ---", None)
        for p in prods:
            self.product_combo.addItem(f"{p.code} - {p.name}", p.id)
            
        self.entity_combo.clear()
        if self.is_client:
            from app.models.client import Client
            clients = self.db_session.query(Client).all()
            for c in clients:
                self.entity_combo.addItem(c.name, c.id)
        else:
            from app.models.supplier import Supplier
            suppliers = self.db_session.query(Supplier).all()
            for s in suppliers:
                self.entity_combo.addItem(s.name, s.id)
                
        if self.reclamation:
            self.reason_input.setText(self.reclamation.reason)
            idx = self.entity_combo.findData(self.reclamation.client_id if self.is_client else self.reclamation.supplier_id)
            if idx >= 0: self.entity_combo.setCurrentIndex(idx)
            
            for item in self.reclamation.items:
                self.items.append({
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total
                })
            self._refresh_table()

    def _on_add_item(self):
        pid = self.product_combo.currentData()
        if not pid: return
        
        from app.models.product import Product
        p = self.db_session.query(Product).get(pid)
        if not p: return
        
        qty = self.qty_spin.value()
        price = p.selling_price if self.is_client else p.cost_price
        total = qty * price
        
        self.items.append({
            "product_id": p.id,
            "product_name": p.name,
            "quantity": qty,
            "unit_price": price,
            "line_total": total
        })
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        tot = 0.0
        for item in self.items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(item["product_name"]))
            self.table.setItem(r, 1, QTableWidgetItem(str(item["quantity"])))
            self.table.setItem(r, 2, QTableWidgetItem(f"{item['unit_price']:.2f}"))
            self.table.setItem(r, 3, QTableWidgetItem(f"{item['line_total']:.2f}"))
            tot += item["line_total"]
            
        self.total_lbl.setText(f"Total : {tot:,.2f} DA".replace(",", " "))

    def _on_save(self):
        if not self.items:
            QMessageBox.warning(self, "Erreur", "Ajoutez au moins un produit.")
            return
            
        reason = self.reason_input.toPlainText().strip()
        if not reason:
            QMessageBox.warning(self, "Erreur", "Veuillez spécifier la raison.")
            return
            
        entity_id = self.entity_combo.currentData()
        if not entity_id:
            QMessageBox.warning(self, "Erreur", "Entité requise.")
            return

        is_client = self.is_client
        total = sum(i["line_total"] for i in self.items)
        
        if not self.reclamation:
            count = self.db_session.query(Reclamation).count() + 1
            rec_num = f"REC-{datetime.now().strftime('%Y%m%d')}-{count}"
            
            self.reclamation = Reclamation(
                reclamation_number=rec_num,
                client_id=entity_id if is_client else None,
                supplier_id=entity_id if not is_client else None,
                reason=reason,
                total_amount=total,
                created_by=self.user.id
            )
            self.db_session.add(self.reclamation)
            self.db_session.flush()
        else:
            self.reclamation.reason = reason
            self.reclamation.total_amount = total
            if is_client: self.reclamation.client_id = entity_id
            else: self.reclamation.supplier_id = entity_id
            
            self.db_session.query(ReclamationItem).filter(ReclamationItem.reclamation_id == self.reclamation.id).delete()
        
        for item in self.items:
            ri = ReclamationItem(
                reclamation_id=self.reclamation.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                line_total=item["line_total"]
            )
            self.db_session.add(ri)
            
        self.db_session.commit()
        QMessageBox.information(self, "Succès", "Réclamation enregistrée.")
        self.accept()
