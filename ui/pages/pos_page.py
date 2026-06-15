"""
ParaFarm ERP — Point of Sale (POS) Page
Full-featured POS with client selector, discount, receipt printing, search popup.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QDoubleSpinBox, QGridLayout,
    QDialog, QListWidget, QListWidgetItem, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QShortcut, QKeySequence

from app.core.database import get_session
from app.services.product_service import ProductService
from app.services.sale_service import SaleService
from app.services.finance_service import FinanceService
from app.services.print_service import PrintService
from app.core.exceptions import ValidationError, BusinessRuleError
from app.constants import PaymentMethod


class ProductSearchDialog(QDialog):
    """Popup to select from multiple search results."""

    def __init__(self, products, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sélectionner un produit")
        self.setMinimumSize(500, 400)
        self.selected_product = None
        self._setup_ui(products)

    def _setup_ui(self, products):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(f"{len(products)} résultat(s) trouvé(s)")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { padding: 10px; }")
        for p in products:
            stock_qty = p.stock.quantity if p.stock else 0
            text = f"{p.code} — {p.name}  |  Prix: {p.selling_price:.2f} DA  |  Stock: {stock_qty:.0f}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p)
            self.list_widget.addItem(item)
            
        self.list_widget.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self.list_widget)

        # Auto-select first item
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        # Allow Enter key to select
        self.list_widget.keyPressEvent = self._handle_key_press

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        select_btn = QPushButton("✅ Sélectionner")
        select_btn.clicked.connect(self._on_select)
        btn_layout.addWidget(select_btn)
        layout.addLayout(btn_layout)

        # Auto focus
        self.list_widget.setFocus()

    def _handle_key_press(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._on_select()
        else:
            QListWidget.keyPressEvent(self.list_widget, event)

    def _on_select(self, item=None):
        if item is None or isinstance(item, bool):
            item = self.list_widget.currentItem()
        if item:
            self.selected_product = item.data(Qt.UserRole)
            self.accept()


class POSPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.product_service = ProductService(self.db_session)
        self.sale_service = SaleService(self.db_session)
        self.finance_service = FinanceService(self.db_session)
        self.print_service = PrintService()

        self.cart_items = []  # List of dicts: product, quantity, unit_price, cost_price, line_total
        self.selected_client = None
        self.discount_amount = 0.0

        self._setup_ui()
        self._check_cash_register()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ── Left Panel (Cart & Search) ──────────────────
        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Scanner code-barres ou rechercher produit...")
        self.search_input.setMinimumHeight(48)
        font = QFont("Segoe UI", 14)
        self.search_input.setFont(font)
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("🔍")
        search_btn.setMinimumHeight(48)
        search_btn.setFixedWidth(60)
        search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(search_btn)

        left_panel.addLayout(search_layout)

        # Cart Table
        self.cart_table = QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels(["Code", "Produit", "P.U.", "Qté", "Total", ""])
        header = self.cart_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.verticalHeader().setDefaultSectionSize(48)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.setStyleSheet("QTableWidget { font-size: 14px; }")

        left_panel.addWidget(self.cart_table, stretch=1)

        # Cart actions bar
        cart_actions = QHBoxLayout()
        clear_btn = QPushButton("🗑️ Vider le panier")
        clear_btn.setProperty("variant", "danger")
        clear_btn.clicked.connect(self._clear_cart)
        cart_actions.addWidget(clear_btn)
        cart_actions.addStretch()

        items_count = QLabel("0 article(s)")
        items_count.setObjectName("itemsCount")
        items_count.setStyleSheet("font-size: 13px; color: #757575;")
        self._items_count_label = items_count
        cart_actions.addWidget(items_count)

        left_panel.addLayout(cart_actions)

        main_layout.addLayout(left_panel, stretch=7)

        # ── Right Panel (Totals & Payment) ──────────────
        right_panel = QFrame()
        right_panel.setFixedWidth(380)
        right_panel.setProperty("class", "card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)

        # Client selector
        client_frame = QFrame()
        client_layout = QHBoxLayout(client_frame)
        client_layout.setContentsMargins(0, 0, 0, 0)
        client_layout.addWidget(QLabel("Client:"))
        self.client_label = QLabel("Vente comptoir (sans client)")
        self.client_label.setStyleSheet("color: #757575; font-style: italic;")
        client_layout.addWidget(self.client_label, stretch=1)

        self.select_client_btn = QPushButton("👤 Choisir")
        self.select_client_btn.setProperty("variant", "edit")
        self.select_client_btn.setFixedHeight(32)
        self.select_client_btn.clicked.connect(self._select_client)
        client_layout.addWidget(self.select_client_btn)

        self.clear_client_btn = QPushButton("✕")
        self.clear_client_btn.setProperty("variant", "icon-delete")
        self.clear_client_btn.setFixedSize(32, 32)
        self.clear_client_btn.clicked.connect(self._clear_client)
        self.clear_client_btn.setVisible(False)
        client_layout.addWidget(self.clear_client_btn)

        right_layout.addWidget(client_frame)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #E0E0E0;")
        right_layout.addWidget(sep)
        
        # Final Product Input
        right_layout.addWidget(QLabel("Produit Final (Optionnel):"))
        self.final_product_input = QLineEdit()
        self.final_product_input.setPlaceholderText("Nom du produit (Ex: Préparation X)")
        right_layout.addWidget(self.final_product_input)
        
        # Separator
        sep_fp = QFrame()
        sep_fp.setFrameShape(QFrame.HLine)
        sep_fp.setStyleSheet("background-color: #E0E0E0;")
        right_layout.addWidget(sep_fp)

        # Totals
        totals_grid = QGridLayout()
        totals_grid.setSpacing(8)

        totals_grid.addWidget(QLabel("Sous-total:"), 0, 0)
        self.subtotal_label = QLabel("0.00 DA")
        self.subtotal_label.setAlignment(Qt.AlignRight)
        totals_grid.addWidget(self.subtotal_label, 0, 1)

        # Discount
        totals_grid.addWidget(QLabel("Remise (DA):"), 1, 0)
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setMaximum(9999999)
        self.discount_input.setSuffix(" DA")
        self.discount_input.valueChanged.connect(self._on_discount_changed)
        totals_grid.addWidget(self.discount_input, 1, 1)

        totals_grid.addWidget(
            QLabel("TOTAL:", styleSheet="font-size: 18px; font-weight: bold;"), 2, 0)
        self.total_label = QLabel("0.00 DA")
        self.total_label.setProperty("class", "totalLabel")
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("font-size: 32px; color: #1B5E20; font-weight: bold;")
        totals_grid.addWidget(self.total_label, 2, 1)

        right_layout.addLayout(totals_grid)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #E0E0E0;")
        right_layout.addWidget(sep2)

        # Amount Tendered
        right_layout.addWidget(QLabel("Montant Reçu (Espèces):"))
        self.tendered_input = QDoubleSpinBox()
        self.tendered_input.setMinimumHeight(44)
        self.tendered_input.setMaximum(9999999.99)
        self.tendered_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.tendered_input.setFont(font)
        self.tendered_input.valueChanged.connect(self._calculate_change)
        right_layout.addWidget(self.tendered_input)

        right_layout.addWidget(QLabel("Monnaie à rendre:"))
        self.change_label = QLabel("0.00 DA")
        self.change_label.setStyleSheet("font-size: 24px; color: #C62828; font-weight: bold;")
        self.change_label.setAlignment(Qt.AlignRight)
        right_layout.addWidget(self.change_label)

        right_layout.addStretch()

        # Payment Buttons
        self.pay_cash_btn = QPushButton("💵 Payer Espèces")
        self.pay_cash_btn.setProperty("variant", "pay")
        self.pay_cash_btn.clicked.connect(lambda: self._process_payment(PaymentMethod.ESPECES.value))
        right_layout.addWidget(self.pay_cash_btn)

        self.pay_card_btn = QPushButton("💳 Payer Carte")
        self.pay_card_btn.setProperty("variant", "edit")
        self.pay_card_btn.setMinimumHeight(48)
        self.pay_card_btn.clicked.connect(lambda: self._process_payment(PaymentMethod.CARTE.value))
        right_layout.addWidget(self.pay_card_btn)

        self.pay_credit_btn = QPushButton("📝 Vente à Crédit")
        self.pay_credit_btn.setProperty("variant", "warning")
        self.pay_credit_btn.setMinimumHeight(44)
        self.pay_credit_btn.clicked.connect(lambda: self._process_payment(PaymentMethod.CREDIT.value))
        right_layout.addWidget(self.pay_credit_btn)

        main_layout.addWidget(right_panel)

        # ── HOTKEYS ──────────────────────────────────────────────
        QShortcut(QKeySequence("F2"), self).activated.connect(self.search_input.setFocus)
        QShortcut(QKeySequence("F12"), self).activated.connect(lambda: self._process_payment(PaymentMethod.ESPECES.value))
        QShortcut(QKeySequence("Esc"), self).activated.connect(self._clear_cart)

    def showEvent(self, event):
        super().showEvent(event)
        self.setEnabled(True)
        self._check_cash_register()

    def _check_cash_register(self):
        session = self.finance_service.cash_repo.get_active_session()
        if not session:
            QMessageBox.warning(self, "Caisse Fermée", "Veuillez ouvrir une session de caisse avant d'encaisser.")
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.pay_cash_btn.setEnabled(True)
            self.pay_card_btn.setEnabled(True)
            self.pay_credit_btn.setEnabled(True)
            self.search_input.setPlaceholderText("🔍 Scanner code-barres ou rechercher produit...")

    # ── Search & Cart ─────────────────────────────────────────

    def _on_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        # 1. Try exact barcode match first
        product = self.product_service.get_by_barcode(query)

        if product:
            self._add_to_cart(product)
            self.search_input.clear()
            self.search_input.setFocus()
            return

        # 2. Search by name/code
        results = self.product_service.search_products(query)
        if not results:
            QMessageBox.warning(self, "Introuvable", "Aucun produit trouvé.")
            self.search_input.selectAll()
            return

        if len(results) == 1:
            self._add_to_cart(results[0])
            self.search_input.clear()
        else:
            # Multiple results — show picker
            dialog = ProductSearchDialog(results, self)
            if dialog.exec() and dialog.selected_product:
                self._add_to_cart(dialog.selected_product)
            self.search_input.clear()

        self.search_input.setFocus()

    def _add_to_cart(self, product):
        # Check stock
        stock_qty = product.stock.quantity if product.stock else 0
        current_in_cart = sum(
            item["quantity"] for item in self.cart_items
            if item["product"].id == product.id
        )

        # ── EXPIRATION SAFETY CHECK ──
        # Check available batches
        from datetime import datetime, timedelta
        now = datetime.now()
        thirty_days = now + timedelta(days=30)
        
        has_valid_stock = False
        near_expiry = False
        expired_qty = 0.0
        
        if hasattr(product, "batches") and product.batches:
            available_batches = [b for b in product.batches if b.remaining_quantity > 0]
            if not available_batches:
                has_valid_stock = (stock_qty > 0) # fallback to legacy stock
            else:
                for b in available_batches:
                    if not b.expiration_date:
                        has_valid_stock = True
                        continue
                        
                    try:
                        exp_date = datetime.strptime(b.expiration_date, "%Y-%m-%d")
                        if exp_date < now:
                            expired_qty += b.remaining_quantity
                        else:
                            has_valid_stock = True
                            if exp_date <= thirty_days:
                                near_expiry = True
                    except ValueError:
                        has_valid_stock = True # Malformed date, assume valid
        else:
            has_valid_stock = True # Legacy products without batches

        if not has_valid_stock and stock_qty > 0:
            QMessageBox.critical(self, "Produit Expiré", f"Vente bloquée: Tout le stock de '{product.name}' est périmé !")
            return

        if near_expiry:
            reply = QMessageBox.warning(
                self, "Attention: Date courte",
                f"Le produit '{product.name}' approche de sa date de péremption.\nVoulez-vous continuer ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        if stock_qty <= current_in_cart:
            QMessageBox.warning(
                self, "Stock insuffisant",
                f"Stock disponible pour '{product.name}': {stock_qty:.0f}\n"
                f"Déjà dans le panier: {current_in_cart:.0f}"
            )
            return

        # Check if already in cart
        for item in self.cart_items:
            if item["product"].id == product.id:
                item["quantity"] += 1
                item["line_total"] = item["quantity"] * item["unit_price"]
                self._render_cart()
                return

        # New item
        self.cart_items.append({
            "product": product,
            "quantity": 1,
            "unit_price": product.selling_price,
            "cost_price": product.cost_price,
            "tax_rate": product.tax_rate or 0.0,
            "line_total": product.selling_price
        })
        self._render_cart()

    def _update_qty(self, index, new_qty):
        if new_qty <= 0:
            self._remove_item(index)
            return

        item = self.cart_items[index]
        # Check stock
        stock_qty = item["product"].stock.quantity if item["product"].stock else 0
        if new_qty > stock_qty:
            QMessageBox.warning(self, "Stock insuffisant", f"Stock disponible: {stock_qty:.0f}")
            return

        item["quantity"] = new_qty
        item["line_total"] = new_qty * item["unit_price"]
        self._render_cart()

    def _remove_item(self, index):
        self.cart_items.pop(index)
        self._render_cart()

    def _clear_cart(self):
        if self.cart_items:
            reply = QMessageBox.question(
                self, "Confirmer", "Vider le panier ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.cart_items.clear()
                self.discount_input.setValue(0)
                self._render_cart()

    def _render_cart(self):
        self.cart_table.setRowCount(0)
        subtotal = 0.0

        for i, item in enumerate(self.cart_items):
            row = self.cart_table.rowCount()
            self.cart_table.insertRow(row)

            p = item["product"]
            self.cart_table.setItem(row, 0, QTableWidgetItem(p.code))
            self.cart_table.setItem(row, 1, QTableWidgetItem(p.name))
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"{item['unit_price']:.2f}"))

            # Quantity SpinBox
            qty_spin = QDoubleSpinBox()
            qty_spin.setDecimals(0 if p.unit == "Unité" else 2)
            qty_spin.setMinimum(0)
            stock_max = p.stock.quantity if p.stock else 9999
            qty_spin.setMaximum(stock_max)
            qty_spin.setValue(item["quantity"])
            qty_spin.valueChanged.connect(lambda val, idx=i: self._update_qty(idx, val))
            self.cart_table.setCellWidget(row, 3, qty_spin)

            self.cart_table.setItem(row, 4, QTableWidgetItem(f"{item['line_total']:.2f}"))

            # Remove Button
            del_btn = QPushButton("✕")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.setFixedSize(30, 30)
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_item(idx))

            btn_widget = QWidget()
            l = QHBoxLayout(btn_widget)
            l.setContentsMargins(2, 2, 2, 2)
            l.addWidget(del_btn)
            self.cart_table.setCellWidget(row, 5, btn_widget)

            subtotal += item["line_total"]

        self._items_count_label.setText(f"{len(self.cart_items)} article(s)")
        self._update_totals(subtotal)

    def _on_discount_changed(self):
        subtotal = sum(item["line_total"] for item in self.cart_items)
        self._update_totals(subtotal)

    def _update_totals(self, subtotal: float):
        discount = self.discount_input.value()
        if discount > subtotal:
            discount = subtotal
            self.discount_input.setValue(discount)
        total = subtotal - discount
        self.discount_amount = discount

        self.subtotal_label.setText(f"{subtotal:,.2f} DA".replace(",", " "))
        self.total_label.setText(f"{total:,.2f} DA".replace(",", " "))
        self.tendered_input.setValue(total)
        self._calculate_change()

    def _calculate_change(self):
        total = self._get_total()
        tendered = self.tendered_input.value()
        change = tendered - total

        if change < 0:
            self.change_label.setText(f"Manque: {abs(change):,.2f} DA".replace(",", " "))
            self.change_label.setStyleSheet("color: #C62828; font-size: 24px; font-weight: bold;")
        else:
            self.change_label.setText(f"{change:,.2f} DA".replace(",", " "))
            self.change_label.setStyleSheet("color: #2E7D32; font-size: 24px; font-weight: bold;")

    def _get_total(self) -> float:
        try:
            return float(self.total_label.text().replace(" DA", "").replace(" ", ""))
        except ValueError:
            return 0.0

    # ── Client Selection ──────────────────────────────────────

    def _select_client(self):
        from app.repositories.client_supplier_repository import ClientRepository
        client_repo = ClientRepository(self.db_session)
        clients = client_repo.search("")

        if not clients:
            QMessageBox.information(self, "Aucun client", "Aucun client enregistré.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Sélectionner un Client")
        dialog.setMinimumSize(450, 400)
        layout = QVBoxLayout(dialog)

        search = QLineEdit()
        search.setPlaceholderText("Rechercher...")
        layout.addWidget(search)

        list_w = QListWidget()
        for c in clients:
            item = QListWidgetItem(f"{c.code} — {c.name} | {c.phone or '—'}")
            item.setData(Qt.UserRole, c)
            list_w.addItem(item)
        layout.addWidget(list_w)

        def on_filter(text):
            for i in range(list_w.count()):
                it = list_w.item(i)
                it.setHidden(text.lower() not in it.text().lower())
        search.textChanged.connect(on_filter)

        def on_select(item):
            self.selected_client = item.data(Qt.UserRole)
            self.client_label.setText(f"{self.selected_client.name}")
            self.client_label.setStyleSheet("color: #1B5E20; font-weight: 600;")
            self.clear_client_btn.setVisible(True)
            dialog.accept()

        list_w.itemDoubleClicked.connect(on_select)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("Sélectionner")
        ok_btn.clicked.connect(lambda: on_select(list_w.currentItem()) if list_w.currentItem() else None)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _clear_client(self):
        self.selected_client = None
        self.client_label.setText("Vente comptoir (sans client)")
        self.client_label.setStyleSheet("color: #757575; font-style: italic;")
        self.clear_client_btn.setVisible(False)

    # ── Payment Processing ────────────────────────────────────

    def _process_payment(self, method: str):
        session = self.finance_service.cash_repo.get_active_session()
        if not session:
            QMessageBox.warning(self, "Caisse Fermée", "Veuillez ouvrir une session de caisse avant d'encaisser.")
            return

        if not self.cart_items:
            QMessageBox.warning(self, "Erreur", "Le panier est vide.")
            return

        total = self._get_total()
        tendered = self.tendered_input.value()

        # Credit requires client
        if method == PaymentMethod.CREDIT.value and not self.selected_client:
            QMessageBox.warning(self, "Client requis", "Sélectionnez un client pour une vente à crédit.")
            return

        # Cash requires sufficient amount
        if method == PaymentMethod.ESPECES.value and tendered < total:
            QMessageBox.warning(self, "Erreur", "Le montant reçu est insuffisant.")
            return

        # Prepare sale data
        subtotal = sum(item["line_total"] for item in self.cart_items)
        items_data = []
        for item in self.cart_items:
            items_data.append({
                "product_id": item["product"].id,
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "cost_price": item["cost_price"],
                "tax_rate": item.get("tax_rate", 0.0),
                "tax_amount": 0.0,
                "discount_amount": 0.0,
                "line_total": item["line_total"]
            })

        paid = total if method != PaymentMethod.CREDIT.value else 0.0

        sale_data = {
            "items": items_data,
            "client_id": self.selected_client.id if self.selected_client else None,
            "subtotal": subtotal,
            "discount_amount": self.discount_amount,
            "total_amount": total,
            "paid_amount": paid,
            "payment_method": method,
            "change_amount": tendered - total if method == PaymentMethod.ESPECES.value else 0.0,
            "final_product": self.final_product_input.text().strip()
        }

        try:
            sale = self.sale_service.process_sale(sale_data, self.user.id)

            # Print receipt
            self._print_receipt(sale, sale_data)

            QMessageBox.information(self, "✅ Vente Enregistrée", f"Vente {sale.sale_number}\nTotal: {total:.2f} DA")

            # Reset
            self.cart_items.clear()
            self.discount_input.setValue(0)
            self.final_product_input.clear()
            self._clear_client()
            self._render_cart()
            self.search_input.setFocus()

        except (ValidationError, BusinessRuleError) as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur Système", str(e))

    def _print_receipt(self, sale, sale_data):
        """Print receipt after a sale."""
        try:
            # Load shop info from settings
            from app.models.setting import Setting
            settings = self.db_session.query(Setting).all()
            shop_info = {}
            for s in settings:
                shop_info[s.key] = s.value

            receipt_data = {
                "sale_number": sale.sale_number,
                "sale_date": sale.sale_date if hasattr(sale, 'sale_date') else sale.created_at,
                "cashier_name": self.user.full_name,
                "payment_method": sale_data["payment_method"],
                "final_product": sale_data.get("final_product"),
                "items": [
                    {
                        "name": item["product"].name,
                        "quantity": item["quantity"],
                        "unit": item["product"].unit,
                        "unit_price": item["unit_price"],
                        "line_total": item["line_total"]
                    }
                    for item in self.cart_items  # Use cart_items before clearing
                ],
                "subtotal": sale_data["subtotal"],
                "discount_amount": sale_data.get("discount_amount", 0),
                "tax_total": 0.0,
                "total_amount": sale_data["total_amount"],
                "paid_amount": sale_data["paid_amount"],
                "change_amount": sale_data.get("change_amount", 0)
            }

            # Get printer from config
            from app.config import config
            printer_name = config.default_receipt_printer

            self.print_service.print_receipt(receipt_data, printer_name, shop_info)
        except Exception as e:
            # Don't block the sale if printing fails
            import logging
            logging.getLogger(__name__).warning("Receipt printing failed: %s", e)
