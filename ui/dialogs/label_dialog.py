from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Label Form Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QMessageBox,
    QFormLayout, QFrame, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt
import json
from app.models.product import Label
from app.repositories.base_repository import BaseRepository
from app.core.database import get_session

class LabelDialog(QDialog):
    """Dialog to create or edit a label template."""

    def __init__(self, user, label: Label = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.label = label
        self.db_session = get_session()
        self.repo = BaseRepository(self.db_session, Label)
        
        self.setWindowTitle("Modifier l'Étiquette" if label else "Nouvelle Étiquette")
        self.setMinimumWidth(500)
        self._setup_ui()

        if self.label:
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
        form_layout.setSpacing(12)

        # Fields
        self.name_input = QLineEdit()
        form_layout.addRow("Nom de l'étiquette *", self.name_input)

        self.type_combo = SearchableComboBox()
        self.type_combo.addItems(["PRODUCT", "SHELF", "PRICE", "CUSTOM"])
        form_layout.addRow("Type", self.type_combo)

        self.width_spin = QSpinBox()
        self.width_spin.setMaximum(200)
        self.width_spin.setValue(50)
        self.width_spin.setSuffix(" mm")
        form_layout.addRow("Largeur", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setMaximum(200)
        self.height_spin.setValue(30)
        self.height_spin.setSuffix(" mm")
        form_layout.addRow("Hauteur", self.height_spin)

        self.template_input = QTextEdit()
        self.template_input.setPlaceholderText('Ex: {"fields": ["name", "price", "barcode"]}')
        form_layout.addRow("Template Data (JSON)", self.template_input)

        self.default_check = QCheckBox("Définir comme étiquette par défaut")
        form_layout.addRow("", self.default_check)

        layout.addWidget(form_frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self.name_input.setText(self.label.name)
        self.type_combo.setCurrentText(self.label.label_type)
        self.width_spin.setValue(self.label.width_mm)
        self.height_spin.setValue(self.label.height_mm)
        self.template_input.setPlainText(self.label.template_data)
        self.default_check.setChecked(bool(self.label.is_default))

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return

        template_data = self.template_input.toPlainText().strip()
        if not template_data:
            template_data = "{}"
        else:
            try:
                json.loads(template_data)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Erreur", "Le format JSON du template est invalide.")
                return

        data = {
            "name": name,
            "label_type": self.type_combo.currentText(),
            "width_mm": self.width_spin.value(),
            "height_mm": self.height_spin.value(),
            "template_data": template_data,
            "is_default": 1 if self.default_check.isChecked() else 0
        }

        try:
            if self.label:
                self.repo.update(self.label.id, **data)
            else:
                self.repo.create(**data)
            self.repo.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", str(e))
