from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Purchase Form Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QMessageBox,
    QFormLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from app.models.purchase import Purchase
from app.services.purchase_service import PurchaseService
from app.core.database import get_session
from app.core.exceptions import ValidationError

class PurchaseDialog(QDialog):
    """Dialog to create a new purchase order."""

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.service = PurchaseService(self.db_session)
        
        self.items = []  # List of dicts: {'product_id', 'product_name', 'ordered_qty', 'unit_cost', 'line_total'}
        
        self.setWindowTitle("Nouvelle Commande d'Achat")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self._setup_ui()
        self._load_suppliers()
        self._load_products()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel(self.windowTitle())
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        # Header info
        header_frame = QFrame()
        header_frame.setProperty("class", "card")
        header_layout = QHBoxLayout(header_frame)
        
        self.supplier_combo = SearchableComboBox()
        self.supplier_combo.setMinimumWidth(250)
        header_layout.addWidget(QLabel("Fournisseur *:"))
        header_layout.addWidget(self.supplier_combo)
        
        header_layout.addStretch()
        
        layout.addWidget(header_frame)

        # Item entry
        entry_frame = QFrame()
        entry_frame.setProperty("class", "card")
        entry_layout = QHBoxLayout(entry_frame)
        
        self.product_combo = SearchableComboBox()
        self.product_combo.setMinimumWidth(250)
        entry_layout.addWidget(QLabel("Produit:"))
        entry_layout.addWidget(self.product_combo)
        
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(99999)
        self.qty_spin.setValue(1)
        entry_layout.addWidget(QLabel("Qté:"))
        entry_layout.addWidget(self.qty_spin)
        
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setMaximum(999999.99)
        entry_layout.addWidget(QLabel("Prix Unitaire:"))
        entry_layout.addWidget(self.cost_spin)
        
        add_item_btn = QPushButton("Ajouter")
        add_item_btn.clicked.connect(self._on_add_item)
        entry_layout.addWidget(add_item_btn)
        
        layout.addWidget(entry_frame)

        # Items Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Produit", "Quantité", "Prix Unitaire", "Total Ligne", "Action"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        # Totals
        totals_layout = QHBoxLayout()
        totals_layout.addStretch()
        self.total_label = QLabel("Total: 0.00 DA")
        self.total_label.setProperty("class", "totalLabel")
        totals_layout.addWidget(self.total_label)
        layout.addLayout(totals_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Créer la Commande")
        save_btn.setProperty("variant", "success")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_suppliers(self):
        from app.repositories.client_supplier_repository import SupplierRepository
        repo = SupplierRepository(self.db_session)
        res = repo.get_all(include_deleted=False)
        suppliers = res.get("items", []) if isinstance(res, dict) else res
        
        for s in suppliers:
            self.supplier_combo.addItem(f"{s.code} - {s.name}", s.id)

    def _load_products(self):
        from app.repositories.product_repository import ProductRepository
        repo = ProductRepository(self.db_session)
        res = repo.get_all(include_deleted=False)
        products = res.get("items", []) if isinstance(res, dict) else res
        
        for p in products:
            self.product_combo.addItem(p.name, {"id": p.id, "cost": p.cost_price})
            
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        if self.product_combo.count() > 0:
            self._on_product_changed()

    def _on_product_changed(self):
        data = self.product_combo.currentData()
        if data:
            self.cost_spin.setValue(data["cost"] or 0.0)

    def _on_add_item(self):
        prod_data = self.product_combo.currentData()
        if not prod_data:
            return
            
        qty = self.qty_spin.value()
        cost = self.cost_spin.value()
        line_total = qty * cost
        
        item = {
            "product_id": prod_data["id"],
            "product_name": self.product_combo.currentText(),
            "ordered_qty": qty,
            "unit_cost": cost,
            "line_total": line_total
        }
        
        self.items.append(item)
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        total = 0.0
        
        for idx, item in enumerate(self.items):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(f"{item['ordered_qty']:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{item['unit_cost']:.2f} DA"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{item['line_total']:.2f} DA"))
            
            del_btn = QPushButton("🗑️")
            del_btn.setProperty("variant", "icon")
            del_btn.clicked.connect(lambda checked, i=idx: self._on_delete_item(i))
            self.table.setCellWidget(row, 4, del_btn)
            
            total += item["line_total"]
            
        self.total_label.setText(f"Total: {total:.2f} DA")

    def _on_delete_item(self, idx):
        if 0 <= idx < len(self.items):
            self.items.pop(idx)
            self._refresh_table()

    def _on_save(self):
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un fournisseur.")
            return
            
        if not self.items:
            QMessageBox.warning(self, "Erreur", "La commande doit contenir au moins un article.")
            return

        total = sum(item["line_total"] for item in self.items)
        
        data = {
            "supplier_id": supplier_id,
            "subtotal": total,
            "total_amount": total,
            "items": self.items
        }

        try:
            self.service.create_purchase(data, self.user.id)
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "Erreur de validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", str(e))
