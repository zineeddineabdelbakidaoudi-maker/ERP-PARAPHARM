from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Stock Adjustment Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QMessageBox,
    QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from app.models.product import Product
from app.services.stock_service import StockService
from app.core.database import get_session
from app.constants import MovementType

class StockAdjustDialog(QDialog):
    """Dialog to manually adjust stock for a specific product."""

    def __init__(self, user, product: Product, parent=None):
        super().__init__(parent)
        self.user = user
        self.product = product
        self.db_session = get_session()
        self.service = StockService(self.db_session)
        
        self.setWindowTitle("Ajustement de Stock")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel(f"Ajuster: {self.product.name}")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)

        # Current stock info (read-only)
        current_stock = self.product.stock.quantity if self.product.stock else 0.0
        current_stock_label = QLabel(f"<b>{current_stock:.2f}</b> unités")
        form_layout.addRow("Stock Actuel", current_stock_label)

        # Type of adjustment
        self.type_combo = SearchableComboBox()
        self.type_combo.addItem("Ajout (+)", "ADD")
        self.type_combo.addItem("Retrait (-)", "REMOVE")
        form_layout.addRow("Type d'Ajustement", self.type_combo)

        # Quantity
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMinimum(0.01)
        self.qty_spin.setMaximum(99999.99)
        self.qty_spin.setValue(1.0)
        form_layout.addRow("Quantité", self.qty_spin)

        # Reason / Notes
        self.reason_combo = SearchableComboBox()
        self.reason_combo.addItems([
            "Correction d'inventaire",
            "Produit expiré",
            "Produit endommagé / Perte",
            "Retour fournisseur",
            "Autre"
        ])
        form_layout.addRow("Raison", self.reason_combo)
        
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Détails supplémentaires...")
        form_layout.addRow("Notes", self.notes_input)

        layout.addWidget(form_frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Valider")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        qty = self.qty_spin.value()
        is_remove = self.type_combo.currentData() == "REMOVE"
        
        if is_remove:
            qty = -qty
            
        reason = self.reason_combo.currentText()
        notes = self.notes_input.text().strip()
        full_notes = f"{reason} - {notes}" if notes else reason

        try:
            self.service.record_movement(
                product_id=self.product.id,
                movement_type=MovementType.ADJUSTMENT,
                quantity=qty,
                user_id=self.user.id,
                notes=full_notes
            )
            self.db_session.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", str(e))
