import json
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTextEdit, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QMessageBox, QDateEdit, QSpinBox, QGroupBox, QCheckBox, QWidget, QTabWidget
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.customer_order import CustomerOrder, CustomerOrderItem
from app.models.client import Client
from app.models.product import Product
from ui.pages.base_document_page import BaseDocumentPage
from ui.utils.widgets import SearchableComboBox

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PreparationItemDialog(QDialog):
    """Dialog to add a line item to a preparation."""
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un Article à Préparer")
        self.setMinimumWidth(450)
        self.db_session = db_session
        self.result_data = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.product_combo = SearchableComboBox()
        products = self.db_session.query(Product).order_by(Product.name).all()
        for p in products:
            self.product_combo.addItem(f"{p.code} — {p.name}", p.id)
        self.product_combo.currentIndexChanged.connect(self._on_product_change)
        form.addRow("Produit *", self.product_combo)

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0.01, 99999)
        self.qty_spin.setValue(1)
        self.qty_spin.valueChanged.connect(self._calc_total)
        form.addRow("Quantité *", self.qty_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 9999999)
        self.price_spin.setDecimals(2)
        self.price_spin.setSuffix(" DA")
        self.price_spin.valueChanged.connect(self._calc_total)
        form.addRow("Prix Unitaire", self.price_spin)

        self.tva_combo = SearchableComboBox()
        self.tva_combo.addItems(["19%", "9%", "0%"])
        self.tva_combo.currentIndexChanged.connect(self._calc_total)
        form.addRow("TVA", self.tva_combo)

        self.obs_input = QLineEdit()
        form.addRow("Observation / N° Lot", self.obs_input)

        self.total_label = QLabel("0.00 DA")
        self.total_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #1B5E20;")
        form.addRow("Total Ligne", self.total_label)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setProperty("variant", "secondary")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        ok = QPushButton("✅ Ajouter")
        ok.clicked.connect(self._on_ok)
        btns.addWidget(ok)
        layout.addLayout(btns)

        self._on_product_change()

    def _on_product_change(self):
        pid = self.product_combo.currentData()
        if pid:
            p = self.db_session.query(Product).get(pid)
            if p:
                self.price_spin.setValue(p.selling_price or 0)
        self._calc_total()

    def _calc_total(self):
        total = self.qty_spin.value() * self.price_spin.value()
        self.total_label.setText(f"{total:,.2f} DA")

    def _on_ok(self):
        pid = self.product_combo.currentData()
        p = self.db_session.query(Product).get(pid) if pid else None
        
        qty = self.qty_spin.value()
        if p and (p.stock_quantity or 0) < qty:
            QMessageBox.warning(self, "Stock Insuffisant", f"Le stock actuel pour '{p.name}' est de {p.stock_quantity or 0}. Vous demandez {qty}.")
            return
            
        pname = p.name if p else "—"
        pcode = p.code if p else "—"
        self.result_data = {
            "product_id": pid,
            "product_name": pname,
            "product_code": pcode,
            "quantity": self.qty_spin.value(),
            "unit_price": self.price_spin.value(),
            "tax_rate": float(self.tva_combo.currentText().replace("%", "")),
            "observation": self.obs_input.text(),
            "line_total": self.qty_spin.value() * self.price_spin.value(),
            "category": p.category.name if p and p.category else ""
        }
        self.accept()


class PreparationDialog(QDialog):
    """Dialog to create or edit a Preparation."""
    def __init__(self, db_session, user, order=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.order = order
        self.line_items = []
        
        self.setWindowTitle("Modifier Préparation" if order else "Nouveau Bon de Préparation")
        self.setMinimumSize(950, 700)
        self.setWindowState(Qt.WindowMaximized)
        self._setup_ui()
        if order:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 1. Dark Header Title Bar
        header = QFrame()
        header.setStyleSheet("background-color: #1B2631; border-radius: 4px; min-height: 45px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 0, 15, 0)
        self.header_title = QLabel("📦 BON DE PRÉPARATION")
        self.header_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()
        layout.addWidget(header)

        # 2. Metadata / Selectors card
        meta_card = QFrame()
        meta_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px;")
        meta_layout = QHBoxLayout(meta_card)
        meta_layout.setContentsMargins(15, 12, 15, 12)
        meta_layout.setSpacing(20)

        # Client Selection Column
        client_col = QVBoxLayout()
        client_label = QLabel("<b>Client *</b>")
        client_col.addWidget(client_label)
        client_h = QHBoxLayout()
        self.client_combo = SearchableComboBox()
        self.client_combo.addItem("Sélectionnez un client...", None)
        clients = self.db_session.query(Client).filter(Client.is_deleted == 0, Client.is_active == 1).order_by(Client.name).all()
        for c in clients:
            self.client_combo.addItem(c.name, c.id)
        client_h.addWidget(self.client_combo, 4)
        
        self.btn_voir = QPushButton("👁️")
        self.btn_voir.setStyleSheet("font-size: 14px; min-width: 32px; max-width: 32px; min-height: 32px; background-color: #37474F;")
        self.btn_voir.clicked.connect(self._view_client_fiche)
        client_h.addWidget(self.btn_voir, 1)
        client_col.addLayout(client_h)
        meta_layout.addLayout(client_col, 3)

        # Order Info Column
        info_col = QVBoxLayout()
        info_col.addWidget(QLabel("<b>N° Préparation & Date</b>"))
        info_h = QHBoxLayout()
        self.order_num_val = QLabel()
        self.order_num_val.setStyleSheet("font-weight: bold; color: #1565C0; font-size: 14px;")
        info_h.addWidget(self.order_num_val)
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        info_h.addWidget(self.date_edit)
        info_col.addLayout(info_h)
        meta_layout.addLayout(info_col, 2)

        # Fiscal Column
        fiscal_col = QVBoxLayout()
        fiscal_col.addWidget(QLabel("<b>Option Fiscale</b>"))
        self.tva_checkbox = QCheckBox("Soumis au TVA %")
        self.tva_checkbox.setChecked(True)
        self.tva_checkbox.stateChanged.connect(self._refresh_totals)
        fiscal_col.addWidget(self.tva_checkbox)
        meta_layout.addLayout(fiscal_col, 1)

        layout.addWidget(meta_card)

        # 3. Table Toolbar
        table_toolbar = QHBoxLayout()
        table_title = QLabel("📦 <b>Produits à Préparer</b>")
        table_title.setStyleSheet("font-size: 13px; color: #37474F;")
        table_toolbar.addWidget(table_title)
        table_toolbar.addStretch()
        
        add_item_btn = QPushButton("➕ Ajouter Article")
        add_item_btn.setStyleSheet("background-color: #0D47A1; color: white;")
        add_item_btn.clicked.connect(self._add_item)
        table_toolbar.addWidget(add_item_btn)
        layout.addLayout(table_toolbar)

        # 4. Table Grid
        self.items_table = QTableWidget(0, 10)
        self.items_table.setHorizontalHeaderLabels([
            "N°", "Réf.", "Laboratoire", "Désignation", "Qté", "Prix Vente", "Total", "TVA", "Observation", "Actions"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Fixed)
        self.items_table.setColumnWidth(9, 70)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(48)
        self.items_table.setStyleSheet("QTableWidget::item { padding: 4px; }")
        layout.addWidget(self.items_table)

        # 5. Bottom Panels Layout
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)

        # Left Column: Payment & Delivery
        delivery_gb = QGroupBox("Livraison & Règlement")
        delivery_gb.setStyleSheet("font-weight: bold; color: #37474F;")
        delivery_layout = QFormLayout(delivery_gb)
        delivery_layout.setContentsMargins(10, 10, 10, 10)
        
        self.pay_mode = SearchableComboBox()
        self.pay_mode.addItems(["Terme", "Espèce", "Chèque", "Virement", "Carte"])
        delivery_layout.addRow("Mode Paiement :", self.pay_mode)
        
        self.delivery_days = QSpinBox()
        self.delivery_days.setRange(0, 365)
        self.delivery_days.setValue(0)
        self.delivery_days.setSuffix(" Jours")
        self.delivery_days.valueChanged.connect(self._on_days_changed)
        delivery_layout.addRow("Durée Livraison :", self.delivery_days)
        
        self.expected_delivery_date_widget = QDateEdit()
        self.expected_delivery_date_widget.setCalendarPopup(True)
        self.expected_delivery_date_widget.setDate(QDate.currentDate())
        delivery_layout.addRow("Date Livraison :", self.expected_delivery_date_widget)
        
        bottom_row.addWidget(delivery_gb, 2)

        # Right Column: Totals
        totals_gb = QGroupBox("Récapitulatif Financier")
        totals_gb.setStyleSheet("font-weight: bold; color: #37474F;")
        totals_layout = QVBoxLayout(totals_gb)
        totals_layout.setContentsMargins(12, 12, 12, 12)
        totals_layout.setSpacing(12)

        self.total_ttc_box = QLabel("TOTAL T.T.C\n0.00 DA")
        self.total_ttc_box.setAlignment(Qt.AlignCenter)
        self.total_ttc_box.setStyleSheet("background-color: #E8F5E9; color: #1B5E20; border: 2px solid #1B5E20; border-radius: 6px; font-size: 18px; font-weight: bold; padding: 10px;")
        totals_layout.addWidget(self.total_ttc_box)

        bottom_row.addWidget(totals_gb, 3)
        layout.addLayout(bottom_row)

        # 6. Action Buttons footer
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        self.cancel_btn = QPushButton("❌ Annuler")
        self.cancel_btn.setProperty("variant", "secondary")
        self.cancel_btn.setShortcut("Esc")
        self.cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("💾 F10 Enregistrer")
        self.save_btn.setStyleSheet("background-color: #1B5E20; color: white; font-weight: bold;")
        self.save_btn.setShortcut("F10")
        self.save_btn.clicked.connect(self._on_save)
        footer_layout.addWidget(self.save_btn)
        
        layout.addLayout(footer_layout)

        if not self.order:
            now = datetime.now()
            self.order_num_val.setText(f"PREP-{now.strftime('%Y%m%d%H%M%S')}/2026")

    def _on_days_changed(self):
        days = self.delivery_days.value()
        self.expected_delivery_date_widget.setDate(QDate.currentDate().addDays(days))

    def _view_client_fiche(self):
        client_id = self.client_combo.currentData()
        if not client_id: return
        from ui.dialogs.client_dialog import ClientDialog
        from app.models.client import Client
        client = self.db_session.query(Client).get(client_id)
        if client:
            dlg = ClientDialog(self.user, client, self)
            dlg.exec()

    def _load_data(self):
        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == self.order.client_id:
                self.client_combo.setCurrentIndex(i)
                break
        
        self.order_num_val.setText(f"{self.order.order_number}/2026")
        
        if self.order.created_at:
            try:
                dt = datetime.strptime(self.order.created_at, "%Y-%m-%d %H:%M:%S")
                self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                pass
                
        if self.order.expected_delivery_date:
            try:
                dt = datetime.strptime(self.order.expected_delivery_date, "%Y-%m-%d")
                self.expected_delivery_date_widget.setDate(QDate(dt.year, dt.month, dt.day))
                delta = QDate.currentDate().daysTo(self.expected_delivery_date_widget.date())
                self.delivery_days.setValue(max(0, delta))
            except Exception:
                self.expected_delivery_date_widget.setDate(QDate.fromString(self.order.expected_delivery_date, "yyyy-MM-dd"))
                
        observations = []
        plain_notes = self.order.notes or ""
        if self.order.notes:
            try:
                blob = json.loads(self.order.notes)
                if isinstance(blob, dict) and "observations" in blob:
                    plain_notes = blob.get("notes", "")
                    observations = blob.get("observations", [])
            except Exception:
                pass

        for i, item in enumerate(self.order.items):
            obs = observations[i] if i < len(observations) else ""
            self.line_items.append({
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "—",
                "product_code": item.product.code if item.product else "—",
                "category": item.product.category.name if item.product and item.product.category else "",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_rate": item.tax_rate or 0.0,
                "observation": obs,
                "line_total": item.line_total,
            })
        self._refresh_items_table()

    def _add_item(self):
        dlg = PreparationItemDialog(self.db_session, self)
        if dlg.exec() and dlg.result_data:
            self.line_items.append(dlg.result_data)
            self._refresh_items_table()

    def _remove_item(self, idx):
        if 0 <= idx < len(self.line_items):
            self.line_items.pop(idx)
            self._refresh_items_table()

    def _refresh_items_table(self):
        self.items_table.setRowCount(0)
        for i, item in enumerate(self.line_items):
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            
            self.items_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.items_table.setItem(row, 1, QTableWidgetItem(item["product_code"]))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.get("category", "")))
            self.items_table.setItem(row, 3, QTableWidgetItem(item["product_name"]))
            
            qty_item = QTableWidgetItem(f"{item['quantity']:.2f}")
            qty_item.setBackground(Qt.cyan)
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(row, 4, qty_item)
            
            price_item = QTableWidgetItem(f"{item['unit_price']:,.2f} DA")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(row, 5, price_item)
            
            total_item = QTableWidgetItem(f"{item['line_total']:,.2f} DA")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(row, 6, total_item)
            
            tva_item = QTableWidgetItem(f"{item['tax_rate']:.0f}%")
            tva_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(row, 7, tva_item)
            
            self.items_table.setItem(row, 8, QTableWidgetItem(item["observation"]))
            
            del_btn = QPushButton("❌")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_item(idx))
            self.items_table.setCellWidget(row, 9, del_btn)

        self._refresh_totals()

    def _refresh_totals(self):
        total = 0
        tax_total = 0
        for item in self.line_items:
            qty = item["quantity"]
            price = item["unit_price"]
            tax_rate = item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0
            
            line_total = qty * price
            line_tax = line_total * (tax_rate / 100.0)
            
            total += line_total + line_tax
            tax_total += line_tax
            
        self.total_ttc_box.setText(f"TOTAL T.T.C\n{total:,.2f} DA")

    def _on_save(self):
        client_id = self.client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un client.")
            return
        if not self.line_items:
            QMessageBox.warning(self, "Erreur", "Ajoutez au moins un article.")
            return

        try:
            subtotal = 0
            tax_total = 0
            total_amount = 0
            observations = []
            
            for item in self.line_items:
                qty = item["quantity"]
                price = item["unit_price"]
                tax_rate = item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0
                
                line_total = qty * price
                line_tax = line_total * (tax_rate / 100.0)
                
                subtotal += line_total
                tax_total += line_tax
                total_amount += line_total + line_tax
                observations.append(item["observation"])
            
            notes_blob = {
                "notes": "",
                "observations": observations
            }
            notes_str = json.dumps(notes_blob, ensure_ascii=False)
            
            if self.order:
                self.order.client_id = client_id
                self.order.expected_delivery_date = self.expected_delivery_date_widget.date().toString("yyyy-MM-dd")
                self.order.notes = notes_str
                self.order.subtotal = subtotal
                self.order.tax_total = tax_total
                self.order.total_amount = total_amount
                
                if self.order.status != "DRAFT":
                    self.order.status = "MODIFIED"
                
                for old in self.order.items:
                    self.db_session.delete(old)
                self.db_session.flush()
                
                for item in self.line_items:
                    self.db_session.add(CustomerOrderItem(
                        order_id=self.order.id,
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        discount_amount=0,
                        tax_rate=item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0,
                        tax_amount=(item["quantity"] * item["unit_price"]) * ((item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0) / 100.0),
                        line_total=(item["quantity"] * item["unit_price"]) * (1.0 + (item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0) / 100.0),
                    ))
            else:
                raw_num = self.order_num_val.text().split("/")[0]
                order = CustomerOrder(
                    order_number=raw_num,
                    client_id=client_id,
                    status="DRAFT",
                    subtotal=subtotal,
                    tax_total=tax_total,
                    total_amount=total_amount,
                    expected_delivery_date=self.expected_delivery_date_widget.date().toString("yyyy-MM-dd"),
                    notes=notes_str,
                    created_by=self.user.id,
                )
                self.db_session.add(order)
                self.db_session.flush()
                
                for item in self.line_items:
                    self.db_session.add(CustomerOrderItem(
                        order_id=order.id,
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        discount_amount=0,
                        tax_rate=item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0,
                        tax_amount=(item["quantity"] * item["unit_price"]) * ((item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0) / 100.0),
                        line_total=(item["quantity"] * item["unit_price"]) * (1.0 + (item["tax_rate"] if self.tva_checkbox.isChecked() else 0.0) / 100.0),
                    ))
            
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", str(e))


class PreparationsGestionPage(BaseDocumentPage):
    PAGE_TITLE = ""
    STATUS_OPTIONS = ["Tous", "DRAFT", "VALIDATED", "MODIFIED", "COMPLETED", "CANCELLED"]

    def __init__(self, user, parent=None):
        self.db_session = get_session()
        super().__init__(user, parent)
        # Hide the built-in title since it's in a tab
        if hasattr(self, 'title_label'):
            self.title_label.hide()

    def _get_columns(self):
        return ["N° Préparation", "Date", "Client", "Total", "Statut", "Actions"]

    def _load_data(self, search, status_filter):
        query = self.db_session.query(CustomerOrder).order_by(CustomerOrder.created_at.desc())
        if status_filter:
            query = query.filter(CustomerOrder.status == status_filter)
        orders = query.all()

        if search:
            q = search.lower()
            orders = [o for o in orders if q in o.order_number.lower() or (o.client and q in o.client.name.lower())]

        result = []
        for o in orders:
            result.append({
                "id": o.id,
                "N° Préparation": o.order_number,
                "Date": o.created_at,
                "Client": o.client.name if o.client else "—",
                "Total": f"{o.total_amount:,.2f} DA",
                "status": o.status,
                "_obj": o,
            })
        return result

    def _on_add(self):
        dlg = PreparationDialog(self.db_session, self.user, parent=self)
        if dlg.exec():
            self.refresh_data()
            if hasattr(self.parent(), 'refresh_stats'):
                self.parent().refresh_stats()

    def _on_edit(self, row_data):
        order = row_data.get("_obj")
        if not order: return
        dlg = PreparationDialog(self.db_session, self.user, order=order, parent=self)
        if dlg.exec():
            self.refresh_data()
            if hasattr(self.parent(), 'refresh_stats'):
                self.parent().refresh_stats()

    def _on_delete(self, row_data):
        order = row_data.get("_obj")
        if not order:
            return
        if order.status != "DRAFT":
            QMessageBox.warning(self, "Erreur", "Seules les préparations en brouillon peuvent être supprimées.")
            return
        reply = QMessageBox.question(self, "Confirmer", f"Supprimer la préparation {order.order_number} ?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_session.delete(order)
            self.db_session.commit()
            self.refresh_data()
            if hasattr(self.parent(), 'refresh_stats'):
                self.parent().refresh_stats()

    def _add_action_buttons(self, row, col, row_data):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        record_id = row_data.get("id")

        btn_voir = QPushButton("👁 Voir")
        btn_voir.setFixedWidth(70)
        btn_voir.setStyleSheet("background: #17a2b8; color: white; border-radius: 3px; padding: 2px 6px;")
        btn_voir.clicked.connect(lambda checked, row_id=record_id: self.open_detail(row_id))
        layout.addWidget(btn_voir)

        btn_print = QPushButton("🖨 Imprimer (Préparateur)")
        btn_print.setFixedWidth(140)
        btn_print.setStyleSheet("background: #6c757d; color: white; border-radius: 3px; padding: 2px 6px;")
        btn_print.clicked.connect(lambda checked, r=row_data: self._export_pdf(r))
        layout.addWidget(btn_print)

        if row_data.get("status") == "DRAFT":
            validate_btn = QPushButton("✔️ Valider")
            validate_btn.setProperty("variant", "icon-view")
            validate_btn.clicked.connect(lambda: self._validate_order(row_data))
            layout.addWidget(validate_btn)

        self.table.setCellWidget(row, col, widget)

    def open_detail(self, row_id):
        order = self.db_session.query(CustomerOrder).get(row_id)
        if order:
            dlg = PreparationDialog(self.db_session, self.user, order=order, parent=self)
            dlg.exec()

    def _validate_order(self, row_data):
        order = row_data.get("_obj")
        if order:
            order.status = "VALIDATED"
            order.validated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db_session.commit()
            
            # Print PDF automatically
            try:
                from app.utils.pdf_exporter import PDFExporter
                from app.config import config
                from app.services.printer_service import PrinterService
                import tempfile
                import os
                
                self.db_session.refresh(order)
                co_info = {
                    "name": getattr(config, "company_name", "ParaFarm ERP"),
                    "address": getattr(config, "company_address", "Alger, Algérie"),
                    "phone": getattr(config, "company_phone", "—"),
                    "nif": getattr(config, "company_nif", "—"),
                }
                
                pdf_path = os.path.join(tempfile.gettempdir(), f"bon_preparation_{order.order_number}.pdf")
                
                PDFExporter.export_preparation_pdf(
                    file_path=pdf_path,
                    order=order,
                    company_info=co_info
                )
                PrinterService.print_pdf(self.db_session, pdf_path)
            except Exception as e:
                QMessageBox.warning(self, "Impression", f"Erreur lors de l'impression: {str(e)}")
                
            self.refresh_data()
            if hasattr(self.parent(), 'refresh_stats'):
                self.parent().refresh_stats()

    def _export_pdf(self, row_data):
        from app.utils.pdf_exporter import PDFExporter
        from app.config import config
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import tempfile, os, win32api
        
        order = row_data.get("_obj")
        if not order: return
        
        self.db_session.refresh(order)
        co_info = {
            "name": getattr(config, "company_name", "ParaFarm ERP"),
            "address": getattr(config, "company_address", "Alger, Algérie"),
            "phone": getattr(config, "company_phone", "—"),
            "nif": getattr(config, "company_nif", "—"),
        }
        
        # We save to temp file and open automatically so they can select printer
        pdf_path = os.path.join(tempfile.gettempdir(), f"bon_preparation_{order.order_number}.pdf")
        
        try:
            PDFExporter.export_preparation_pdf(
                file_path=pdf_path,
                order=order,
                company_info=co_info
            )
            # Open the PDF for the user to select the Preparateur Printer
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur PDF: {str(e)}")


class PreparationsStatsPage(QWidget):
    def __init__(self, db_session):
        super().__init__()
        self.db_session = db_session
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Statistiques des Préparations"))
        toolbar.addStretch()
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_stats)
        toolbar.addWidget(refresh_btn)
        self.layout.addLayout(toolbar)

        # Plot Canvas
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.refresh_stats()

    def refresh_stats(self):
        from sqlalchemy import func
        self.figure.clear()
        
        # Top Products Prepared
        ax1 = self.figure.add_subplot(121)
        top_products = self.db_session.query(
            Product.name, func.sum(CustomerOrderItem.quantity).label('qty')
        ).join(CustomerOrderItem).group_by(Product.id).order_by(func.sum(CustomerOrderItem.quantity).desc()).limit(5).all()
        
        if top_products:
            names = [p[0][:15] for p in top_products]
            qtys = [p[1] for p in top_products]
            ax1.bar(names, qtys, color='#3498db')
            ax1.set_title("Top 5 Produits Préparés")
            ax1.tick_params(axis='x', rotation=45)
        
        # Top Clients by Prep volume
        ax2 = self.figure.add_subplot(122)
        top_clients = self.db_session.query(
            Client.name, func.count(CustomerOrder.id)
        ).join(CustomerOrder).group_by(Client.id).order_by(func.count(CustomerOrder.id).desc()).limit(5).all()
        
        if top_clients:
            names = [c[0][:15] for c in top_clients]
            counts = [c[1] for c in top_clients]
            ax2.pie(counts, labels=names, autopct='%1.1f%%', startangle=90)
            ax2.set_title("Répartition par Client")
        
        self.figure.tight_layout()
        self.canvas.draw()


class PreparationsPage(QWidget):
    """Main container with Tabs for Preparations."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Gestion
        self.gestion_tab = PreparationsGestionPage(user, self)
        self.tabs.addTab(self.gestion_tab, "Gestion des Préparations")
        
        # Tab 2: Statistiques
        self.stats_tab = PreparationsStatsPage(self.db_session)
        self.tabs.addTab(self.stats_tab, "Statistiques")
        
        layout.addWidget(self.tabs)
        
    def refresh_stats(self):
        self.stats_tab.refresh_stats()
