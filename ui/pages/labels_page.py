"""
ParaFarm ERP — Labels Page
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.base_repository import BaseRepository
from app.models.product import Label
from ui.dialogs.label_dialog import LabelDialog

class LabelsPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.repo = BaseRepository(self.db_session, Label)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher une étiquette (Nom)...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()

        add_btn = QPushButton("➕ Nouvelle Étiquette")
        add_btn.clicked.connect(self._on_add_label)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Nom", "Type", "Dimensions (LxH)", "Défaut", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 220)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        
        res = self.repo.get_all()
        labels = res.get("items", []) if isinstance(res, dict) else res
        
        if query:
            q = query.lower()
            labels = [l for l in labels if q in l.name.lower()]

        for lbl in labels:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(lbl.name))
            self.table.setItem(row, 1, QTableWidgetItem(lbl.label_type))
            self.table.setItem(row, 2, QTableWidgetItem(f"{lbl.width_mm}x{lbl.height_mm} mm"))
            
            is_default = "Oui" if lbl.is_default else "Non"
            item_def = QTableWidgetItem(is_default)
            if lbl.is_default:
                item_def.setForeground(Qt.darkGreen)
            self.table.setItem(row, 3, item_def)
            
            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 0, 4, 0)
            action_layout.setSpacing(4)
            
            edit_btn = QPushButton("✏️ Modifier")
            edit_btn.setProperty("variant", "icon-edit")
            edit_btn.clicked.connect(lambda checked, l=lbl: self._on_edit_label(l))
            action_layout.addWidget(edit_btn)
            
            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, l=lbl: self._on_delete_label(l))
            action_layout.addWidget(del_btn)
            
            self.table.setCellWidget(row, 4, action_widget)

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_add_label(self):
        dialog = LabelDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_edit_label(self, label):
        dialog = LabelDialog(self.user, label=label, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_delete_label(self, label):
        reply = QMessageBox.question(
            self, "Supprimer", f"Voulez-vous supprimer l'étiquette {label.name} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.repo.hard_delete(label.id)  # Using hard_delete since Label doesn't have is_deleted
            self.refresh_data(self.search_input.text())
