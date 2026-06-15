from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Additional Module Pages (Section 10)
Production, Personnel, Journal (Accounting), Statistics Overview.
"""
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDateEdit, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session


class ProductionPage(QWidget):
    """Placeholder for production orders module."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("🏭 Production — Ordres de Fabrication")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher...")
        self.search_input.setMinimumWidth(250)
        toolbar.addWidget(self.search_input)
        toolbar.addStretch()
        add_btn = QPushButton("➕ Nouvel Ordre")
        toolbar.addWidget(add_btn)
        refresh_btn = QPushButton("🔄 Actualiser")
        toolbar.addWidget(refresh_btn)
        export_btn = QPushButton("📊 CSV")
        toolbar.addWidget(export_btn)
        layout.addLayout(toolbar)

        cols = ["N° Ordre", "Date", "Produit", "Quantité", "Statut", "Responsable", "Actions"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        # Empty state
        self.table.insertRow(0)
        empty = QTableWidgetItem("Module Production — En cours de développement")
        empty.setTextAlignment(Qt.AlignCenter)
        empty.setForeground(Qt.gray)
        self.table.setItem(0, 3, empty)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("0 ordres de production"))
        bottom.addStretch()
        layout.addLayout(bottom)


class PersonnelPage(QWidget):
    """Placeholder for employee management module."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("👥 Personnel — Gestion des Employés")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher un employé...")
        self.search_input.setMinimumWidth(250)
        toolbar.addWidget(self.search_input)
        toolbar.addStretch()
        add_btn = QPushButton("➕ Nouvel Employé")
        toolbar.addWidget(add_btn)
        refresh_btn = QPushButton("🔄 Actualiser")
        toolbar.addWidget(refresh_btn)
        export_btn = QPushButton("📊 CSV")
        toolbar.addWidget(export_btn)
        layout.addLayout(toolbar)

        cols = ["Matricule", "Nom Complet", "Poste", "Département", "Date Embauche", "Téléphone", "Statut", "Actions"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        self.table.insertRow(0)
        empty = QTableWidgetItem("Module Personnel — En cours de développement")
        empty.setTextAlignment(Qt.AlignCenter)
        empty.setForeground(Qt.gray)
        self.table.setItem(0, 3, empty)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("0 employés"))
        bottom.addStretch()
        layout.addLayout(bottom)


class JournalComptablePage(QWidget):
    """Accounting journal — daily transaction log across all modules."""
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

        title = QLabel("📒 Journal Comptable — Transactions Quotidiennes")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)

        self.module_filter = SearchableComboBox()
        self.module_filter.addItems(["Tous", "Ventes", "Achats", "Banque", "Caisse", "Dépenses"])
        self.module_filter.currentTextChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.module_filter)

        toolbar.addWidget(QLabel("Du:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate())
        self.date_from.dateChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.date_from)
        toolbar.addWidget(QLabel("Au:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.date_to)

        toolbar.addStretch()
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        export_btn = QPushButton("📊 CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)
        layout.addLayout(toolbar)

        cols = ["Date/Heure", "Module", "N° Référence", "Description", "Débit", "Crédit", "Utilisateur"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 écritures")
        self.lbl_count.setStyleSheet("color: #757575; font-size: 12px;")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()
        self.lbl_debit = QLabel("Total Débit: 0.00 DA")
        self.lbl_debit.setStyleSheet("color: #C62828; font-weight: 600;")
        bottom.addWidget(self.lbl_debit)
        self.lbl_credit = QLabel("Total Crédit: 0.00 DA")
        self.lbl_credit.setStyleSheet("color: #2E7D32; font-weight: 600;")
        bottom.addWidget(self.lbl_credit)
        layout.addLayout(bottom)

    def refresh_data(self):
        self.table.setRowCount(0)
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to = self.date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        module = self.module_filter.currentText()
        search = self.search_input.text().strip().lower()

        entries = []

        # Collect from sales
        if module in ("Tous", "Ventes"):
            from app.models.sale import Sale
            sales = self.db_session.query(Sale).filter(
                Sale.status == "COMPLETED",
                Sale.sale_date >= d_from, Sale.sale_date <= d_to
            ).all()
            for s in sales:
                entries.append({
                    "date": s.sale_date, "module": "Ventes", "ref": s.sale_number,
                    "desc": f"Vente comptoir", "debit": 0, "credit": s.total_amount,
                    "user": f"User #{s.cashier_id}"
                })

        # Collect from purchases
        if module in ("Tous", "Achats"):
            from app.models.purchase import Purchase
            purchases = self.db_session.query(Purchase).filter(
                Purchase.is_deleted == 0,
                Purchase.purchase_date >= d_from, Purchase.purchase_date <= d_to
            ).all()
            for p in purchases:
                entries.append({
                    "date": p.purchase_date, "module": "Achats", "ref": p.purchase_number,
                    "desc": f"Achat fournisseur", "debit": p.total_amount, "credit": 0,
                    "user": "—"
                })

        # Bank deposits
        if module in ("Tous", "Banque"):
            from app.models.bank import BankDeposit, BankWithdrawal
            deps = self.db_session.query(BankDeposit).filter(
                BankDeposit.is_deleted == 0,
                BankDeposit.deposit_date >= d_from, BankDeposit.deposit_date <= d_to
            ).all()
            for d in deps:
                entries.append({
                    "date": d.deposit_date, "module": "Banque", "ref": d.reference,
                    "desc": "Versement bancaire", "debit": 0, "credit": d.amount,
                    "user": f"User #{d.recorded_by}"
                })
            wds = self.db_session.query(BankWithdrawal).filter(
                BankWithdrawal.is_deleted == 0,
                BankWithdrawal.withdrawal_date >= d_from, BankWithdrawal.withdrawal_date <= d_to
            ).all()
            for w in wds:
                entries.append({
                    "date": w.withdrawal_date, "module": "Banque", "ref": w.reference,
                    "desc": "Retrait bancaire", "debit": w.amount, "credit": 0,
                    "user": f"User #{w.recorded_by}"
                })

        # Expenses
        if module in ("Tous", "Dépenses"):
            from app.models.cash_register import Expense
            expenses = self.db_session.query(Expense).filter(
                Expense.is_deleted == 0,
                Expense.expense_date >= d_from, Expense.expense_date <= d_to
            ).all()
            for e in expenses:
                entries.append({
                    "date": e.expense_date, "module": "Dépenses", "ref": f"DEP-{e.id}",
                    "desc": e.description, "debit": e.amount, "credit": 0,
                    "user": f"User #{e.recorded_by}"
                })

        # Sort by date desc
        entries.sort(key=lambda x: x["date"], reverse=True)

        if search:
            entries = [e for e in entries if any(search in str(v).lower() for v in e.values())]

        total_debit = total_credit = 0.0
        for e in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(e["date"]))
            self.table.setItem(row, 1, QTableWidgetItem(e["module"]))
            self.table.setItem(row, 2, QTableWidgetItem(e["ref"]))
            self.table.setItem(row, 3, QTableWidgetItem(e["desc"]))

            if e["debit"] > 0:
                di = QTableWidgetItem(f"{e['debit']:,.2f}")
                di.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                di.setForeground(Qt.red)
                self.table.setItem(row, 4, di)
                total_debit += e["debit"]
            else:
                self.table.setItem(row, 4, QTableWidgetItem(""))

            if e["credit"] > 0:
                ci = QTableWidgetItem(f"{e['credit']:,.2f}")
                ci.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                ci.setForeground(Qt.darkGreen)
                self.table.setItem(row, 5, ci)
                total_credit += e["credit"]
            else:
                self.table.setItem(row, 5, QTableWidgetItem(""))

            self.table.setItem(row, 6, QTableWidgetItem(e["user"]))

        self.lbl_count.setText(f"{len(entries)} écritures")
        self.lbl_debit.setText(f"Total Débit: {total_debit:,.2f} DA")
        self.lbl_credit.setText(f"Total Crédit: {total_credit:,.2f} DA")

    def _export_csv(self):
        import csv
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée.")
            return
        fp, _ = QFileDialog.getSaveFileName(self, "CSV", f"Journal_{datetime.now():%Y%m%d}.csv", "CSV (*.csv)")
        if not fp:
            return
        try:
            cols = ["Date/Heure", "Module", "N° Réf", "Description", "Débit", "Crédit", "Utilisateur"]
            with open(fp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(cols)
                for r in range(self.table.rowCount()):
                    w.writerow([self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(7)])
            QMessageBox.information(self, "Succès", f"Exporté: {fp}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


class StatistiquesPage(QWidget):
    """Statistics overview — summary charts across sales, purchases, stock."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self._load_stats()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("📊 Statistiques Générales")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        # KPI Cards row
        cards = QHBoxLayout()
        cards.setSpacing(12)

        self.kpi_sales = self._make_kpi_card("💰 Ventes Totales", "0 DA", "#E8F5E9", "#1B5E20")
        self.kpi_purchases = self._make_kpi_card("📦 Achats Totaux", "0 DA", "#E3F2FD", "#1565C0")
        self.kpi_stock = self._make_kpi_card("🏪 Valeur Stock", "0 DA", "#FFF3E0", "#E65100")
        self.kpi_clients = self._make_kpi_card("👥 Clients Actifs", "0", "#F3E5F5", "#6A1B9A")
        self.kpi_bank = self._make_kpi_card("🏦 Solde Bancaire", "0 DA", "#E0F2F1", "#00695C")

        cards.addWidget(self.kpi_sales[0])
        cards.addWidget(self.kpi_purchases[0])
        cards.addWidget(self.kpi_stock[0])
        cards.addWidget(self.kpi_clients[0])
        cards.addWidget(self.kpi_bank[0])
        layout.addLayout(cards)

        # Summary table
        cols = ["Module", "Nb Opérations", "Total Période", "Moy/Opération", "Tendance"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        refresh_btn = QPushButton("🔄 Actualiser les Statistiques")
        refresh_btn.clicked.connect(self._load_stats)
        layout.addWidget(refresh_btn)

    def _make_kpi_card(self, title, value, bg_color, text_color):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {bg_color}; border-radius: 8px; padding: 12px; }}")
        card_layout = QVBoxLayout(card)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {text_color}; font-size: 11px; font-weight: 600;")
        card_layout.addWidget(lbl_title)
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {text_color}; font-size: 18px; font-weight: 700;")
        card_layout.addWidget(lbl_value)
        return card, lbl_value

    def _load_stats(self):
        from app.models.sale import Sale
        from app.models.purchase import Purchase
        from app.models.stock import Stock
        from app.models.client import Client
        from app.models.bank import BankAccount

        # Sales
        sales = self.db_session.query(Sale).filter(Sale.status == "COMPLETED").all()
        total_sales = sum(s.total_amount for s in sales)
        self.kpi_sales[1].setText(f"{total_sales:,.0f} DA")

        # Purchases
        purchases = self.db_session.query(Purchase).filter(Purchase.is_deleted == 0).all()
        total_purchases = sum(p.total_amount for p in purchases)
        self.kpi_purchases[1].setText(f"{total_purchases:,.0f} DA")

        # Stock value
        stocks = self.db_session.query(Stock).all()
        stock_val = sum(s.quantity * 100 for s in stocks)  # Approximate
        self.kpi_stock[1].setText(f"{stock_val:,.0f} DA")

        # Clients
        client_count = self.db_session.query(Client).filter(Client.is_deleted == 0, Client.is_active == 1).count()
        self.kpi_clients[1].setText(str(client_count))

        # Bank
        bank_total = sum(a.current_balance for a in self.db_session.query(BankAccount).filter(BankAccount.is_deleted == 0).all())
        self.kpi_bank[1].setText(f"{bank_total:,.0f} DA")

        # Summary table
        self.table.setRowCount(0)
        stats = [
            ("Ventes", len(sales), total_sales, total_sales / max(len(sales), 1), "📈"),
            ("Achats", len(purchases), total_purchases, total_purchases / max(len(purchases), 1), "📈"),
            ("Clients", client_count, 0, 0, "➡️"),
            ("Banque", 0, bank_total, 0, "➡️"),
        ]
        for module, nb, total, avg, trend in stats:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(module))
            self.table.setItem(row, 1, QTableWidgetItem(str(nb)))
            ti = QTableWidgetItem(f"{total:,.2f} DA")
            ti.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, ti)
            ai = QTableWidgetItem(f"{avg:,.2f} DA")
            ai.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, ai)
            self.table.setItem(row, 4, QTableWidgetItem(trend))
