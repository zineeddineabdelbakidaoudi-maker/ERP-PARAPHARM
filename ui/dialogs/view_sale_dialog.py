# -*- coding: utf-8 -*-
"""
ParaFarm ERP — View Sale (BL) Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QKeySequence, QShortcut

from app.core.database import get_session
from app.models.sale import Sale
from PySide6.QtWidgets import QMessageBox, QFileDialog
import os


class ViewSaleDialog(QDialog):
    """
    Dialog displaying the full details of a Sale (BL) document in a premium design.
    """

    def __init__(self, sale_id_or_number, parent=None):
        super().__init__(parent)
        self.db_session = get_session()
        self.sale = None
        
        # Load the sale
        if isinstance(sale_id_or_number, int):
            self.sale = self.db_session.query(Sale).filter(Sale.id == sale_id_or_number).first()
        else:
            self.sale = self.db_session.query(Sale).filter(Sale.sale_number == sale_id_or_number).first()

        self.setWindowTitle(f"Détail du Bon de Livraison: {self.sale.sale_number if self.sale else 'Inconnu'}")
        self.setMinimumSize(850, 550)
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QLabel {
                font-size: 13px;
                color: #2C3E50;
            }
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                gridline-color: #ECF0F1;
            }
            QHeaderView::section {
                color: black;
                background-color: #34495E;
                color: white;
                font-weight: bold;
                border: 1px solid #2C3E50;
                padding: 6px;
            }
        """)

        self._setup_ui()
        self._load_data()
        self._setup_shortcuts()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # ── HEADER INFO CARD ────────────────────────────────────
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #FFFFFF; border-radius: 6px; border: 1px solid #CFD8DC; padding: 12px;")
        header_grid = QGridLayout(header_card)
        header_grid.setSpacing(10)

        # Title
        title_label = QLabel("BON DE LIVRAISON")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1E88E5;")
        header_grid.addWidget(title_label, 0, 0, 1, 2)

        # N° Bon
        header_grid.addWidget(QLabel("<b>N° de Commande:</b>"), 0, 2)
        self.lbl_num = QLabel("—")
        self.lbl_num.setStyleSheet("font-size: 14px; font-weight: bold; color: #D32F2F;")
        header_grid.addWidget(self.lbl_num, 0, 3)

        # Client Info
        header_grid.addWidget(QLabel("<b>Client:</b>"), 1, 0)
        self.lbl_client = QLabel("—")
        self.lbl_client.setStyleSheet("font-weight: bold; color: #2C3E50;")
        header_grid.addWidget(self.lbl_client, 1, 1)

        # Date
        header_grid.addWidget(QLabel("<b>Date:</b>"), 1, 2)
        self.lbl_date = QLabel("—")
        header_grid.addWidget(self.lbl_date, 1, 3)

        # Payment Mode
        header_grid.addWidget(QLabel("<b>Mode de paiement:</b>"), 2, 0)
        self.lbl_payment = QLabel("—")
        header_grid.addWidget(self.lbl_payment, 2, 1)

        # Status
        header_grid.addWidget(QLabel("<b>Statut:</b>"), 2, 2)
        self.lbl_status = QLabel("—")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #2E7D32;")
        header_grid.addWidget(self.lbl_status, 2, 3)

        layout.addWidget(header_card)

        # ── LINE ITEMS GRID ─────────────────────────────────────
        cols = ["N° Ordre", "Référence", "Désignation", "Qté", "Prix U TTC", "Total"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setAlternatingRowColors(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)

        # ── TOTALS PANEL ────────────────────────────────────────
        totals_layout = QHBoxLayout()
        totals_layout.addStretch()

        totals_card = QFrame()
        totals_card.setStyleSheet("background-color: #ECEFF1; border-radius: 4px; padding: 10px; border: 1px solid #B0BEC5;")
        totals_grid = QGridLayout(totals_card)
        totals_grid.setSpacing(8)

        totals_grid.addWidget(QLabel("Total Brut:"), 0, 0)
        self.lbl_tot_brut = QLabel("0,00 DA")
        self.lbl_tot_brut.setStyleSheet("font-weight: bold;")
        totals_grid.addWidget(self.lbl_tot_brut, 0, 1)

        totals_grid.addWidget(QLabel("Remise:"), 1, 0)
        self.lbl_remise = QLabel("0,00 DA")
        self.lbl_remise.setStyleSheet("color: #D35400; font-weight: bold;")
        totals_grid.addWidget(self.lbl_remise, 1, 1)

        totals_grid.addWidget(QLabel("<b>NET À PAYER:</b>"), 2, 0)
        self.lbl_net = QLabel("0,00 DA")
        self.lbl_net.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32;")
        totals_grid.addWidget(self.lbl_net, 2, 1)

        totals_layout.addWidget(totals_card)
        layout.addLayout(totals_layout)

        # ── ACTIONS BAR ─────────────────────────────────────────
        actions = QHBoxLayout()
        actions.addStretch()
        
        self.btn_print = QPushButton("🖨️ Imprimer")
        self.btn_print.setStyleSheet("background-color: #3498DB; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px;")
        self.btn_print.clicked.connect(self._print_bl)
        actions.addWidget(self.btn_print)
        
        self.btn_close = QPushButton("Fermer (ESC)")
        self.btn_close.setStyleSheet("background-color: #E53935; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px;")
        self.btn_close.clicked.connect(self.reject)
        actions.addWidget(self.btn_close)
        
        layout.addLayout(actions)

    def _load_data(self):
        if not self.sale:
            self.lbl_num.setText("DOCUMENT NON TROUVÉ")
            return

        self.lbl_num.setText(self.sale.sale_number)
        self.lbl_client.setText(self.sale.client.name if self.sale.client else "—")
        self.lbl_date.setText(self.sale.sale_date.split(' ')[0] if self.sale.sale_date else "—")
        self.lbl_payment.setText(self.sale.payment_method or "—")
        self.lbl_status.setText(self.sale.status or "VALIDE")

        # Load items
        self.table.setRowCount(0)
        for i, item in enumerate(self.sale.items):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(item.product.code if item.product else "—"))
            self.table.setItem(row, 2, QTableWidgetItem(item.product.name if item.product else "—"))
            
            qty_item = QTableWidgetItem(f"{item.quantity:.2f}")
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, qty_item)

            price_item = QTableWidgetItem(f"{item.unit_price:,.2f}".replace(",", " "))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4, price_item)

            total_item = QTableWidgetItem(f"{item.line_total:,.2f}".replace(",", " "))
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_item.setBackground(QBrush(QColor("#FFF9C4")))
            self.table.setItem(row, 5, total_item)

        # Set totals
        self.lbl_tot_brut.setText(f"{self.sale.total_amount:,.2f} DA".replace(",", " "))
        self.lbl_remise.setText(f"{self.sale.discount_amount:,.2f} DA".replace(",", " "))
        net = self.sale.total_amount - self.sale.discount_amount
        self.lbl_net.setText(f"{net:,.2f} DA".replace(",", " "))

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.reject)

    def _print_bl(self):
        if not self.sale: return
        from app.utils.pdf_exporter import PDFExporter
        d = QFileDialog.getSaveFileName(self, "Enregistrer BL", f"BL_{self.sale.sale_number}.pdf", "PDF (*.pdf)")
        if d[0]:
            try:
                # In ParaFarm, Sale and Delivery items are often mirrored, and export_delivery_to_pdf can take a Sale
                # Because Sale model shares attributes like client, items (with quantity, line_total), total_amount, etc.
                # The exporter uses getattr so it's compatible. Let's pass the sale directly.
                PDFExporter.export_delivery_to_pdf(d[0], self.sale, self.sale.items)
                QMessageBox.information(self, "Succès", "BL imprimé avec succès.")
                os.startfile(d[0])
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur d'impression : {e}")
