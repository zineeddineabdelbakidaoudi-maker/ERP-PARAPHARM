from ui.utils.widgets import SearchableComboBox
# -*- coding: utf-8 -*-
"""
ParaFarm ERP — Client Payment Dialog (Fiche Versements Client)
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QComboBox, QCheckBox, QRadioButton,
    QButtonGroup, QFrame, QMessageBox, QWidget, QDateEdit, QTimeEdit,
    QFormLayout, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

from app.core.database import get_session
from app.models.client import Client
from app.models.debt import Debt, Payment
from app.services.debt_service import DebtService
from app.core.number_to_arabic import number_to_arabic_words


class ClientPaymentDialog(QDialog):
    """
    Fiche Versements Client
    Completely rebuilt to match the exact layout described in SECTION 1.
    """

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.debt_service = DebtService(self.db_session)
        self.selected_client = None
        self._ancien_credit_val = 0.0
        self.clients_list = []

        self.setWindowTitle("Versement Client")
        self.setMinimumSize(950, 650)
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QLabel {
                font-weight: 500;
                color: #333333;
            }
            QLineEdit, QComboBox, QDateEdit, QTimeEdit {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px;
                background-color: #FFFFFF;
                font-size: 13px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {
                border: 1px solid #1E88E5;
            }
            QCheckBox, QRadioButton {
                font-size: 13px;
                spacing: 6px;
            }
            QPushButton {
                font-weight: 600;
                border-radius: 4px;
            }
        """)

        self._setup_ui()
        self._load_clients()
        self._setup_shortcuts()
        self._update_calculation()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ── LEFT & BODY PANEL ──────────────────────────────────
        body_panel = QVBoxLayout()
        body_panel.setSpacing(10)

        # Header Section
        header_layout = QHBoxLayout()
        
        # Title
        title_lbl = QLabel("Versement Client")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #1565C0;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        # N° Reçu
        header_layout.addWidget(QLabel("N° Reçu :"))
        self.recu_input = QLineEdit()
        self.recu_input.setPlaceholderText("N° de Reçu manuscrit")
        self.recu_input.setFixedWidth(160)
        header_layout.addWidget(self.recu_input)

        # Imprimante
        header_layout.addWidget(QLabel("Imprimante :"))
        self.printer_combo = SearchableComboBox()
        self.printer_combo.addItem("Default System Printer")
        # Try to load real printers if possible
        try:
            from PySide6.QtPrintSupport import QPrinterInfo
            printers = [p.printerName() for p in QPrinterInfo.availablePrinters()]
            if printers:
                self.printer_combo.clear()
                self.printer_combo.addItems(printers)
                default_p = QPrinterInfo.defaultPrinterName()
                if default_p:
                    self.printer_combo.setCurrentText(default_p)
        except Exception:
            pass
        self.printer_combo.setFixedWidth(180)
        header_layout.addWidget(self.printer_combo)

        # Refresh printer button
        self.refresh_printer_btn = QPushButton("🔄")
        self.refresh_printer_btn.setFixedSize(32, 32)
        self.refresh_printer_btn.setStyleSheet("background-color: #E0E0E0; color: black; border: 1px solid #CCC;")
        self.refresh_printer_btn.clicked.connect(self._refresh_printers)
        header_layout.addWidget(self.refresh_printer_btn)

        body_panel.addLayout(header_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #E0E0E0;")
        body_panel.addWidget(sep)

        # Form grid
        form_grid = QGridLayout()
        form_grid.setSpacing(10)

        # Nom Client / اسم العميل
        form_grid.addWidget(QLabel("Nom / اسم :"), 0, 0)
        client_selector_layout = QHBoxLayout()
        self.client_combo = SearchableComboBox()
        self.client_combo.setEditable(True)
        self.client_combo.setPlaceholderText("Rechercher ou sélectionner un client...")
        self.client_combo.currentTextChanged.connect(self._on_client_search_text_changed)
        self.client_combo.currentIndexChanged.connect(self._on_client_selected)
        client_selector_layout.addWidget(self.client_combo, stretch=1)
        
        self.client_search_btn = QPushButton("🔍")
        self.client_search_btn.setFixedSize(32, 32)
        self.client_search_btn.setStyleSheet("background-color: #1E88E5; color: white;")
        self.client_search_btn.clicked.connect(self._open_client_picker)
        client_selector_layout.addWidget(self.client_search_btn)
        form_grid.addLayout(client_selector_layout, 0, 1)

        # Ancien crédit / الرصيد السابق
        form_grid.addWidget(QLabel("Ancien crédit / الرصيد السابق :"), 1, 0)
        ancien_layout = QHBoxLayout()
        self.ancien_credit_lbl = QLabel("0,00 DA")
        self.ancien_credit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32; padding: 4px;")
        ancien_layout.addWidget(self.ancien_credit_lbl)
        
        self.clock_icon1 = QLabel("🕐")
        self.clock_icon1.setStyleSheet("font-size: 16px;")
        ancien_layout.addWidget(self.clock_icon1)
        ancien_layout.addStretch()
        form_grid.addLayout(ancien_layout, 1, 1)

        # Date de versement / تاريخ وساعة الدفع
        form_grid.addWidget(QLabel("Date de versement / تاريخ وساعة الدفع :"), 2, 0)
        date_layout = QHBoxLayout()
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_picker)

        # Small box for day number
        self.day_number_box = QLabel(str(QDate.currentDate().day()))
        self.day_number_box.setAlignment(Qt.AlignCenter)
        self.day_number_box.setStyleSheet("border: 1px solid #CCC; background-color: #EEE; border-radius: 3px; font-weight: bold; padding: 2px 8px; font-size: 12px;")
        date_layout.addWidget(self.day_number_box)

        # Time Picker
        date_layout.addWidget(QLabel("Heure :"))
        self.time_picker = QTimeEdit()
        self.time_picker.setTime(QTime.currentTime())
        date_layout.addWidget(self.time_picker)

        self.clock_icon2 = QLabel("🕐")
        self.clock_icon2.setStyleSheet("font-size: 16px;")
        date_layout.addWidget(self.clock_icon2)
        date_layout.addStretch()
        form_grid.addLayout(date_layout, 2, 1)

        body_panel.addLayout(form_grid)

        # ── LARGE BLUE HEADER SECTION FOR AMOUNT ──
        self.amount_card = QFrame()
        self.amount_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976D2, stop:1 #0D47A1);
                border-radius: 8px;
                color: white;
            }
            QLabel {
                color: white;
            }
        """)
        amount_layout = QVBoxLayout(self.amount_card)
        amount_layout.setContentsMargins(15, 15, 15, 15)
        amount_layout.setSpacing(5)

        # Section label bilingual
        lbl_montant = QLabel("Montant à Verser / مبلغ الدفع")
        lbl_montant.setStyleSheet("font-size: 14px; font-weight: 600; text-transform: uppercase; color: rgba(255,255,255,0.85);")
        amount_layout.addWidget(lbl_montant)

        # Arabic words
        self.arabic_words_lbl = QLabel("صفر دينار")
        self.arabic_words_lbl.setStyleSheet("font-size: 14px; font-style: italic; color: #E3F2FD;")
        self.arabic_words_lbl.setAlignment(Qt.AlignLeft)
        amount_layout.addWidget(self.arabic_words_lbl)

        # Display amount box
        display_layout = QHBoxLayout()
        self.amount_display_lbl = QLabel("0,00 DA")
        self.amount_display_lbl.setStyleSheet("font-size: 32px; font-weight: 900; letter-spacing: 1px;")
        display_layout.addWidget(self.amount_display_lbl)
        display_layout.addStretch()
        
        self.centimes_lbl = QLabel("CENTIMES")
        self.centimes_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: rgba(255,255,255,0.7);")
        self.centimes_lbl.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        display_layout.addWidget(self.centimes_lbl)
        amount_layout.addLayout(display_layout)

        # Number Input Box inside the blue layout for easy entry
        input_container = QHBoxLayout()
        input_container.addWidget(QLabel("Saisir Montant :"))
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setDecimals(2)
        self.amount_input.setMaximum(99999999.99)
        self.amount_input.setMinimum(0.00)
        self.amount_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.amount_input.setFixedWidth(200)
        self.amount_input.setStyleSheet("color: black; background-color: white; font-size: 16px; font-weight: bold; padding: 4px;")
        self.amount_input.valueChanged.connect(self._on_amount_changed)
        input_container.addWidget(self.amount_input)
        input_container.addStretch()
        amount_layout.addLayout(input_container)

        body_panel.addWidget(self.amount_card)

        # Extra Fields Form
        extra_form = QGridLayout()
        extra_form.setSpacing(8)

        # Versement Chèque checkbox
        self.cheque_checkbox = QCheckBox("Versement Chèque")
        self.cheque_checkbox.stateChanged.connect(self._on_cheque_state_changed)
        extra_form.addWidget(self.cheque_checkbox, 0, 0, 1, 2)

        # Remboursement section
        self.remboursement_checkbox = QCheckBox("Remboursement au client (Après retour,...)")
        self.remboursement_checkbox.stateChanged.connect(self._update_calculation)
        extra_form.addWidget(self.remboursement_checkbox, 1, 0, 1, 2)

        # N° Chèque
        extra_form.addWidget(QLabel("N° Chèque :"), 2, 0)
        self.cheque_number_input = QLineEdit()
        self.cheque_number_input.setPlaceholderText("Si le versement est par chèque saisie ici le N°")
        self.cheque_number_input.setEnabled(False)
        extra_form.addWidget(self.cheque_number_input, 2, 1)

        # Montant Remise / مبلغ التخفيض
        extra_form.addWidget(QLabel("Montant Remise / مبلغ التخفيض :"), 3, 0)
        self.remise_input = QDoubleSpinBox()
        self.remise_input.setMaximum(9999999.99)
        self.remise_input.setDecimals(2)
        self.remise_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.remise_input.setStyleSheet("background-color: #FFFDE7; font-size: 14px; font-weight: bold; color: black; border: 1px solid #CCC;")
        self.remise_input.valueChanged.connect(self._update_calculation)
        extra_form.addWidget(self.remise_input, 3, 1)

        # Nouveau crédit / الرصيد النهائي
        extra_form.addWidget(QLabel("Nouveau crédit / الرصيد النهائي :"), 4, 0)
        self.nouveau_credit_lbl = QLabel("0,00 DA")
        self.nouveau_credit_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #C62828; padding: 4px;")
        extra_form.addWidget(self.nouveau_credit_lbl, 4, 1)

        # Observation
        extra_form.addWidget(QLabel("Observation :"), 5, 0)
        self.observation_input = QLineEdit()
        self.observation_input.setPlaceholderText("Nom du verseur...")
        extra_form.addWidget(self.observation_input, 5, 1)

        body_panel.addLayout(extra_form)
        main_layout.addLayout(body_panel, stretch=3)

        # ── RIGHT PANEL (PRINT OPTIONS & ACTIONS) ──────────────
        right_panel = QFrame()
        right_panel.setFixedWidth(260)
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #ECEFF1;
                border-radius: 8px;
                border: 1px solid #CFD8DC;
            }
            QLabel {
                font-weight: bold;
                color: #37474F;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        # Impression section
        right_layout.addWidget(QLabel("Impression Bon de Versement"))
        
        self.print_group = QButtonGroup(self)
        self.radio_2ex = QRadioButton("02 Exemplaires")
        self.radio_2ex.setChecked(True)
        self.radio_1ex = QRadioButton("01 Exemplaire")
        self.radio_no_print = QRadioButton("Ne pas Imprimer")
        
        self.print_group.addButton(self.radio_2ex)
        self.print_group.addButton(self.radio_1ex)
        self.print_group.addButton(self.radio_no_print)
        
        right_layout.addWidget(self.radio_2ex)
        right_layout.addWidget(self.radio_1ex)
        right_layout.addWidget(self.radio_no_print)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #CFD8DC;")
        right_layout.addWidget(sep2)

        # Papier section
        right_layout.addWidget(QLabel("Papier"))
        self.paper_group = QButtonGroup(self)
        self.chk_a4 = QCheckBox("A4")
        self.chk_a4.setChecked(True)
        self.chk_a5 = QCheckBox("A5")
        self.chk_tk = QCheckBox("TK")
        
        # Simple mutual exclusion for paper options
        def on_paper_toggle(state, chk):
            if state == Qt.Checked:
                for c in [self.chk_a4, self.chk_a5, self.chk_tk]:
                    if c != chk:
                        c.setChecked(False)
        
        self.chk_a4.stateChanged.connect(lambda s: on_paper_toggle(s, self.chk_a4))
        self.chk_a5.stateChanged.connect(lambda s: on_paper_toggle(s, self.chk_a5))
        self.chk_tk.stateChanged.connect(lambda s: on_paper_toggle(s, self.chk_tk))

        right_layout.addWidget(self.chk_a4)
        right_layout.addWidget(self.chk_a5)
        right_layout.addWidget(self.chk_tk)

        right_layout.addStretch()

        # Valider (F10) Button
        self.valider_btn = QPushButton("✅ Valider (F10)")
        self.valider_btn.setMinimumHeight(45)
        self.valider_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1B5E20;
            }
        """)
        self.valider_btn.clicked.connect(self._on_validate)
        right_layout.addWidget(self.valider_btn)

        # Annuler (ESC) Button
        self.annuler_btn = QPushButton("❌ Annuler (ESC)")
        self.annuler_btn.setMinimumHeight(45)
        self.annuler_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: white;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        self.annuler_btn.clicked.connect(self.reject)
        right_layout.addWidget(self.annuler_btn)

        # F7 Caisse Button
        self.caisse_btn = QPushButton("🖨️ F7 ((Caisse))")
        self.caisse_btn.setMinimumHeight(40)
        self.caisse_btn.setStyleSheet("""
            QPushButton {
                background-color: #78909C;
                color: white;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #607D8B;
            }
        """)
        self.caisse_btn.clicked.connect(self._open_caisse)
        right_layout.addWidget(self.caisse_btn)

        main_layout.addWidget(right_panel)

    def _setup_shortcuts(self):
        # Keyboard shortcuts
        QShortcut(QKeySequence("F10"), self).activated.connect(self._on_validate)
        QShortcut(QKeySequence("F7"), self).activated.connect(self._open_caisse)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.reject)

    def _refresh_printers(self):
        try:
            from PySide6.QtPrintSupport import QPrinterInfo
            printers = [p.printerName() for p in QPrinterInfo.availablePrinters()]
            if printers:
                self.printer_combo.clear()
                self.printer_combo.addItems(printers)
                default_p = QPrinterInfo.defaultPrinterName()
                if default_p:
                    self.printer_combo.setCurrentText(default_p)
                QMessageBox.information(self, "Imprimantes", "Liste des imprimantes actualisée.")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible d'actualiser les imprimantes: {str(e)}")

    def _load_clients(self):
        # Fetch clients from database
        self.client_combo.clear()
        self.clients_list = self.db_session.query(Client).filter(Client.is_deleted == 0, Client.is_active == 1).order_by(Client.name).all()
        
        self.client_combo.addItem("Sélectionnez un client...", None)
        for client in self.clients_list:
            self.client_combo.addItem(f"{client.code} — {client.name}", client.id)

    def _on_client_search_text_changed(self, text):
        pass

    def _on_client_selected(self, index):
        client_id = self.client_combo.itemData(index)
        if client_id is None:
            self.selected_client = None
            self._ancien_credit_val = 0.0
            self.ancien_credit_lbl.setText("0,00 DA")
            self.ancien_credit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32; padding: 4px;")
            self._update_calculation()
            return

        self.selected_client = self.db_session.query(Client).filter(Client.id == client_id).first()
        self._load_client_credit()

    def _load_client_credit(self):
        if not self.selected_client:
            return
        
        # Calculate ancien credit (all non-written-off debts)
        debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "CLIENT",
            Debt.entity_id == self.selected_client.id,
            Debt.status != "WRITTEN_OFF",
            Debt.is_deleted == 0
        ).all()
        
        val = sum(d.total_amount - d.paid_amount for d in debts)
        self._ancien_credit_val = val

        if val < -0.01:
            self.ancien_credit_lbl.setText(f"Crédit: {abs(val):,.2f} DA".replace(",", " "))
            self.ancien_credit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1565C0; padding: 4px;")  # blue
        elif val < 0.01:
            self.ancien_credit_lbl.setText("0,00 DA")
            self.ancien_credit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32; padding: 4px;")  # green
        else:
            self.ancien_credit_lbl.setText(f"{val:,.2f} DA".replace(",", " "))
            self.ancien_credit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #C62828; padding: 4px;")  # red
        self._update_calculation()

    def _on_amount_changed(self, val):
        # Update large display
        self.amount_display_lbl.setText(f"{val:,.2f} DA".replace(",", " "))
        
        # Update Arabic words
        if val == 0:
            self.arabic_words_lbl.setText("ZERO")
        else:
            words = number_to_arabic_words(val)
            self.arabic_words_lbl.setText(words)

        self._update_calculation()

    def _on_cheque_state_changed(self, state):
        self.cheque_number_input.setEnabled(state == Qt.Checked)

    def _update_calculation(self):
        # Calculate new credit using stored numeric value (avoids label parsing issues)
        ancien = self._ancien_credit_val

        montant = self.amount_input.value()
        remise = self.remise_input.value()

        if self.remboursement_checkbox.isChecked():
            # Refund to client actually increases client credit (they owe us more or we paid them back)
            nouveau = ancien + montant
        else:
            # Versement and discount reduce what client owes
            nouveau = ancien - montant - remise

        if nouveau < -0.01:
            # Client has overpaid — they have a credit (avoir)
            self.nouveau_credit_lbl.setText(f"Crédit: {abs(nouveau):,.2f} DA".replace(",", " "))
            self.nouveau_credit_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #1565C0; padding: 4px;")  # blue
        elif nouveau < 0.01:
            # Settled
            self.nouveau_credit_lbl.setText("0,00 DA — Soldé")
            self.nouveau_credit_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #2E7D32; padding: 4px;")  # green
        else:
            # Client still owes
            self.nouveau_credit_lbl.setText(f"{nouveau:,.2f} DA".replace(",", " "))
            self.nouveau_credit_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #C62828; padding: 4px;")  # red

    def _open_client_picker(self):
        # SECTION 3 - Client Picker (Will be implemented in Section 3, for now simple lookup)
        from ui.dialogs.client_picker_dialog import ClientPickerDialog
        picker = ClientPickerDialog(self.user, parent=self)
        if picker.exec() and picker.selected_client:
            # Find and select client in combobox
            cl = picker.selected_client
            for idx in range(self.client_combo.count()):
                if self.client_combo.itemData(idx) == cl.id:
                    self.client_combo.setCurrentIndex(idx)
                    break

    def _open_caisse(self):
        # F7 shortcuts to Caisse
        from ui.pages.cash_register_page import CashRegisterPage
        QMessageBox.information(self, "Caisse", "Redirection vers la caisse...")

    def _on_validate(self):
        if not self.selected_client:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un client.")
            return

        montant = self.amount_input.value()
        remise = self.remise_input.value()

        if montant <= 0 and remise <= 0:
            QMessageBox.warning(self, "Erreur", "Le montant ou la remise doit être supérieur à 0.")
            return

        # Payment method
        method = "CHEQUE" if self.cheque_checkbox.isChecked() else "ESPECES"
        ref_num = self.cheque_number_input.text().strip() if method == "CHEQUE" else self.recu_input.text().strip()

        # Validate cash register session if Espèces
        if method == "ESPECES":
            from app.repositories.finance_repository import CashRegisterRepository
            cash_repo = CashRegisterRepository(self.db_session)
            if not cash_repo.get_active_session():
                QMessageBox.warning(self, "Caisse Fermée", "La caisse doit être ouverte pour encaisser en espèces.")
                return

        try:
            total_deduction = montant + remise
            
            # Find unpaid/partial debts
            debts = self.db_session.query(Debt).filter(
                Debt.entity_type == "CLIENT",
                Debt.entity_id == self.selected_client.id,
                Debt.status.in_(["PENDING", "PARTIAL"]),
                Debt.is_deleted == 0
            ).order_by(Debt.created_at.asc()).all()

            remaining_to_deduct = total_deduction

            for d in debts:
                if remaining_to_deduct <= 0:
                    break

                deduct_now = min(remaining_to_deduct, d.remaining_amount)
                
                # Check if this is a refund
                if self.remboursement_checkbox.isChecked():
                    # Refunds increase debt, which is opposite of recording a payment!
                    # Actually, if we are refunding them, we can increase their debt or create a new negative payment.
                    # But if we want to reduce their payment, we can just create a negative payment or a new debt.
                    pass
                else:
                    # Normal versement - record a payment
                    self.debt_service.record_payment(
                        debt_id=d.id,
                        amount=deduct_now,
                        method=method,
                        user_id=self.user.id,
                        reference=ref_num,
                        notes=self.observation_input.text().strip() or "Versement Client"
                    )
                remaining_to_deduct -= deduct_now

            # If there's leftover versement or no debts at all, register a credit note / negative debt entry
            if remaining_to_deduct > 0 and not self.remboursement_checkbox.isChecked():
                # Create a new debt record representing negative debt (advance credit payment)
                from app.constants import DebtStatus
                new_debt = Debt(
                    entity_type="CLIENT",
                    entity_id=self.selected_client.id,
                    reference_type="VERSEMENT",
                    reference_id=0,
                    total_amount=0.0,
                    paid_amount=remaining_to_deduct,
                    remaining_amount=-remaining_to_deduct,
                    status=DebtStatus.PAID.value,
                    notes=self.observation_input.text().strip() or "Versement anticipé / Crédit Client"
                )
                self.db_session.add(new_debt)
                self.db_session.commit()

                # Record the cash register deposit if applicable
                if method == "ESPECES":
                    from app.repositories.finance_repository import CashRegisterRepository
                    cash_repo = CashRegisterRepository(self.db_session)
                    active = cash_repo.get_active_session()
                    if active:
                        active.total_deposits += remaining_to_deduct
                        active.expected_balance += remaining_to_deduct
                        self.db_session.commit()

            QMessageBox.information(self, "Succès", "Le versement a été enregistré avec succès.")
            self.accept()

        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
