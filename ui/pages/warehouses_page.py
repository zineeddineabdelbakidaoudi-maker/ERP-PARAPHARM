from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Warehouses Page (Entrepôts)
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QFrame, QComboBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.warehouse import Warehouse


class WarehouseDialog(QDialog):
    def __init__(self, db_session, warehouse=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.warehouse = warehouse
        self.setWindowTitle("Modifier Entrepôt" if warehouse else "Nouvel Entrepôt")
        self.setMinimumWidth(420)
        self._setup_ui()
        if warehouse:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        title = QLabel(self.windowTitle())
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form = QFormLayout(form_frame)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom de l'entrepôt")
        form.addRow("Nom *", self.name_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Adresse / Emplacement")
        form.addRow("Emplacement", self.location_input)

        self.active_combo = SearchableComboBox()
        self.active_combo.addItems(["Actif", "Inactif"])
        form.addRow("Statut", self.active_combo)

        layout.addWidget(form_frame)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setProperty("variant", "secondary")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton("💾 Enregistrer")
        save.clicked.connect(self._on_save)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _load_data(self):
        self.name_input.setText(self.warehouse.name)
        self.location_input.setText(self.warehouse.location or "")
        self.active_combo.setCurrentIndex(0 if self.warehouse.is_active else 1)

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
        try:
            if self.warehouse:
                self.warehouse.name = name
                self.warehouse.location = self.location_input.text().strip()
                self.warehouse.is_active = 1 if self.active_combo.currentIndex() == 0 else 0
            else:
                wh = Warehouse(
                    name=name,
                    location=self.location_input.text().strip(),
                    is_active=1 if self.active_combo.currentIndex() == 0 else 0,
                )
                self.db_session.add(wh)
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", str(e))


class WarehousesPage(QWidget):
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

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher un entrepôt...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)
        toolbar.addStretch()
        add_btn = QPushButton("➕ Nouvel Entrepôt")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nom", "Emplacement", "Statut", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 220)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def refresh_data(self):
        search = self.search_input.text().strip().lower()
        self.table.setRowCount(0)
        warehouses = self.db_session.query(Warehouse).order_by(Warehouse.name).all()
        if search:
            warehouses = [w for w in warehouses if search in w.name.lower()]

        for wh in warehouses:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(wh.name))
            self.table.setItem(row, 1, QTableWidgetItem(wh.location or "—"))

            status = QTableWidgetItem("✅ Actif" if wh.is_active else "❌ Inactif")
            status.setForeground(Qt.darkGreen if wh.is_active else Qt.red)
            self.table.setItem(row, 2, status)

            widget = QWidget()
            btn_layout = QHBoxLayout(widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            edit_btn = QPushButton("✏️ Modifier")
            edit_btn.setProperty("variant", "icon-edit")
            edit_btn.clicked.connect(lambda checked, w=wh: self._on_edit(w))
            btn_layout.addWidget(edit_btn)
            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, w=wh: self._on_delete(w))
            btn_layout.addWidget(del_btn)
            self.table.setCellWidget(row, 3, widget)

    def _on_add(self):
        dlg = WarehouseDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_edit(self, wh):
        dlg = WarehouseDialog(self.db_session, warehouse=wh, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_delete(self, wh):
        reply = QMessageBox.question(self, "Confirmer", f"Supprimer l'entrepôt '{wh.name}' ?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_session.delete(wh)
            self.db_session.commit()
            self.refresh_data()
