from ui.utils.widgets import SearchableComboBox
# -*- coding: utf-8 -*-
"""
ParaFarm ERP — Sélection d'un Fournisseur Dialog (Supplier Picker)
Completely rebuilt to match SECTION 4.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.core.database import get_session
from app.models.supplier import Supplier
from ui.dialogs.supplier_dialog import SupplierDialog


class SupplierPickerDialog(QDialog):
    """
    Sélection d'un Fournisseur
    Rebuilt matching the exact layout and behavior described in SECTION 4.
    """

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.selected_supplier = None

        self.setWindowTitle("Sélectionner un Fournisseur")
        self.setMinimumSize(750, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                font-weight: 600;
                font-size: 13px;
                color: #37474F;
            }
            QComboBox {
                border: 1px solid #B0BEC5;
                border-radius: 4px;
                padding: 4px;
                background-color: #FFFFFF;
                min-width: 140px;
                min-height: 28px;
            }
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F9F9F9;
                gridline-color: #ECEFF1;
                border: 1px solid #CFD8DC;
                border-radius: 4px;
            }
        """)

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ── HEADER TOOLBAR ──────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Recherche Par Dropdown
        toolbar.addWidget(QLabel("Recherche Par :"))
        self.search_by_combo = SearchableComboBox()
        self.search_by_combo.addItems(["Commnance Par Fr", "Contient"])
        toolbar.addWidget(self.search_by_combo)

        # Language Flag "Fr" Button
        self.lang_btn = QPushButton("Fr 🇫🇷")
        self.lang_btn.setFixedSize(50, 32)
        self.lang_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #333;
                border: 1px solid #B0BEC5;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ECEFF1; color: black;
            }
        """)
        toolbar.addWidget(self.lang_btn)

        # Yellow highlighted search text input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Saisir texte de recherche...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFF59D;  /* Yellow highlight */
                border: 2px solid #FBC02D;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
                font-weight: bold;
                color: #212121;
            }
            QLineEdit:focus {
                background-color: #FFF9C4;
                border: 2px solid #F57F17;
            }
        """)
        self.search_input.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search_input, stretch=1)

        # Action Buttons: + (green) | pencil (yellow) | checkmark (green) | X (red)
        self.add_btn = QPushButton("➕ Nouveau")
        self.add_btn.setFixedHeight(32)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #43A047;
            }
        """)
        self.add_btn.clicked.connect(self._on_add_supplier)
        toolbar.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Modifier")
        self.edit_btn.setFixedHeight(32)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFEB3B;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 0 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FDD835;
            }
        """)
        self.edit_btn.clicked.connect(self._on_edit_supplier)
        toolbar.addWidget(self.edit_btn)

        self.select_btn = QPushButton("✔️ Choisir")
        self.select_btn.setFixedHeight(32)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1B5E20;
            }
        """)
        self.select_btn.clicked.connect(self._on_confirm_selection)
        toolbar.addWidget(self.select_btn)

        self.close_btn = QPushButton("❌ Fermer")
        self.close_btn.setFixedHeight(32)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E53935;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.close_btn.clicked.connect(self.reject)
        toolbar.addWidget(self.close_btn)

        layout.addLayout(toolbar)

        # ── DATA GRID ───────────────────────────────────────────
        # Column names with magnifier icons and sort arrows
        cols = [
            "N° 🔍", 
            "Nom 🔍", 
            "Adresse 🔍"
        ]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStyleSheet("QHeaderView::section { font-weight: bold; background-color: #ECEFF1; color: black; padding: 6px; }")

        # Double-click selects row
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.table)

    def refresh_data(self):
        # Disable sorting while populating to avoid indexing bugs
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        suppliers = self.db_session.query(Supplier).filter(Supplier.is_deleted == 0).all()

        # Apply search text
        search_txt = self.search_input.text().strip().lower()
        search_by = self.search_by_combo.currentText()

        filtered = []
        for s in suppliers:
            if not search_txt:
                filtered.append(s)
                continue

            match = False
            if search_by == "Commnance Par Fr":
                match = s.name.lower().startswith(search_txt) or s.code.lower().startswith(search_txt)
            elif search_by == "Contient":
                match = search_txt in s.name.lower() or search_txt in (s.address or "").lower()

            if match:
                filtered.append(s)

        for s in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Columns: N° | Nom | Adresse
            item_id = QTableWidgetItem(str(s.id))
            item_name = QTableWidgetItem(s.name)
            item_address = QTableWidgetItem(s.address or "")

            # Store the supplier object inside item_id
            item_id.setData(Qt.UserRole, s)

            item_id.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_name)
            self.table.setItem(row, 2, item_address)

            # Alternate row background colors
            self._apply_row_styling(row, s)

        self.table.setSortingEnabled(True)

    def _apply_row_styling(self, row, supplier):
        for col in range(3):
            item = self.table.item(row, col)
            if item:
                if row % 2 == 0:
                    item.setBackground(QColor("#FFFFFF"))
                else:
                    item.setBackground(QColor("#F9F9F9"))

    def _on_selection_changed(self):
        # Dynamically highlight selected row in cyan
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        
        for r in range(self.table.rowCount()):
            id_item = self.table.item(r, 0)
            if not id_item:
                continue
            s = id_item.data(Qt.UserRole)
            
            if r in selected_rows:
                # Cyan highlight for selected row
                for col in range(3):
                    item = self.table.item(r, col)
                    if item:
                        item.setBackground(QColor("#B2DFDB"))
                        item.setForeground(QColor("#004D40"))
            else:
                for col in range(3):
                    item = self.table.item(r, col)
                    if item:
                        item.setForeground(QColor("#212121"))
                self._apply_row_styling(r, s)

    def _on_row_double_clicked(self, item):
        row = item.row()
        id_item = self.table.item(row, 0)
        if id_item:
            self.selected_supplier = id_item.data(Qt.UserRole)
            self.accept()

    def _on_confirm_selection(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un fournisseur.")
            return

        row = selected_ranges[0].topRow()
        id_item = self.table.item(row, 0)
        if id_item:
            self.selected_supplier = id_item.data(Qt.UserRole)
            self.accept()

    def _on_add_supplier(self):
        dialog = SupplierDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data()

    def _on_edit_supplier(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Attention", "Veuillez choisir le fournisseur à modifier.")
            return

        row = selected_ranges[0].topRow()
        id_item = self.table.item(row, 0)
        if id_item:
            supplier = id_item.data(Qt.UserRole)
            dialog = SupplierDialog(self.user, supplier=supplier, parent=self)
            if dialog.exec():
                self.refresh_data()
