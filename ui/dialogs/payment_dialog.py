from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QMessageBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QDateEdit

class PaymentDialog(QDialog):
    def __init__(self, max_amount, parent=None):
        super().__init__(parent)
        self.max_amount = max_amount
        self.setWindowTitle("Ajouter un Versement / Règlement")
        self.setFixedSize(400, 300)
        
        self.payment_data = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Date
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date :"))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.date_edit)
        layout.addLayout(date_layout)

        # Montant
        amt_layout = QHBoxLayout()
        amt_layout.addWidget(QLabel("Montant :"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(self.max_amount if self.max_amount > 0 else 999999999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(self.max_amount if self.max_amount > 0 else 0)
        self.amount_spin.setStyleSheet("font-size: 14px; font-weight: bold;")
        amt_layout.addWidget(self.amount_spin)
        layout.addLayout(amt_layout)

        # Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode :"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["ESPECES", "CHEQUE", "VIREMENT", "TRAITE"])
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)

        # Référence
        ref_layout = QHBoxLayout()
        ref_layout.addWidget(QLabel("Référence :"))
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("Ex: CHQ-12345...")
        ref_layout.addWidget(self.ref_input)
        layout.addLayout(ref_layout)

        # Banque
        bank_layout = QHBoxLayout()
        bank_layout.addWidget(QLabel("Banque :"))
        self.bank_input = QLineEdit()
        self.bank_input.setPlaceholderText("Nom de la banque (optionnel)")
        bank_layout.addWidget(self.bank_input)
        layout.addLayout(bank_layout)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("✔️ Valider Règlement")
        ok_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        ok_btn.clicked.connect(self._validate)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)

    def _validate(self):
        amt = self.amount_spin.value()
        if amt <= 0:
            QMessageBox.warning(self, "Erreur", "Le montant doit être supérieur à 0.")
            return
            
        if self.max_amount > 0 and amt > self.max_amount:
            reply = QMessageBox.question(
                self, "Attention", 
                f"Le montant saisi ({amt} DA) est supérieur au reste à payer ({self.max_amount} DA). Continuer (Cela va créer un avoir) ?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Build combined reference string
        ref = self.ref_input.text().strip()
        bank = self.bank_input.text().strip()
        final_ref = ref
        if bank:
            final_ref = f"{ref} ({bank})" if ref else bank

        self.payment_data = {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "amount": amt,
            "method": self.mode_combo.currentText(),
            "reference": final_ref
        }
        
        self.accept()
