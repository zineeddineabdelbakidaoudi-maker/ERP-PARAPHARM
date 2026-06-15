"""
ParaFarm ERP — Purchase Receive Dialog
Allows receiving items for a purchase order, with partial receive support.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDoubleSpinBox, QFrame, QFormLayout, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.services.purchase_service import PurchaseService
from app.services.audit_service import AuditService


class PurchaseReceiveDialog(QDialog):
    """Dialog to receive products from a purchase order."""

    def __init__(self, purchase, user, parent=None):
        super().__init__(parent)
        self.purchase = purchase
        self.user = user
        self.db_session = get_session()
        self.purchase_service = PurchaseService(self.db_session)
        self.audit = AuditService(self.db_session)

        self.setWindowTitle(f"Réception — {purchase.purchase_number}")
        self.setMinimumSize(950, 650)
        self._setup_ui()
        self._load_items()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel(f"Réception de commande: {self.purchase.purchase_number}")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        # Info bar
        info_frame = QFrame()
        info_frame.setProperty("class", "card")
        info_layout = QHBoxLayout(info_frame)

        supplier_name = self.purchase.supplier.name if self.purchase.supplier else "—"
        info_layout.addWidget(QLabel(f"Fournisseur: {supplier_name}"))
        info_layout.addWidget(QLabel(f"Statut: {self.purchase.status}"))
        info_layout.addWidget(QLabel(f"Total: {self.purchase.total_amount:.2f} DA"))
        layout.addWidget(info_frame)

        # Invoice number
        inv_layout = QHBoxLayout()
        inv_layout.addWidget(QLabel("N° Facture Fournisseur:"))
        self.invoice_input = QLineEdit()
        self.invoice_input.setPlaceholderText("Optionnel")
        inv_layout.addWidget(self.invoice_input)
        layout.addLayout(inv_layout)

        # Items table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Produit", "Commandé", "Déjà Reçu", "À Recevoir", "N° Lot", "Expiration", "Coût Unit."
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.receive_btn = QPushButton("✅ Confirmer la Réception")
        self.receive_btn.setProperty("variant", "success")
        self.receive_btn.setMinimumWidth(220)
        self.receive_btn.clicked.connect(self._on_receive)
        btn_layout.addWidget(self.receive_btn)

        layout.addLayout(btn_layout)

    def _load_items(self):
        self.table.setRowCount(0)
        self._qty_spins = []
        self._batch_inputs = []
        self._expiry_inputs = []

        for item in self.purchase.items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Product name
            product_name = item.product.name if item.product else f"Produit #{item.product_id}"
            self.table.setItem(row, 0, QTableWidgetItem(product_name))

            # Ordered qty
            self.table.setItem(row, 1, QTableWidgetItem(f"{item.ordered_qty:.0f}"))

            # Already received
            self.table.setItem(row, 2, QTableWidgetItem(f"{item.received_qty:.0f}"))

            # Qty to receive (spinbox)
            remaining = item.ordered_qty - item.received_qty
            qty_spin = QDoubleSpinBox()
            qty_spin.setMinimum(0)
            qty_spin.setMaximum(remaining)
            qty_spin.setValue(remaining)
            qty_spin.setDecimals(0)
            self.table.setCellWidget(row, 3, qty_spin)
            self._qty_spins.append((item, qty_spin))

            # Batch number
            batch_input = QLineEdit()
            batch_input.setPlaceholderText("Lot")
            batch_input.setText(item.batch_number or "")
            self.table.setCellWidget(row, 4, batch_input)
            self._batch_inputs.append(batch_input)

            # Expiry date
            expiry_input = QDateEdit()
            expiry_input.setCalendarPopup(True)
            expiry_input.setDisplayFormat("yyyy-MM-dd")
            if item.expiry_date:
                try:
                    expiry_input.setDate(QDate.fromString(item.expiry_date, "yyyy-MM-dd"))
                except Exception:
                    expiry_input.setDate(QDate.currentDate().addYears(1))
            else:
                expiry_input.setDate(QDate.currentDate().addYears(1))
            self.table.setCellWidget(row, 5, expiry_input)
            self._expiry_inputs.append(expiry_input)

            # Unit cost (read-only)
            self.table.setItem(row, 6, QTableWidgetItem(f"{item.unit_cost:.2f} DA"))

    def _on_receive(self):
        """Process the receive action."""
        items_to_receive = []

        for i, (item, qty_spin) in enumerate(self._qty_spins):
            qty = int(qty_spin.value())
            if qty <= 0:
                continue

            items_to_receive.append({
                "item_id": item.id,
                "received_qty": qty,
                "batch_number": self._batch_inputs[i].text().strip() or None,
                "expiry_date": self._expiry_inputs[i].date().toString("yyyy-MM-dd"),
            })

        if not items_to_receive:
            QMessageBox.warning(self, "Erreur", "Aucune quantité à recevoir.")
            return

        reply = QMessageBox.question(
            self, "Confirmer",
            f"Confirmer la réception de {len(items_to_receive)} article(s) ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            invoice_num = self.invoice_input.text().strip() or None
            self.purchase_service.receive_purchase(
                purchase_id=self.purchase.id,
                items_received=items_to_receive,
                user_id=self.user.id,
                invoice_number=invoice_num
            )
            self.audit.log_purchase_receive(self.user.id, self.purchase.id, self.purchase.purchase_number)
            QMessageBox.information(self, "Succès", "Réception enregistrée avec succès.")
            
            # Print PDF automatically
            try:
                import os
                import tempfile
                from app.utils.pdf_exporter import PDFExporter
                from app.services.printer_service import PrinterService
                
                # Reload purchase to get updated items
                self.db_session.refresh(self.purchase)
                
                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir, f"BR_{self.purchase.purchase_number}.pdf")
                
                # We can just export the purchase as a BR
                PDFExporter.export_purchase_to_pdf(file_path, self.purchase, self.purchase.items)
                PrinterService.print_pdf(self.db_session, file_path)
            except Exception as e:
                QMessageBox.warning(self, "Impression", f"Erreur lors de l'impression: {str(e)}")
                
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
