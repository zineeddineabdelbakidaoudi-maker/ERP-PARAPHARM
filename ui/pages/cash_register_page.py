"""
ParaFarm ERP — Cash Register Page
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDoubleSpinBox, QFrame, QFormLayout, QDialog
)
from PySide6.QtCore import Qt

from app.core.database import get_session
from app.services.finance_service import FinanceService
from app.core.exceptions import BusinessRuleError
from app.constants import CashRegisterStatus


class ExpenseDialog(QDialog):
    def __init__(self, finance_service, user_id, parent=None):
        super().__init__(parent)
        self.finance_service = finance_service
        self.user_id = user_id
        self.setWindowTitle("Enregistrer une Dépense")
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Ex: Loyer, Fournitures, etc.")
        layout.addRow("Catégorie:", self.cat_input)

        self.desc_input = QLineEdit()
        layout.addRow("Description:", self.desc_input)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(9999999.99)
        self.amount_input.setSuffix(" DA")
        layout.addRow("Montant:", self.amount_input)

        btn_box = QHBoxLayout()
        cancel = QPushButton("Annuler")
        cancel.setProperty("variant", "secondary")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Enregistrer")
        save.clicked.connect(self._on_save)
        
        btn_box.addWidget(cancel)
        btn_box.addWidget(save)
        layout.addRow(btn_box)

    def _on_save(self):
        cat = self.cat_input.text().strip()
        desc = self.desc_input.text().strip()
        amount = self.amount_input.value()
        
        if not cat or not desc or amount <= 0:
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs.")
            return

        try:
            self.finance_service.record_expense(self.user_id, cat, desc, amount)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


class CashRegisterPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.finance_service = FinanceService(self.db_session)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Status Banner
        self.banner = QFrame()
        self.banner.setProperty("class", "card")
        banner_layout = QHBoxLayout(self.banner)
        
        self.status_label = QLabel("État de la caisse: INCONNU")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        banner_layout.addWidget(self.status_label)
        
        banner_layout.addStretch()
        
        self.action_btn = QPushButton("Action")
        self.action_btn.setMinimumWidth(150)
        self.action_btn.clicked.connect(self._toggle_session)
        banner_layout.addWidget(self.action_btn)
        
        layout.addWidget(self.banner)

        # Stats Grid
        self.stats_frame = QFrame()
        stats_layout = QHBoxLayout(self.stats_frame)
        
        self.lbl_opening = self._create_stat_label("Fond de Caisse")
        self.lbl_sales = self._create_stat_label("Ventes (Espèces)")
        self.lbl_expenses = self._create_stat_label("Dépenses")
        self.lbl_expected = self._create_stat_label("Solde Théorique")
        
        stats_layout.addWidget(self.lbl_opening)
        stats_layout.addWidget(self.lbl_sales)
        stats_layout.addWidget(self.lbl_expenses)
        stats_layout.addWidget(self.lbl_expected)
        
        layout.addWidget(self.stats_frame)

        # Expenses Actions
        exp_layout = QHBoxLayout()
        lbl = QLabel("Dépenses de la session")
        lbl.setProperty("class", "sectionTitle")
        exp_layout.addWidget(lbl)
        exp_layout.addStretch()
        
        self.add_exp_btn = QPushButton("➕ Nouvelle Dépense")
        self.add_exp_btn.clicked.connect(self._add_expense)
        exp_layout.addWidget(self.add_exp_btn)
        
        layout.addLayout(exp_layout)

        # Expenses Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Heure", "Catégorie", "Description", "Montant"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def _create_stat_label(self, title):
        frame = QFrame()
        frame.setProperty("class", "card")
        l = QVBoxLayout(frame)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #757575;")
        val_lbl = QLabel("0.00 DA")
        val_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #1B5E20;")
        l.addWidget(title_lbl)
        l.addWidget(val_lbl)
        frame.val_lbl = val_lbl
        return frame

    def refresh_data(self):
        session = self.finance_service.cash_repo.get_active_session()
        
        if session:
            self.status_label.setText("🟢 CAISSE OUVERTE")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2E7D32;")
            self.action_btn.setText("Fermer la Caisse")
            self.action_btn.setProperty("variant", "danger")
            self.action_btn.style().unpolish(self.action_btn)
            self.action_btn.style().polish(self.action_btn)
            
            self.add_exp_btn.setEnabled(True)
            
            self.lbl_opening.val_lbl.setText(f"{session.opening_balance:,.2f} DA")
            self.lbl_sales.val_lbl.setText(f"{session.total_sales_cash:,.2f} DA")
            self.lbl_expenses.val_lbl.setText(f"{session.total_expenses:,.2f} DA")
            self.lbl_expected.val_lbl.setText(f"{session.expected_balance:,.2f} DA")
            
            # Load expenses
            expenses = self.finance_service.expense_repo.get_by_session(session.id)
            self.table.setRowCount(0)
            for e in expenses:
                row = self.table.rowCount()
                self.table.insertRow(row)
                time_str = e.created_at.split(" ")[1][:5]
                self.table.setItem(row, 0, QTableWidgetItem(time_str))
                self.table.setItem(row, 1, QTableWidgetItem(e.category))
                self.table.setItem(row, 2, QTableWidgetItem(e.description))
                self.table.setItem(row, 3, QTableWidgetItem(f"{e.amount:.2f} DA"))
                
        else:
            self.status_label.setText("🔴 CAISSE FERMÉE")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #C62828;")
            self.action_btn.setText("Ouvrir la Caisse")
            self.action_btn.setProperty("variant", "success")
            self.action_btn.style().unpolish(self.action_btn)
            self.action_btn.style().polish(self.action_btn)
            
            self.add_exp_btn.setEnabled(False)
            
            self.lbl_opening.val_lbl.setText("0.00 DA")
            self.lbl_sales.val_lbl.setText("0.00 DA")
            self.lbl_expenses.val_lbl.setText("0.00 DA")
            self.lbl_expected.val_lbl.setText("0.00 DA")
            self.table.setRowCount(0)

    def _toggle_session(self):
        session = self.finance_service.cash_repo.get_active_session()
        if session:
            # Close Session
            import PySide6.QtWidgets as qw
            val, ok = qw.QInputDialog.getDouble(self, "Fermeture de Caisse", "Montant compté en caisse (Espèces):", session.expected_balance, 0, 9999999, 2)
            if ok:
                try:
                    self.finance_service.close_session(self.user.id, val)
                    QMessageBox.information(self, "Succès", "Caisse fermée avec succès.")
                    self.refresh_data()
                except Exception as e:
                    QMessageBox.warning(self, "Erreur", str(e))
        else:
            # Open Session
            import PySide6.QtWidgets as qw
            val, ok = qw.QInputDialog.getDouble(self, "Ouverture de Caisse", "Fond de caisse initial:", 0, 0, 9999999, 2)
            if ok:
                try:
                    self.finance_service.open_session(self.user.id, val)
                    QMessageBox.information(self, "Succès", "Caisse ouverte avec succès.")
                    self.refresh_data()
                except Exception as e:
                    QMessageBox.warning(self, "Erreur", str(e))

    def _add_expense(self):
        d = ExpenseDialog(self.finance_service, self.user.id, self)
        if d.exec():
            self.refresh_data()
