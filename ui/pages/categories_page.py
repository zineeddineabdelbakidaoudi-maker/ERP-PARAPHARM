"""
ParaFarm ERP — Category Management Page
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.base_repository import BaseRepository
from app.models.product import Category
from app.services.audit_service import AuditService

class CategoryDialog(QDialog):
    def __init__(self, category_obj=None, parent=None):
        super().__init__(parent)
        self.category_obj = category_obj
        self.db_session = get_session()
        self.repo = BaseRepository(self.db_session, Category)
        
        self.setWindowTitle("Modifier la Catégorie" if category_obj else "Nouvelle Catégorie")
        self.setMinimumWidth(400)
        self._setup_ui()
        if self.category_obj:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel(self.windowTitle())
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form_layout = QFormLayout(form_frame)

        self.name_input = QLineEdit()
        form_layout.addRow("Nom de la Catégorie *", self.name_input)

        layout.addWidget(form_frame)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Enregistrer")
        save_btn.setProperty("variant", "success")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self.name_input.setText(self.category_obj.name)

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return

        try:
            if self.category_obj:
                self.category_obj.name = name
            else:
                self.repo.create(name=name)
            self.repo.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


class CategoriesPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.repo = BaseRepository(self.db_session, Category)
        self.audit = AuditService(self.db_session)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher une catégorie...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        add_btn = QPushButton("➕ Nouvelle Catégorie")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Nom", "Actions"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 220)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        res = self.repo.get_all()
        categories = res.get("items", []) if isinstance(res, dict) else res

        if query:
            q = query.lower()
            categories = [c for c in categories if q in c.name.lower()]

        for c in categories:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(c.id)))
            self.table.setItem(row, 1, QTableWidgetItem(c.name))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            edit_btn = QPushButton("✏️ Modifier")
            edit_btn.setProperty("variant", "icon-edit")
            edit_btn.clicked.connect(lambda checked, cat=c: self._on_edit(cat))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, cat=c: self._on_delete(cat))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 2, action_widget)

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_add(self):
        dialog = CategoryDialog(parent=self)
        if dialog.exec():
            self.audit.log_create(self.user.id, "PRODUCTS", "Category", 0, description="Création catégorie")
            self.refresh_data(self.search_input.text())

    def _on_edit(self, category):
        dialog = CategoryDialog(category_obj=category, parent=self)
        if dialog.exec():
            self.audit.log_update(self.user.id, "PRODUCTS", "Category", category.id, description=f"Modif catégorie {category.name}")
            self.refresh_data(self.search_input.text())

    def _on_delete(self, category):
        reply = QMessageBox.question(
            self, "Supprimer", f"Voulez-vous supprimer la catégorie {category.name} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.repo.soft_delete(category.id)
            self.repo.commit()
            self.audit.log_delete(self.user.id, "PRODUCTS", "Category", category.id, description=f"Suppression catégorie {category.name}")
            self.refresh_data(self.search_input.text())
