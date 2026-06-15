from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.stock import StockBatch
from app.models.product import Product


class LotsPage(QWidget):
    """Global page to view all Stock Batches and their expiration dates."""

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Lots & Péremptions")
        title.setProperty("class", "pageTitle")
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par produit ou n° de lot...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search_input)

        refresh_btn = QPushButton("Actualiser")
        refresh_btn.setProperty("variant", "primary")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Code Produit", "Désignation", "N° Lot", "Date Péremption", "Qté Restante", "Prix Achat"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        self.db_session.expire_all()
        
        q = self.db_session.query(StockBatch).join(Product).filter(StockBatch.remaining_quantity > 0)
        
        if query:
            search_str = f"%{query}%"
            q = q.filter(
                (Product.name.ilike(search_str)) | 
                (Product.code.ilike(search_str)) | 
                (StockBatch.lot_number.ilike(search_str))
            )
            
        batches = q.order_by(StockBatch.expiration_date.asc()).limit(200).all()

        from datetime import datetime
        current_date = datetime.now().strftime("%m/%yyyy") # just to compare strings roughly or format correctly
        
        for b in batches:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            p = b.product
            self.table.setItem(row, 0, QTableWidgetItem(p.code if p else "N/A"))
            self.table.setItem(row, 1, QTableWidgetItem(p.name if p else "N/A"))
            self.table.setItem(row, 2, QTableWidgetItem(b.lot_number or "N/A"))
            
            exp_item = QTableWidgetItem(b.expiration_date or "N/A")
            # Basic highlighting for expired or near expiration could be added here
            self.table.setItem(row, 3, exp_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(f"{b.remaining_quantity:.2f}"))
            cost_str = f"{b.cost_price:.2f} DA" if b.cost_price is not None else "---"
            self.table.setItem(row, 5, QTableWidgetItem(cost_str))

