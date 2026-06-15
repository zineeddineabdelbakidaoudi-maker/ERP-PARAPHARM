# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.delivery import Delivery

class DeliveriesPage(QWidget):
    """
    Bon de Livraison (BL) History Page
    """
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Recherche par N° BL ou Code Client...")
        self.search_input.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search_input)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["N° BL", "Date", "Client", "Zone", "Statut"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.search_input.text().strip().lower()
        
        deliveries = self.db_session.query(Delivery).order_by(Delivery.created_at.desc()).limit(100).all()
        
        for d in deliveries:
            if query:
                cname = d.client.name.lower() if d.client else ""
                if query not in d.delivery_number.lower() and query not in cname:
                    continue
                    
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(d.delivery_number))
            self.table.setItem(row, 1, QTableWidgetItem(d.scheduled_date or d.created_at[:10]))
            self.table.setItem(row, 2, QTableWidgetItem(d.client.name if d.client else "—"))
            self.table.setItem(row, 3, QTableWidgetItem(d.zone or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(d.status))
