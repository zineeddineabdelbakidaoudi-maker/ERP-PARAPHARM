# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.invoice import Invoice

class InvoicesPage(QWidget):
    """
    Facture History Page
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
        self.search_input.setPlaceholderText("Recherche par N° Facture ou Code Client...")
        self.search_input.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search_input)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["N° Facture", "Date", "Client", "Total", "Statut"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemDoubleClicked.connect(self._on_invoice_double_clicked)
        layout.addWidget(self.table)

    def _on_invoice_double_clicked(self, item):
        row = item.row()
        inv_id = self.table.item(row, 0).data(Qt.UserRole)
        if not inv_id: return
        from ui.dialogs.invoice_dialog import InvoiceDialog
        dlg = InvoiceDialog(self.db_session, self.user, invoice_id=inv_id, parent=self)
        dlg.exec()

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.search_input.text().strip().lower()
        
        invoices = self.db_session.query(Invoice).order_by(Invoice.created_at.desc()).limit(100).all()
        
        for d in invoices:
            if query:
                cname = d.client.name.lower() if d.client else ""
                if query not in d.invoice_number.lower() and query not in cname:
                    continue
                    
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            num_item = QTableWidgetItem(d.invoice_number)
            num_item.setData(Qt.UserRole, d.id)
            self.table.setItem(row, 0, num_item)
            self.table.setItem(row, 1, QTableWidgetItem(d.created_at[:10]))
            self.table.setItem(row, 2, QTableWidgetItem(d.client.name if d.client else "—"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{d.total_amount:,.2f} DA".replace(",", " ")))
            self.table.setItem(row, 4, QTableWidgetItem(d.status))
