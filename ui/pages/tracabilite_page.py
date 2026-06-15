from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from app.core.database import get_session
from app.models.stock import StockBatch, StockMovement
from ui.utils.widgets import SearchableComboBox

class TracabilitePage(QWidget):
    """
    Page dédiée à la traçabilité des lots (Batch Tracking).
    """
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Titre
        title = QLabel("🔍 Traçabilité des Lots (Péremptions & Mouvements)")
        title.setProperty("class", "pageTitle")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #37474F;")
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un N° de Lot ou Produit...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Produit", "N° Lot", "Date Péremption", "Entrées", "Sorties", "Reste", "Statut"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        layout.addWidget(self.table)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        
        batches = self.db_session.query(StockBatch).join(StockBatch.product).order_by(StockBatch.expiration_date.asc()).all()
        
        if query:
            q = query.lower()
            batches = [b for b in batches if q in str(b.lot_number).lower() or q in b.product.name.lower()]

        now = datetime.now()
        alert_threshold = now + timedelta(days=90)

        for b in batches:
            # Calcule les entrées et sorties via StockMovement
            movements = self.db_session.query(StockMovement).filter(
                StockMovement.product_id == b.product_id,
                StockMovement.batch_number == b.lot_number
            ).all()
            
            entrees = sum(m.quantity for m in movements if m.quantity > 0)
            sorties = sum(abs(m.quantity) for m in movements if m.quantity < 0)
            
            # Use stored remaining quantity
            reste = b.remaining_quantity

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(b.product.name))
            self.table.setItem(row, 1, QTableWidgetItem(str(b.lot_number)))
            
            exp_date_str = b.expiration_date or "—"
            exp_item = QTableWidgetItem(exp_date_str)
            
            status_text = "🟢 Normal"
            status_color = Qt.darkGreen
            
            # Check expiration
            if b.expiration_date:
                try:
                    exp_date = datetime.strptime(b.expiration_date, "%Y-%m-%d")
                    if exp_date < now:
                        status_text = "🔴 EXPIRÉ"
                        status_color = QColor("#D32F2F")
                        exp_item.setForeground(status_color)
                    elif exp_date <= alert_threshold:
                        status_text = "🟠 Expire dans < 90j"
                        status_color = QColor("#F57C00")
                        exp_item.setForeground(status_color)
                except ValueError:
                    pass

            if reste <= 0:
                status_text = "⚫ Épuisé"
                status_color = QColor("#757575")

            self.table.setItem(row, 2, exp_item)
            self.table.setItem(row, 3, QTableWidgetItem(f"{entrees:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{sorties:.2f}"))
            
            reste_item = QTableWidgetItem(f"{reste:.2f}")
            bold_font = QFont()
            bold_font.setBold(True)
            reste_item.setFont(bold_font)
            self.table.setItem(row, 5, reste_item)
            
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(status_color)
            status_item.setFont(bold_font)
            self.table.setItem(row, 6, status_item)

    def _on_search(self, text):
        self.refresh_data(text)
