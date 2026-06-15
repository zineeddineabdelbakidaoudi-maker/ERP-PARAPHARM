from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Expiration Tracking Page
"""
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.core.database import get_session
from app.models.stock import StockMovement
from app.repositories.product_repository import ProductRepository


class ExpirationPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.product_repo = ProductRepository(self.db_session)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un produit...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)

        self.filter_combo = SearchableComboBox()
        self.filter_combo.addItem("Tous", 0)
        self.filter_combo.addItem("Expire dans 30 jours", 30)
        self.filter_combo.addItem("Expire dans 60 jours", 60)
        self.filter_combo.addItem("Expire dans 90 jours", 90)
        self.filter_combo.addItem("Déjà expiré", -1)
        self.filter_combo.currentIndexChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.filter_combo)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Produit", "Lot", "Quantité", "Date d'Expiration", "Statut"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.search_input.text().strip().lower()
        days_filter = self.filter_combo.currentData()
        today = datetime.now().date()

        # Query stock movements that have an expiry_date set
        movements = (
            self.db_session.query(StockMovement)
            .filter(StockMovement.expiry_date.isnot(None))
            .filter(StockMovement.expiry_date != "")
            .all()
        )

        for m in movements:
            # Get product name
            product = self.product_repo.get_by_id(m.product_id)
            if not product:
                continue
            if query and query not in product.name.lower() and query not in (product.code or "").lower():
                continue

            try:
                exp_date = datetime.strptime(m.expiry_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            days_left = (exp_date - today).days

            # Apply filter
            if days_filter == -1 and days_left >= 0:
                continue
            elif days_filter > 0 and days_left > days_filter:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(product.name))
            self.table.setItem(row, 1, QTableWidgetItem(m.batch_number or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{m.quantity:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(m.expiry_date))

            # Status
            if days_left < 0:
                status_text = f"Expiré ({abs(days_left)}j)"
                color = Qt.red
            elif days_left <= 30:
                status_text = f"Critique ({days_left}j)"
                color = QColor("#E65100")
            elif days_left <= 90:
                status_text = f"Proche ({days_left}j)"
                color = QColor("#F57F17")
            else:
                status_text = f"OK ({days_left}j)"
                color = Qt.darkGreen

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(color)
            self.table.setItem(row, 4, status_item)
