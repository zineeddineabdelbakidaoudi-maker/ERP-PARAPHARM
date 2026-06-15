"""
ParaFarm ERP — Reports Page
"""
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QFrame, QTabWidget, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.sale import Sale
from app.models.purchase import Purchase
from app.models.stock import StockMovement
from app.core.worker import Worker


class ReportsPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self._refresh_all()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Date filter toolbar
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Du:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        toolbar.addWidget(self.date_from)

        toolbar.addWidget(QLabel("Au:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        toolbar.addWidget(self.date_to)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(self._refresh_all)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        export_csv_btn = QPushButton("📊 Exporter CSV")
        export_csv_btn.setProperty("variant", "export")
        export_csv_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_csv_btn)

        export_pdf_btn = QPushButton("📄 Exporter PDF")
        export_pdf_btn.setProperty("variant", "print")
        export_pdf_btn.clicked.connect(self._export_pdf)
        toolbar.addWidget(export_pdf_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Summary cards
        cards = QHBoxLayout()

        self.sales_card = self._make_card("Ventes", "0.00 DA")
        cards.addWidget(self.sales_card)

        self.purchases_card = self._make_card("Achats", "0.00 DA")
        cards.addWidget(self.purchases_card)

        self.profit_card = self._make_card("Bénéfice Brut", "0.00 DA")
        cards.addWidget(self.profit_card)

        self.count_card = self._make_card("Nb. Ventes", "0")
        cards.addWidget(self.count_card)

        layout.addLayout(cards)

        # Tabs for detailed views
        self.tabs = QTabWidget()

        # Sales tab
        self.sales_table = QTableWidget(0, 5)
        self.sales_table.setHorizontalHeaderLabels([
            "N° Vente", "Date", "Client", "Total", "Méthode"
        ])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sales_table.verticalHeader().setVisible(False)
        self.sales_table.verticalHeader().setDefaultSectionSize(48)
        self.tabs.addTab(self.sales_table, "Détail Ventes")

        # Purchases tab
        self.purchases_table = QTableWidget(0, 4)
        self.purchases_table.setHorizontalHeaderLabels([
            "N° Achat", "Date", "Fournisseur", "Total"
        ])
        self.purchases_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.purchases_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.purchases_table.verticalHeader().setVisible(False)
        self.purchases_table.verticalHeader().setDefaultSectionSize(48)
        self.tabs.addTab(self.purchases_table, "Détail Achats")

        # Movements tab
        self.movements_table = QTableWidget(0, 5)
        self.movements_table.setHorizontalHeaderLabels([
            "Produit", "Type", "Quantité", "Notes", "Date"
        ])
        self.movements_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.movements_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.movements_table.verticalHeader().setVisible(False)
        self.movements_table.verticalHeader().setDefaultSectionSize(48)
        self.tabs.addTab(self.movements_table, "Mouvements Stock")

        layout.addWidget(self.tabs)

    def _make_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "statLabel")
        card_layout.addWidget(lbl_title)

        lbl_value = QLabel(value)
        lbl_value.setProperty("class", "statValue")
        lbl_value.setObjectName(f"card_{title}")
        card_layout.addWidget(lbl_value)

        card._value_label = lbl_value
        return card

    def _get_date_range(self):
        d_from = self.date_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        d_to = self.date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        return d_from, d_to

    def _refresh_all(self):
        # Show loading state
        self.sales_table.setRowCount(0)
        self.sales_table.insertRow(0)
        item = QTableWidgetItem("⏳ Chargement...")
        item.setTextAlignment(Qt.AlignCenter)
        self.sales_table.setItem(0, 2, item)

        self.purchases_table.setRowCount(0)
        self.movements_table.setRowCount(0)

        d_from, d_to = self._get_date_range()

        # Run query in background thread
        self.worker = Worker(self._fetch_data_in_background, d_from, d_to)
        self.worker.signals.finished.connect(self._on_data_loaded)
        self.worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Erreur", e))
        self.worker.start()

    def _fetch_data_in_background(self, d_from, d_to):
        """Runs in separate thread. Must create own session to avoid SQLite thread errors."""
        from app.core.database import get_session
        from sqlalchemy.orm import joinedload
        session = get_session()
        try:
            # Sales
            sales = session.query(Sale).options(joinedload(Sale.client), joinedload(Sale.items)).filter(
                Sale.sale_date >= d_from, Sale.sale_date <= d_to, Sale.status == "COMPLETED"
            ).order_by(Sale.sale_date.desc()).all()

            # Process sales into dicts to safely pass across threads
            sales_data = []
            total_sales = 0.0
            total_cogs = 0.0
            for s in sales:
                total_sales += s.total_amount
                cogs = sum(item.quantity * item.cost_price for item in s.items)
                total_cogs += cogs
                sales_data.append({
                    "sale_number": s.sale_number,
                    "sale_date": s.sale_date,
                    "client_name": s.client.name if s.client else "Comptoir",
                    "total_amount": s.total_amount,
                    "payment_method": s.payment_method
                })

            gross_profit = total_sales - total_cogs

            # Purchases
            purchases = session.query(Purchase).options(joinedload(Purchase.supplier)).filter(
                Purchase.purchase_date >= d_from, Purchase.purchase_date <= d_to
            ).order_by(Purchase.purchase_date.desc()).all()

            purchases_data = []
            total_purchases = 0.0
            for p in purchases:
                total_purchases += p.total_amount
                purchases_data.append({
                    "purchase_number": p.purchase_number,
                    "purchase_date": p.purchase_date,
                    "supplier_name": p.supplier.name if p.supplier else "—",
                    "total_amount": p.total_amount
                })

            # Movements
            movements = session.query(StockMovement).options(joinedload(StockMovement.product)).filter(
                StockMovement.created_at >= d_from, StockMovement.created_at <= d_to
            ).order_by(StockMovement.created_at.desc()).limit(200).all()

            movements_data = []
            for m in movements:
                movements_data.append({
                    "product_name": m.product.name if m.product else "—",
                    "movement_type": m.movement_type,
                    "quantity": m.quantity,
                    "notes": m.notes,
                    "created_at": m.created_at
                })

            return {
                "sales": sales_data,
                "total_sales": total_sales,
                "gross_profit": gross_profit,
                "purchases": purchases_data,
                "total_purchases": total_purchases,
                "movements": movements_data
            }
        finally:
            session.close()

    def _on_data_loaded(self, data):
        sales = data["sales"]
        purchases = data["purchases"]
        movements = data["movements"]

        self.sales_card._value_label.setText(f"{data['total_sales']:,.2f} DA")
        self.count_card._value_label.setText(str(len(sales)))
        self.purchases_card._value_label.setText(f"{data['total_purchases']:,.2f} DA")
        self.profit_card._value_label.setText(f"{data['gross_profit']:,.2f} DA")

        self.sales_table.setRowCount(0)
        if not sales:
            self.sales_table.insertRow(0)
            item = QTableWidgetItem("Aucune donnée trouvée")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(Qt.gray)
            self.sales_table.setItem(0, 2, item)
        else:
            for s in sales:
                row = self.sales_table.rowCount()
                self.sales_table.insertRow(row)
                self.sales_table.setItem(row, 0, QTableWidgetItem(s["sale_number"]))
                self.sales_table.setItem(row, 1, QTableWidgetItem(s["sale_date"]))
                self.sales_table.setItem(row, 2, QTableWidgetItem(s["client_name"]))
                self.sales_table.setItem(row, 3, QTableWidgetItem(f"{s['total_amount']:,.2f} DA"))
                self.sales_table.setItem(row, 4, QTableWidgetItem(s["payment_method"]))

        # Purchases
        purchases = data["purchases"]


        


        self.purchases_table.setRowCount(0)
        if not purchases:
            self.purchases_table.insertRow(0)
            item = QTableWidgetItem("Aucune donnée trouvée")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(Qt.gray)
            self.purchases_table.setItem(0, 1, item)
        else:
            for p in purchases:
                row = self.purchases_table.rowCount()
                self.purchases_table.insertRow(row)
                self.purchases_table.setItem(row, 0, QTableWidgetItem(p["purchase_number"]))
                self.purchases_table.setItem(row, 1, QTableWidgetItem(p["purchase_date"]))
                self.purchases_table.setItem(row, 2, QTableWidgetItem(p["supplier_name"]))
                self.purchases_table.setItem(row, 3, QTableWidgetItem(f"{p['total_amount']:,.2f} DA"))

        # Movements — data already fetched in background thread
        self.movements_table.setRowCount(0)
        if not movements:
            self.movements_table.insertRow(0)
            item = QTableWidgetItem("Aucune donnée trouvée")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(Qt.gray)
            self.movements_table.setItem(0, 2, item)
        else:
            for m in movements:
                row = self.movements_table.rowCount()
                self.movements_table.insertRow(row)
                self.movements_table.setItem(row, 0, QTableWidgetItem(m["product_name"]))
                self.movements_table.setItem(row, 1, QTableWidgetItem(m["movement_type"]))
                qty_item = QTableWidgetItem(f"{m['quantity']:+.2f}")
                if m["quantity"] < 0:
                    qty_item.setForeground(Qt.red)
                else:
                    qty_item.setForeground(Qt.darkGreen)
                self.movements_table.setItem(row, 2, qty_item)
                self.movements_table.setItem(row, 3, QTableWidgetItem(str(m["notes"]) if m["notes"] else "—"))
                self.movements_table.setItem(row, 4, QTableWidgetItem(str(m["created_at"])))

    def _get_active_table(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            return self.sales_table, "Ventes"
        elif idx == 1:
            return self.purchases_table, "Achats"
        else:
            return self.movements_table, "Mouvements"

    def _export_csv(self):
        import csv
        table, name = self._get_active_table()
        if table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", f"Export_{name}_{datetime.now().strftime('%Y%m%d')}.csv", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                
                # Headers
                headers = []
                for col in range(table.columnCount()):
                    headers.append(table.horizontalHeaderItem(col).text())
                writer.writerow(headers)

                # Data
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

            QMessageBox.information(self, "Succès", f"Export CSV réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _export_pdf(self):
        from app.utils.pdf_exporter import PDFExporter
        table, name = self._get_active_table()
        if table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", f"Export_{name}_{datetime.now().strftime('%Y%m%d')}.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return

        try:
            headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
            data = []
            for row in range(table.rowCount()):
                row_data = [table.item(row, col).text() if table.item(row, col) else "" for col in range(table.columnCount())]
                data.append(row_data)

            filters = f"Période: {self.date_from.date().toString('yyyy-MM-dd')} au {self.date_to.date().toString('yyyy-MM-dd')}"
            
            PDFExporter.export_table_to_pdf(
                file_path=file_path,
                title=f"Rapport: {name}",
                headers=headers,
                data=data,
                filters=filters
            )
                
            QMessageBox.information(self, "Succès", f"Export PDF généré:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
