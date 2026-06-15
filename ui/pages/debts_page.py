from ui.utils.widgets import SearchableComboBox
# -*- coding: utf-8 -*-
"""
ParaFarm ERP — Supplier Debts Page (États des Dettes Fournisseurs)
Completely rebuilt as described in SECTION 8, including integration with SupplierFicheDialog.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDoubleSpinBox, QComboBox, QFrame, QRadioButton, QButtonGroup,
    QGridLayout, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QBrush, QKeySequence, QShortcut

from app.core.database import get_session
from app.models.supplier import Supplier
from app.models.debt import Debt, Payment
from app.models.purchase import Purchase
from app.models.supplier_return import SupplierReturn
from ui.dialogs.supplier_payment_dialog import SupplierPaymentDialog
from ui.dialogs.supplier_dialog import SupplierDialog
from ui.dialogs.supplier_fiche_dialog import SupplierFicheDialog

class RemiseGlobaleDialog(QDialog):
    def __init__(self, db_session, user, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.setWindowTitle("Remise Globale Fournisseur")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #F5F7FA; }
            QLabel { font-weight: bold; }
            QLineEdit, QComboBox, QDoubleSpinBox { padding: 5px; border: 1px solid #CCC; border-radius: 4px; }
            QPushButton { padding: 6px 12px; font-weight: bold; border-radius: 4px; }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.supplier_combo = SearchableComboBox()
        suppliers = self.db_session.query(Supplier).filter(Supplier.is_deleted == 0, Supplier.is_active == 1).order_by(Supplier.name).all()
        self.supplier_combo.addItem("Sélectionnez un fournisseur...", None)
        for s in suppliers:
            self.supplier_combo.addItem(s.name, s.id)
        layout.addRow("Fournisseur :", self.supplier_combo)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(99999999.0)
        self.amount_input.setDecimals(2)
        self.amount_input.setSuffix(" DA")
        layout.addRow("Montant Remise :", self.amount_input)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Observation / Motif...")
        layout.addRow("Notes :", self.notes_input)

        btn_layout = QHBoxLayout()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Confirmer")
        save.setStyleSheet("background-color: #4CAF50; color: white;")
        save.clicked.connect(self._on_save)
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addRow(btn_layout)

    def _on_save(self):
        supp_id = self.supplier_combo.currentData()
        if not supp_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un fournisseur.")
            return
        amount = self.amount_input.value()
        if amount <= 0:
            QMessageBox.warning(self, "Erreur", "Le montant doit être supérieur à 0.")
            return

        try:
            from app.services.debt_service import DebtService
            debt_service = DebtService(self.db_session)
            
            debts = self.db_session.query(Debt).filter(
                Debt.entity_type == "SUPPLIER",
                Debt.entity_id == supp_id,
                Debt.status.in_(["PENDING", "PARTIAL"]),
                Debt.is_deleted == 0
            ).order_by(Debt.created_at.asc()).all()

            remaining = amount
            for d in debts:
                if remaining <= 0:
                    break
                deduct = min(remaining, d.remaining_amount)
                debt_service.record_payment(
                    debt_id=d.id,
                    amount=deduct,
                    method="ESPECES",
                    user_id=self.user.id,
                    reference="REMISE_GLOBALE",
                    notes=self.notes_input.text().strip() or "Remise Globale Fournisseur"
                )
                remaining -= deduct

            self.db_session.commit()
            QMessageBox.information(self, "Succès", "Remise globale enregistrée avec succès.")
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", str(e))


class DebtsPage(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        
        self.setStyleSheet("""
            QWidget { background-color: #F4F6F9; }
            QLabel { font-size: 13px; color: #333; }
            QFrame#card { background-color: white; border: 1px solid #CFD8DC; border-radius: 4px; }
            QTableWidget { background-color: white; gridline-color: #E0E0E0; border: 1px solid #CFD8DC; }
            QHeaderView::section { background-color: #F0F0F0; color: black; font-weight: bold; border: 1px solid #CFD8DC; padding: 4px; }
            QPushButton { font-weight: bold; border-radius: 4px; padding: 6px 12px; }
        """)
        
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # --- HEADER ROW ---
        header_layout = QHBoxLayout()
        
        title_lbl = QLabel("DETTES")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #1E88E5;")
        header_layout.addWidget(title_lbl)
        
        header_layout.addSpacing(30)
        
        # Period toggle
        self.period_group = QButtonGroup(self)
        self.rad_tous = QRadioButton("Tous")
        self.rad_tous.setChecked(True)
        self.rad_periode = QRadioButton("Par Période")
        self.period_group.addButton(self.rad_tous)
        self.period_group.addButton(self.rad_periode)
        
        header_layout.addWidget(self.rad_tous)
        header_layout.addWidget(self.rad_periode)
        
        header_layout.addStretch()
        
        # Action Buttons
        self.btn_chercher = QPushButton("🔍 Chercher")
        self.btn_chercher.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_chercher.clicked.connect(self.refresh_data)
        
        self.btn_imprimer = QPushButton("🖨️ Imprimer")
        self.btn_imprimer.setStyleSheet("background-color: #2196F3; color: white;")
        
        self.btn_fermer = QPushButton("❌ Fermer")
        self.btn_fermer.setStyleSheet("background-color: #F44336; color: white;")
        self.btn_fermer.clicked.connect(self._close_page)
        
        header_layout.addWidget(self.btn_chercher)
        header_layout.addWidget(self.btn_imprimer)
        header_layout.addWidget(self.btn_fermer)
        
        main_layout.addLayout(header_layout)

        # --- DATA GRID ---
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Nom Fournisseur", "Solde Initial", "Total des achats", "Total des versements",
            "Total retours", "Les remises", "Solde Final", "Dernier Achat",
            "Date Dernier Versement", "Chiffre Affaire"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        main_layout.addWidget(self.table, stretch=1)

        # --- BOTTOM PANEL ---
        bottom_layout = QHBoxLayout()
        
        # Left side stats
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # Credits Box
        credits_frame = QFrame()
        credits_frame.setObjectName("card")
        credits_lay = QVBoxLayout(credits_frame)
        credits_lay.setContentsMargins(10, 8, 10, 8)
        credits_lay.addWidget(QLabel("CRÉDITS FOURNISSEURS"))
        self.credits_display = QLabel("0,00 DA")
        self.credits_display.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976D2;")
        credits_lay.addWidget(self.credits_display)
        stats_layout.addWidget(credits_frame)
        
        # Real Debts Box
        debts_frame = QFrame()
        debts_frame.setObjectName("card")
        debts_frame.setStyleSheet("background-color: black; border-radius: 4px;")
        debts_lay = QVBoxLayout(debts_frame)
        debts_lay.setContentsMargins(15, 8, 15, 8)
        lbl_debts = QLabel("TOTAL DES DETTES RÉELS")
        lbl_debts.setStyleSheet("color: #00E676; background-color: black; font-weight: bold; font-size: 18pt;")
        debts_lay.addWidget(lbl_debts)
        self.debts_display = QLabel("0,00 DA")
        self.debts_display.setStyleSheet("font-size: 18pt; font-weight: bold; color: #00E676; background-color: black;")
        debts_lay.addWidget(self.debts_display)
        stats_layout.addWidget(debts_frame)
        
        bottom_layout.addLayout(stats_layout, stretch=1)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        self.btn_fiche = QPushButton("🕐 Fiche Fournisseur")
        self.btn_fiche.setStyleSheet("background-color: #00ACC1; color: white;")
        self.btn_fiche.clicked.connect(self._open_fiche_fournisseur)
        
        self.btn_vers = QPushButton("+ Versement Fournisseur")
        self.btn_vers.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_vers.clicked.connect(self._open_versement)
        
        self.btn_remise = QPushButton("+ Remise Globale")
        self.btn_remise.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_remise.clicked.connect(self._open_remise)
        
        actions_layout.addWidget(self.btn_fiche)
        actions_layout.addWidget(self.btn_vers)
        actions_layout.addWidget(self.btn_remise)
        
        bottom_layout.addLayout(actions_layout)
        
        main_layout.addLayout(bottom_layout)

    def refresh_data(self):
        self.table.setRowCount(0)
        
        suppliers = self.db_session.query(Supplier).filter(Supplier.is_deleted == 0).order_by(Supplier.name).all()
        
        total_credits = 0.0
        total_debts_reels = 0.0
        
        sums = {
            "solde_init": 0.0,
            "achats": 0.0,
            "versements": 0.0,
            "retours": 0.0,
            "remises": 0.0,
            "solde_final": 0.0,
            "ca": 0.0
        }

        for s in suppliers:
            # 1. Solde Final (outstanding debt)
            debts = self.db_session.query(Debt).filter(
                Debt.entity_type == "SUPPLIER",
                Debt.entity_id == s.id,
                Debt.status != "WRITTEN_OFF",
                Debt.is_deleted == 0
            ).all()
            solde_final = sum(d.total_amount - d.paid_amount for d in debts)
            
            # 2. Total des achats
            purchases = self.db_session.query(Purchase).filter(
                Purchase.supplier_id == s.id,
                Purchase.status != "CANCELLED",
                Purchase.is_deleted == 0
            ).all()
            total_achats = sum(p.total_amount for p in purchases)
            
            # 3. Total des versements
            payments = self.db_session.query(Payment).join(Debt).filter(
                Debt.entity_type == "SUPPLIER",
                Debt.entity_id == s.id,
                Debt.is_deleted == 0
            ).all()
            total_versements = sum(pay.amount for pay in payments)
            
            # 4. Total retours
            returns = self.db_session.query(SupplierReturn).filter(
                SupplierReturn.supplier_id == s.id,
                SupplierReturn.status == "COMPLETED"
            ).all()
            total_retours = sum(ret.total_amount for ret in returns)
            
            # 5. Les remises
            remises_list = [pay.amount for pay in payments if pay.reference_number == "REMISE_GLOBALE"]
            total_remises = sum(remises_list)
            
            # 6. Solde Initial
            solde_initial = solde_final - total_achats + total_versements + total_retours
            
            # 7. Dernier Achat
            dernier_achat = "—"
            last_p = self.db_session.query(Purchase).filter(
                Purchase.supplier_id == s.id,
                Purchase.status != "CANCELLED",
                Purchase.is_deleted == 0
            ).order_by(Purchase.created_at.desc()).first()
            if last_p:
                ref_br = last_p.purchase_number
                if last_p.invoice_number:
                    ref_br += f" (Inv: {last_p.invoice_number})"
                dernier_achat = ref_br
                
            # 8. Date Dernier Versement
            date_dernier_vers = "—"
            last_pay = self.db_session.query(Payment).join(Debt).filter(
                Debt.entity_type == "SUPPLIER",
                Debt.entity_id == s.id,
                Debt.is_deleted == 0
            ).order_by(Payment.payment_date.desc()).first()
            if last_pay:
                date_dernier_vers = last_pay.payment_date.split(' ')[0]
                
            # 9. Chiffre Affaire
            ca = total_achats

            # Track global statistics
            if solde_final < 0:
                total_credits += abs(solde_final)
            else:
                total_debts_reels += solde_final

            # Add row to table
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(s.name))
            self.table.setItem(row, 1, self._num_item(solde_initial))
            self.table.setItem(row, 2, self._num_item(total_achats))
            self.table.setItem(row, 3, self._num_item(total_versements))
            self.table.setItem(row, 4, self._num_item(total_retours))
            self.table.setItem(row, 5, self._num_item(total_remises))
            
            # Solde Final display with proper sign convention
            if solde_final > 0.01:
                final_item = self._num_item(solde_final)
                final_item.setBackground(QBrush(QColor("#FFF9C4")))  # Yellow — owes
            elif solde_final < -0.01:
                final_item = QTableWidgetItem(f"Avoir: {abs(solde_final):,.2f}".replace(",", " "))
                final_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                final_item.setBackground(QBrush(QColor("#E3F2FD")))  # Light blue — overpaid/credit
                final_item.setForeground(QBrush(QColor("#1565C0")))  # Blue text
            else:
                final_item = QTableWidgetItem("Soldé")
                final_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                final_item.setBackground(QBrush(QColor("#E8F5E9")))  # Light green — settled
                final_item.setForeground(QBrush(QColor("#2E7D32")))  # Green text
            self.table.setItem(row, 6, final_item)
            
            self.table.setItem(row, 7, QTableWidgetItem(dernier_achat))
            self.table.setItem(row, 8, QTableWidgetItem(date_dernier_vers))
            self.table.setItem(row, 9, self._num_item(ca))

            # Store for sums
            sums["solde_init"] += solde_initial
            sums["achats"] += total_achats
            sums["versements"] += total_versements
            sums["retours"] += total_retours
            sums["remises"] += total_remises
            sums["solde_final"] += solde_final
            sums["ca"] += ca

        # Add TOTAUX row
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        lbl_totaux = QTableWidgetItem("TOTAUX")
        lbl_totaux.setFont(QFont("Arial", 10, QFont.Bold))
        self.table.setItem(row, 0, lbl_totaux)
        
        for col_idx, key in enumerate(["solde_init", "achats", "versements", "retours", "remises", "solde_final"]):
            item = self._num_item(sums[key])
            item.setFont(QFont("Arial", 10, QFont.Bold))
            self.table.setItem(row, col_idx + 1, item)
            
        self.table.setItem(row, 7, QTableWidgetItem(""))
        self.table.setItem(row, 8, QTableWidgetItem(""))
        
        ca_item = self._num_item(sums["ca"])
        ca_item.setFont(QFont("Arial", 10, QFont.Bold))
        self.table.setItem(row, 9, ca_item)

        # Update stats
        self.credits_display.setText(f"{total_credits:,.2f} DA".replace(",", " "))
        self.debts_display.setText(f"{total_debts_reels:,.2f} DA".replace(",", " "))

    def _num_item(self, val):
        item = QTableWidgetItem(f"{val:,.2f}".replace(",", " "))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    def _open_fiche_fournisseur(self):
        idx = self.table.currentRow()
        if idx < 0 or idx >= self.table.rowCount() - 1:
            # No specific supplier selected, just open empty or let them select
            dlg = SupplierFicheDialog(self.user, parent=self)
            dlg.exec()
            self.refresh_data()
            return
            
        supp_name = self.table.item(idx, 0).text()
        s = self.db_session.query(Supplier).filter(Supplier.name == supp_name).first()
        if s:
            dlg = SupplierFicheDialog(self.user, supplier=s, parent=self)
            dlg.exec()
            self.refresh_data()

    def _open_versement(self):
        dlg = SupplierPaymentDialog(self.user, self)
        if dlg.exec():
            self.refresh_data()

    def _open_remise(self):
        dlg = RemiseGlobaleDialog(self.db_session, self.user, self)
        if dlg.exec():
            self.refresh_data()

    def _close_page(self):
        parent = self.parentWidget()
        while parent:
            if parent.inherits("QTabWidget"):
                parent.removeTab(parent.indexOf(self))
                break
            parent = parent.parentWidget()

    def _on_print(self):
        from app.utils.pdf_exporter import PDFExporter
        import os, tempfile
        from PySide6.QtWidgets import QMessageBox
        
        headers = []
        for j in range(self.table.columnCount()):
            headers.append(self.table.horizontalHeaderItem(j).text())
            
        data = []
        for i in range(self.table.rowCount()):
            row = []
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
            
        pdf_path = os.path.join(tempfile.gettempdir(), "etat_dettes_fournisseurs.pdf")
        
        try:
            PDFExporter.export_table_to_pdf(
                file_path=pdf_path,
                title="ETAT DES DETTES FOURNISSEURS",
                headers=headers,
                data=data,
                filters="Toutes les dettes" if self.rad_tous.isChecked() else "Par période",
                is_landscape=True
            )
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'impression: {str(e)}")
