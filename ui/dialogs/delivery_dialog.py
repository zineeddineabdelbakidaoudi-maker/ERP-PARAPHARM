from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Delivery Form Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QMessageBox,
    QFormLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from app.services.delivery_service import DeliveryService
from app.core.database import get_session
from app.core.exceptions import ValidationError

class DeliveryDialog(QDialog):
    """Dialog to create a new delivery note."""

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.service = DeliveryService(self.db_session)
        
        self.items = []  # List of dicts: {'product_id', 'product_name', 'quantity'}
        
        self.setWindowTitle("Nouveau Bon de Livraison")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setWindowState(Qt.WindowMaximized)
        self._setup_ui()
        self._load_clients()
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
        header_layout = QFormLayout(header_frame)
        
        self.client_combo = SearchableComboBox()
        self.client_combo.setMinimumWidth(250)
        header_layout.addRow("Client *", self.client_combo)
        
        self.address_input = QLineEdit()
        header_layout.addRow("Adresse de livraison", self.address_input)

        self.zone_combo = SearchableComboBox()
        self.zone_combo.addItems(["Centre-ville", "Nord", "Sud", "Est", "Ouest", "Hors-wilaya"])
        self.zone_combo.setEditable(True)
        header_layout.addRow("Zone", self.zone_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        header_layout.addRow("Date Prévue", self.date_edit)
        
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
        
        add_item_btn = QPushButton("Ajouter")
        add_item_btn.clicked.connect(self._on_add_item)
        entry_layout.addWidget(add_item_btn)
        
        layout.addWidget(entry_frame)

        # Items Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            "Produit", "Quantité", "Action"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Créer le Bon")
        save_btn.setProperty("variant", "success")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_clients(self):
        from app.repositories.client_supplier_repository import ClientRepository
        repo = ClientRepository(self.db_session)
        res = repo.get_all(include_deleted=False)
        clients = res.get("items", []) if isinstance(res, dict) else res
        
        for c in clients:
            self.client_combo.addItem(f"{c.code} - {c.name}", c.id)

    def _load_products(self):
        from app.repositories.product_repository import ProductRepository
        repo = ProductRepository(self.db_session)
        res = repo.get_all(include_deleted=False)
        products = res.get("items", []) if isinstance(res, dict) else res
        
        for p in products:
            self.product_combo.addItem(p.name, p.id)

    def _on_add_item(self):
        prod_id = self.product_combo.currentData()
        if not prod_id:
            return
            
        qty = self.qty_spin.value()
        
        from app.models.product import Product
        p = self.db_session.query(Product).get(prod_id)
        if p and (p.stock_quantity or 0) < qty:
            QMessageBox.warning(self, "Stock Insuffisant", f"Le stock actuel pour '{p.name}' est de {p.stock_quantity or 0}. Vous demandez {qty}.")
            return
        
        item = {
            "product_id": prod_id,
            "product_name": self.product_combo.currentText(),
            "quantity": qty
        }
        
        self.items.append(item)
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        
        for idx, item in enumerate(self.items):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(f"{item['quantity']:.2f}"))
            
            del_btn = QPushButton("🗑️")
            del_btn.setProperty("variant", "icon")
            del_btn.clicked.connect(lambda checked, i=idx: self._on_delete_item(i))
            self.table.setCellWidget(row, 2, del_btn)

    def _on_delete_item(self, idx):
        if 0 <= idx < len(self.items):
            self.items.pop(idx)
            self._refresh_table()

    def _on_save(self):
        client_id = self.client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un client.")
            return
            
        if not self.items:
            QMessageBox.warning(self, "Erreur", "La livraison doit contenir au moins un article.")
            return

        data = {
            "client_id": client_id,
            "address": self.address_input.text().strip() or None,
            "zone": self.zone_combo.currentText() or None,
            "scheduled_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "items": self.items
        }

        try:
            self.service.create_delivery(data, self.user.id)
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "Erreur de validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", str(e))
