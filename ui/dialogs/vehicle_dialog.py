from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Vehicle Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QComboBox, QMessageBox, QCheckBox
)
from app.core.database import get_session
from app.models.logistics import Vehicle


class VehicleDialog(QDialog):
    def __init__(self, user, vehicle=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.vehicle = vehicle
        self.db_session = get_session()
        self.setWindowTitle("Modifier Véhicule" if vehicle else "Nouveau Véhicule")
        self.setMinimumWidth(400)
        self._setup_ui()
        if vehicle:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        form.addRow("Nom / Marque :", self.name_input)

        self.plate_input = QLineEdit()
        form.addRow("Immatriculation :", self.plate_input)

        self.type_input = SearchableComboBox()
        self.type_input.addItems(["Van", "Camion", "Moto", "Voiture"])
        form.addRow("Type de véhicule :", self.type_input)

        self.capacity_input = QLineEdit("0.0")
        form.addRow("Capacité (T/Kg/Vol) :", self.capacity_input)

        self.active_check = QCheckBox("Véhicule Actif")
        self.active_check.setChecked(True)
        form.addRow("", self.active_check)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self.name_input.setText(self.vehicle.name)
        self.plate_input.setText(self.vehicle.plate_number)
        self.type_input.setCurrentText(self.vehicle.vehicle_type or "Van")
        self.capacity_input.setText(str(self.vehicle.capacity))
        self.active_check.setChecked(bool(self.vehicle.is_active))

    def _save(self):
        name = self.name_input.text().strip()
        plate = self.plate_input.text().strip()

        if not name or not plate:
            QMessageBox.warning(self, "Erreur", "Le nom et l'immatriculation sont requis.")
            return

        try:
            capacity = float(self.capacity_input.text())
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Capacité invalide.")
            return

        if not self.vehicle:
            self.vehicle = Vehicle()
            self.db_session.add(self.vehicle)

        self.vehicle.name = name
        self.vehicle.plate_number = plate
        self.vehicle.vehicle_type = self.type_input.currentText()
        self.vehicle.capacity = capacity
        self.vehicle.is_active = 1 if self.active_check.isChecked() else 0

        try:
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {e}")
