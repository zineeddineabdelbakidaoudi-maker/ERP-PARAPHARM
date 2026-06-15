# -*- coding: utf-8 -*-
"""
ParaFarm ERP — Reusable Product Search & Picker Dialog
Designed to search, filter and pick products with high visual fidelity.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from app.core.database import get_session
from app.models.product import Product

class ProductSearchDialog(QDialog):
    """
    State-of-the-art Product Picker Dialog with dynamic database querying.
    """

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.selected_product = None

        self.setWindowTitle("Sélectionner un Produit")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F7FA;
            }
            QLabel {
                font-weight: bold;
                color: #2C3E50;
            }
            QLineEdit {
                border: 2px solid #BDC3C7;
                border-radius: 4px;
                padding: 6px;
                background-color: #FFF59D; /* Soft yellow highlighting for search */
                color: #2C3E50;
                font-weight: bold;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2980B9;
            }
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                gridline-color: #ECF0F1;
                font-size: 13px;
            }
            QHeaderView::section {
                color: black;
                background-color: #34495E;
                color: white;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #2C3E50;
            }
            QPushButton {
                padding: 6px 12px;
                font-weight: bold;
                border-radius: 4px;
            }
        """)

        self._setup_ui()
        self._load_products()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Search Bar
        search_layout = QHBoxLayout()
        search_lbl = QLabel("Recherche / بحث :")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Entrez le code, désignation ou code barre...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(search_lbl)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Table Grid
        cols = ["Code", "Désignation / الاسم", "Prix Public", "PPT", "Stock"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.table.itemDoubleClicked.connect(self._on_confirm_selection)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("❌ Annuler (ESC)")
        self.cancel_btn.setStyleSheet("background-color: #E74C3C; color: white;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.select_btn = QPushButton("✅ Sélectionner (F10)")
        self.select_btn.setStyleSheet("background-color: #2ECC71; color: white;")
        self.select_btn.clicked.connect(self._on_confirm_selection)
        btn_layout.addWidget(self.select_btn)

        layout.addLayout(btn_layout)

        # Focus search input initially
        self.search_input.setFocus()

    def keyPressEvent(self, event):
        # Allow Arrow keys to navigate table even when search is focused
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.table.setFocus()
            self.table.keyPressEvent(event)
        elif event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F10):
            self._on_confirm_selection()
        else:
            super().keyPressEvent(event)

    def _load_products(self, query_str=""):
        self.table.setRowCount(0)
        
        q = self.db_session.query(Product).filter(Product.is_active == 1)
        if query_str:
            filter_pattern = f"%{query_str}%"
            q = q.filter(
                (Product.code.like(filter_pattern)) |
                (Product.name.like(filter_pattern)) |
                (Product.barcode.like(filter_pattern))
            )
        
        products = q.order_by(Product.name.asc()).limit(100).all()
        
        for p in products:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Code
            c_item = QTableWidgetItem(p.code)
            self.table.setItem(row, 0, c_item)

            # Designation
            n_item = QTableWidgetItem(p.name)
            self.table.setItem(row, 1, n_item)

            # Selling Price
            s_item = QTableWidgetItem(f"{p.selling_price:,.2f} DA".replace(",", " "))
            s_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, s_item)

            # PPT Price
            w_val = p.ppt_price if getattr(p, 'ppt_price', None) is not None else p.selling_price
            w_item = QTableWidgetItem(f"{w_val:,.2f} DA".replace(",", " "))
            w_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, w_item)

            # Stock Qty
            stock_qty = p.stock.quantity if p.stock else 0.0
            st_item = QTableWidgetItem(f"{stock_qty:,.0f}")
            st_item.setTextAlignment(Qt.AlignCenter)
            
            # Colour Stock depending on availability
            if stock_qty <= 0:
                st_item.setForeground(QBrush(QColor("#E74C3C")))
            elif stock_qty < (p.min_stock_level or 10):
                st_item.setForeground(QBrush(QColor("#D35400")))
            else:
                st_item.setForeground(QBrush(QColor("#27AE60")))

            self.table.setItem(row, 4, st_item)

            # Keep reference to the actual model object
            for col in range(5):
                item = self.table.item(row, col)
                if item:
                    item.setData(Qt.UserRole, p)
                    # Highlight selected row in cyan
                    # We will rely on Qt's selection highlight stylesheet, but can apply custom selection styling
            
            # Apply custom style to row: if stock is 0, give a light grey background or standard
            if stock_qty <= 0:
                for col in range(5):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor("#F9EBEA")) # Very soft red for out of stock

        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _on_search(self):
        text = self.search_input.text().strip()
        self._load_products(text)

    def _on_confirm_selection(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                self.selected_product = item.data(Qt.UserRole)
                self.accept()
        else:
            self.reject()
