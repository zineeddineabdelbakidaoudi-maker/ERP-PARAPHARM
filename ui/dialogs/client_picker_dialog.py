from ui.utils.widgets import SearchableComboBox
# -*- coding: utf-8 -*-
"""
ParaFarm ERP — Sélection d'un Client Dialog (Client Picker)
Completely rebuilt to match SECTION 3.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QFrame, QCheckBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from app.core.database import get_session
from app.models.client import Client
from ui.dialogs.client_dialog import ClientDialog


class ClientPickerDialog(QDialog):
    """
    Sélection d'un Client
    Rebuilt matching the exact layout and behavior described in SECTION 3.
    """

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.selected_client = None

        self.setWindowTitle("Sélectionner un Client")
        self.setMinimumSize(900, 500)
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
        self.search_by_combo.addItems(["Commnance Par Fr", "Contient", "Code Client"])
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

        # Catégorie Label & Dropdown
        toolbar.addWidget(QLabel("Catégorie :"))
        self.category_filter = SearchableComboBox()
        self.category_filter.addItems(["Tous", "PARTICULIER", "ENTREPRISE"])
        self.category_filter.currentIndexChanged.connect(self.refresh_data)
        toolbar.addWidget(self.category_filter)

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
        self.add_btn.clicked.connect(self._on_add_client)
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
        self.edit_btn.clicked.connect(self._on_edit_client)
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
            "Code Client 🔍", 
            "N° 🔍", 
            "Nom 🔍", 
            "Adresse 🔍", 
            "Crédit Max 🔍", 
            "Bloquer 🔍"
        ]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setAlternatingRowColors(False) # Custom row coloring below
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

        query = self.db_session.query(Client).filter(Client.is_deleted == 0)

        # Category filter
        cat = self.category_filter.currentText()
        if cat != "Tous":
            query = query.filter(Client.client_type == cat)

        clients = query.all()

        # Apply search text
        search_txt = self.search_input.text().strip().lower()
        search_by = self.search_by_combo.currentText()

        filtered_clients = []
        for c in clients:
            if not search_txt:
                filtered_clients.append(c)
                continue

            match = False
            if search_by == "Commnance Par Fr":
                match = c.name.lower().startswith(search_txt) or c.code.lower().startswith(search_txt)
            elif search_by == "Contient":
                match = search_txt in c.name.lower() or search_txt in (c.address or "").lower()
            elif search_by == "Code Client":
                match = search_txt in c.code.lower()

            if match:
                filtered_clients.append(c)

        for c in filtered_clients:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Columns: Code Client | N° | Nom | Adresse | Crédit Max | Bloquer
            item_code = QTableWidgetItem(c.code)
            item_id = QTableWidgetItem(str(c.id))
            item_name = QTableWidgetItem(c.name)
            item_address = QTableWidgetItem(c.address or "")
            item_credit = QTableWidgetItem(f"{c.credit_limit:,.2f} DA".replace(",", " "))

            # Store the client object inside item_code
            item_code.setData(Qt.UserRole, c)

            # Custom text alignment
            item_id.setTextAlignment(Qt.AlignCenter)
            item_credit.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.table.setItem(row, 0, item_code)
            self.table.setItem(row, 1, item_id)
            self.table.setItem(row, 2, item_name)
            self.table.setItem(row, 3, item_address)
            self.table.setItem(row, 4, item_credit)

            # Centered Black Checkbox for Bloquer column
            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            
            chk = QCheckBox()
            # If `is_active` is 0, client is blocked (Bloquer = Checked)
            chk.setChecked(c.is_active == 0)
            chk.setEnabled(False) # Read-only in grid
            chk.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid black; background: white; } QCheckBox::indicator:checked { background-color: black; }")
            
            checkbox_layout.addWidget(chk)
            self.table.setCellWidget(row, 5, checkbox_container)

            # Row background colors based on state
            self._apply_row_styling(row, c)

        self.table.setSortingEnabled(True)

    def _apply_row_styling(self, row, client):
        # Default row backgrounds or specific blocked colors
        is_blocked = (client.is_active == 0)
        checkbox_widget = self.table.cellWidget(row, 5)
        
        for col in range(5):
            item = self.table.item(row, col)
            if item:
                if is_blocked:
                    # Blocked client row highlighted in orange/yellow
                    item.setBackground(QColor("#FFE082"))
                else:
                    # Alternate colors
                    if row % 2 == 0:
                        item.setBackground(QColor("#FFFFFF"))
                    else:
                        item.setBackground(QColor("#F9F9F9"))
        
        if checkbox_widget:
            if is_blocked:
                checkbox_widget.setStyleSheet("background-color: #FFE082;")
            else:
                if row % 2 == 0:
                    checkbox_widget.setStyleSheet("background-color: #FFFFFF;")
                else:
                    checkbox_widget.setStyleSheet("background-color: #F9F9F9;")

    def _on_selection_changed(self):
        # Dynamically highlight selected row in cyan/turquoise
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        
        for r in range(self.table.rowCount()):
            # Re-fetch the client to determine if blocked
            code_item = self.table.item(r, 0)
            if not code_item:
                continue
            client = code_item.data(Qt.UserRole)
            checkbox_widget = self.table.cellWidget(r, 5)
            
            if r in selected_rows:
                # Cyan/turquoise highlight for selected row
                for col in range(5):
                    item = self.table.item(r, col)
                    if item:
                        item.setBackground(QColor("#B2DFDB"))
                        item.setForeground(QColor("#004D40"))
                if checkbox_widget:
                    checkbox_widget.setStyleSheet("background-color: #B2DFDB;")
            else:
                # Reset standard coloring
                for col in range(5):
                    item = self.table.item(r, col)
                    if item:
                        item.setForeground(QColor("#212121"))
                self._apply_row_styling(r, client)

    def _on_row_double_clicked(self, item):
        row = item.row()
        code_item = self.table.item(row, 0)
        if code_item:
            self.selected_client = code_item.data(Qt.UserRole)
            self.accept()

    def _on_confirm_selection(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un client.")
            return

        row = selected_ranges[0].topRow()
        code_item = self.table.item(row, 0)
        if code_item:
            self.selected_client = code_item.data(Qt.UserRole)
            self.accept()

    def _on_add_client(self):
        dialog = ClientDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data()

    def _on_edit_client(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Attention", "Veuillez choisir le client à modifier.")
            return

        row = selected_ranges[0].topRow()
        code_item = self.table.item(row, 0)
        if code_item:
            client = code_item.data(Qt.UserRole)
            dialog = ClientDialog(self.user, client=client, parent=self)
            if dialog.exec():
                self.refresh_data()
