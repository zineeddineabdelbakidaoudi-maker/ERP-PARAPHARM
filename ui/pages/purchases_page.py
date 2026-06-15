"""
ParaFarm ERP — Purchases Page
Full CRUD + Receive workflow
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.purchase_repository import PurchaseRepository
from ui.dialogs.purchase_dialog import PurchaseDialog
from ui.dialogs.purchase_receive_dialog import PurchaseReceiveDialog


class PurchasesPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.purchase_repo = PurchaseRepository(self.db_session)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher un achat (N° commande)...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        add_btn = QPushButton("➕ Nouvelle Commande")
        add_btn.clicked.connect(self._on_add_purchase)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "N° Achat", "Date", "Fournisseur", "Statut", "Total", "Facture", "Créé par", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 220)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)

        res = self.purchase_repo.get_all()
        purchases = res.get("items", []) if isinstance(res, dict) else res

        if query:
            q = query.lower()
            purchases = [p for p in purchases if q in p.purchase_number.lower()]

        for p in purchases:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(p.purchase_number))
            self.table.setItem(row, 1, QTableWidgetItem(p.purchase_date))

            supplier_name = p.supplier.name if p.supplier else "—"
            self.table.setItem(row, 2, QTableWidgetItem(supplier_name))

            status_item = QTableWidgetItem(p.status)
            if p.status == "RECEIVED":
                status_item.setForeground(Qt.darkGreen)
            elif p.status == "CONFIRMED":
                status_item.setForeground(Qt.blue)
            elif p.status == "PARTIAL_RECEIVED":
                status_item.setForeground(Qt.darkYellow)
            self.table.setItem(row, 3, status_item)

            self.table.setItem(row, 4, QTableWidgetItem(f"{p.total_amount:.2f} DA"))
            self.table.setItem(row, 5, QTableWidgetItem(p.invoice_number or "—"))

            creator_name = p.creator.full_name if hasattr(p, 'creator') and p.creator else "—"
            self.table.setItem(row, 6, QTableWidgetItem(creator_name))

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            # Receive button (only if not fully received)
            if p.status not in ("RECEIVED", "CANCELLED"):
                recv_btn = QPushButton("📥 Recevoir")
                recv_btn.setProperty("variant", "success")
                recv_btn.setFixedHeight(30)
                recv_btn.clicked.connect(lambda checked, purch=p: self._on_receive_purchase(purch))
                action_layout.addWidget(recv_btn)

            view_btn = QPushButton("👁️ Voir")
            view_btn.setProperty("variant", "icon-view")
            view_btn.clicked.connect(lambda checked, purch=p: self._on_view_purchase(purch))
            action_layout.addWidget(view_btn)

            del_btn = QPushButton("🗑️ Annuler")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, purch=p: self._on_delete_purchase(purch))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 7, action_widget)

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_add_purchase(self):
        dialog = PurchaseDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_receive_purchase(self, purchase):
        """Open the receive dialog for a purchase order."""
        dialog = PurchaseReceiveDialog(purchase, self.user, parent=self)
        if dialog.exec():
            self.db_session.expire_all()
            self.refresh_data(self.search_input.text())

    def _on_view_purchase(self, purchase):
        """Show purchase details."""
        items_text = ""
        for item in purchase.items:
            product_name = item.product.name if item.product else f"#{item.product_id}"
            items_text += f"  • {product_name}: {item.ordered_qty:.0f} commandé, {item.received_qty:.0f} reçu — {item.line_total:.2f} DA\n"

        details = (
            f"Commande: {purchase.purchase_number}\n"
            f"Fournisseur: {purchase.supplier.name if purchase.supplier else '—'}\n"
            f"Date: {purchase.purchase_date}\n"
            f"Statut: {purchase.status}\n"
            f"Total: {purchase.total_amount:.2f} DA\n"
            f"Facture: {purchase.invoice_number or '—'}\n\n"
            f"Articles:\n{items_text}"
        )
        QMessageBox.information(self, f"Commande {purchase.purchase_number}", details)

    def _on_delete_purchase(self, purchase):
        if purchase.status == "RECEIVED":
            QMessageBox.warning(self, "Erreur", "Impossible d'annuler une commande déjà reçue.")
            return
        reply = QMessageBox.question(
            self, "Annuler", f"Voulez-vous annuler l'achat {purchase.purchase_number} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            purchase.status = "CANCELLED"
            self.purchase_repo.commit()
            self.refresh_data(self.search_input.text())
