from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Product Form Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QMessageBox,
    QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from app.models.product import Product, Category
from app.repositories.base_repository import BaseRepository
from app.services.product_service import ProductService
from app.core.database import get_session
from app.core.exceptions import ValidationError, DuplicateError


class ProductDialog(QDialog):
    """Dialog to create or edit a product."""

    def __init__(self, user, product: Product = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.product = product
        self.db_session = get_session()
        self.service = ProductService(self.db_session)
        
        self.setWindowTitle("Modifier le Produit" if product else "Nouveau Produit")
        self.setMinimumWidth(500)
        self._setup_ui()

        if self.product:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel(self.windowTitle())
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)

        # Fields
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan ou saisie manuelle")
        form_layout.addRow("Code-barres", self.barcode_input)

        self.name_input = QLineEdit()
        form_layout.addRow("Nom du produit *", self.name_input)

        self.cat_combo = SearchableComboBox()
        self.cat_combo.addItem("Général", None)
        
        cat_repo = BaseRepository(self.db_session, Category)
        cats = cat_repo.get_all()
        categories = cats.get("items", []) if isinstance(cats, dict) else cats
        for cat in categories:
            self.cat_combo.addItem(cat.name, cat.id)
            
        form_layout.addRow("Catégorie", self.cat_combo)

        self.tva_spin = QDoubleSpinBox()
        self.tva_spin.setMaximum(100.0)
        self.tva_spin.setValue(0.0)
        self.tva_spin.setSuffix(" %")
        form_layout.addRow("TVA", self.tva_spin)
        
        self.ug_spin = QDoubleSpinBox()
        self.ug_spin.setMaximum(100.0)
        self.ug_spin.setValue(0.0)
        self.ug_spin.setSuffix(" %")
        form_layout.addRow("UJ % Unité Gratuit", self.ug_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setMaximum(9999999.99)
        self.cost_spin.setSuffix(" DA")
        form_layout.addRow("Prix d'Achat", self.cost_spin)

        self.sell_spin = QDoubleSpinBox()
        self.sell_spin.setMaximum(9999999.99)
        self.sell_spin.setSuffix(" DA")
        form_layout.addRow("Prix de Vente (Client) *", self.sell_spin)

        self.ppt_spin = QDoubleSpinBox()
        self.ppt_spin.setMaximum(9999999.99)
        self.ppt_spin.setSuffix(" DA")
        form_layout.addRow("PPT (Prix Populaire)", self.ppt_spin)
        
        self.lot_input = QLineEdit()
        self.lot_input.setPlaceholderText("Numéro de Lot")
        form_layout.addRow("N° Lot", self.lot_input)
        
        from PySide6.QtWidgets import QDateEdit
        from PySide6.QtCore import QDate
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(QDate.currentDate().addYears(1))
        form_layout.addRow("Date de Péremption", self.expiry_input)

        self.min_stock_spin = QSpinBox()
        self.min_stock_spin.setMaximum(9999)
        self.min_stock_spin.setValue(10)
        form_layout.addRow("Stock Minimum", self.min_stock_spin)

        self.stock_spin = QDoubleSpinBox()
        self.stock_spin.setMaximum(999999.99)
        self.stock_spin.setValue(0.0)
        form_layout.addRow("Quantité en Stock", self.stock_spin)

        layout.addWidget(form_frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self.barcode_input.setText(self.product.barcode or "")
        self.name_input.setText(self.product.name)
        self.cost_spin.setValue(self.product.cost_price or 0.0)
        self.sell_spin.setValue(self.product.selling_price)
        self.ppt_spin.setValue(getattr(self.product, 'ppt_price', 0.0) or 0.0)
        self.lot_input.setText(getattr(self.product, 'lot_number', '') or '')
        if getattr(self.product, 'expiry_date', None):
            try:
                from PySide6.QtCore import QDate
                d = QDate.fromString(self.product.expiry_date, "yyyy-MM-dd")
                if d.isValid():
                    self.expiry_input.setDate(d)
            except Exception:
                pass
        self.min_stock_spin.setValue(self.product.min_stock_level)
        self.tva_spin.setValue(self.product.tax_rate or 0.0)
        self.ug_spin.setValue(getattr(self.product, 'ug_percent', 0.0) or 0.0)
        self.stock_spin.setValue(self.product.stock.quantity if self.product.stock else 0.0)

        if self.product.category_id:
            index = self.cat_combo.findData(self.product.category_id)
            if index >= 0:
                self.cat_combo.setCurrentIndex(index)

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom du produit est obligatoire.")
            return

        data = {
            "barcode": self.barcode_input.text().strip() or None,
            "name": name,
            "category_id": self.cat_combo.currentData(),
            "cost_price": self.cost_spin.value(),
            "selling_price": self.sell_spin.value(),
            "ppt_price": self.ppt_spin.value(),
            "lot_number": self.lot_input.text().strip(),
            "expiry_date": self.expiry_input.date().toString("yyyy-MM-dd"),
            "tax_rate": self.tva_spin.value(),
            "ug_percent": self.ug_spin.value(),
            "min_stock_level": self.min_stock_spin.value()
        }

        if self.product:
            data["stock_quantity"] = self.stock_spin.value()
        else:
            data["initial_stock"] = self.stock_spin.value()

        try:
            if self.product:
                self.service.update_product(self.product.id, data)
            else:
                self.service.create_product(data, self.user.id)
            self.accept()
        except (ValidationError, DuplicateError) as e:
            QMessageBox.warning(self, "Erreur de validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", str(e))
