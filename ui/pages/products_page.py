"""
ParaFarm ERP — Products Page (Master-Detail Design)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QSplitter, QFormLayout, QFrame, QDoubleSpinBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.product_repository import ProductRepository
from app.repositories.base_repository import BaseRepository
from app.models.product import Category, Product
from app.core.event_bus import get_event_bus


class ProductsPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.product_repo = ProductRepository(self.db_session)
        self.current_product = None
        self._setup_ui()
        self.refresh_data()
        
        get_event_bus().stock_updated.connect(lambda _: self.refresh_data())

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un produit (Code, Nom)...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        add_btn = QPushButton("➕ Nouveau (F1)")
        add_btn.clicked.connect(self._on_new_product)
        toolbar.addWidget(add_btn)

        print_btn = QPushButton("🖨️ Etat de Stock")
        print_btn.clicked.connect(self._on_print_stock)
        toolbar.addWidget(print_btn)

        listing_btn = QPushButton("📄 Listing Client")
        listing_btn.clicked.connect(self._on_listing_client)
        toolbar.addWidget(listing_btn)
        
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Splitter for Master (Left) and Detail (Right)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ─── LEFT PANEL (List) ───
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Code", "Désignation", "Stock", "PV TTC", "Statut"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        # Alternate row colors handled by stylesheet usually, but can be set
        self.table.setAlternatingRowColors(True)
        left_layout.addWidget(self.table)

        splitter.addWidget(left_widget)

        # ─── RIGHT PANEL (Fiche Produit) ───
        right_widget = QFrame()
        right_widget.setProperty("class", "card")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        fiche_title = QLabel("FICHE PRODUIT")
        fiche_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #2C3E50; margin-bottom: 8px;")
        right_layout.addWidget(fiche_title)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Identifiants
        self.f_code = QLineEdit()
        self.f_barcode = QLineEdit()
        self.f_name = QLineEdit()
        
        self.f_stock = QDoubleSpinBox()
        self.f_stock.setMaximum(999999)
        self.f_stock.setSuffix(" U")
        self.f_stock.valueChanged.connect(self._calculate_uj_stock)
        
        # Tarifs & TVA
        self.f_cost = QDoubleSpinBox()
        self.f_cost.setMaximum(9999999)
        self.f_cost.setSuffix(" DA")
        self.f_sell = QDoubleSpinBox()
        self.f_sell.setMaximum(9999999)
        self.f_sell.setSuffix(" DA")
        self.f_ppt = QDoubleSpinBox()
        self.f_ppt.setMaximum(9999999)
        self.f_ppt.setSuffix(" DA")
        
        self.f_tva = QDoubleSpinBox()
        self.f_tva.setMaximum(100)
        self.f_tva.setSuffix(" %")

        # UJ Logic
        self.f_ug_pct = QDoubleSpinBox()
        self.f_ug_pct.setMaximum(100)
        self.f_ug_pct.setSuffix(" %")
        self.f_ug_pct.valueChanged.connect(self._calculate_uj_stock)
        
        self.f_uj_seuil = QSpinBox()
        self.f_uj_seuil.setMaximum(9999)
        
        self.f_uj_stock = QLineEdit()
        self.f_uj_stock.setReadOnly(True)
        self.f_uj_stock.setStyleSheet("background-color: #263238; color: #FFF59D; font-weight: bold;")
        self.f_uj_stock.setText("0.00")

        # Lots
        self.f_lot = QLineEdit()
        self.f_exp = QLineEdit()
        self.f_exp.setPlaceholderText("YYYY-MM-DD")

        # Setup Form
        form_layout.addRow("Code Article :", self.f_code)
        form_layout.addRow("Code Barre :", self.f_barcode)
        form_layout.addRow("Désignation :", self.f_name)
        form_layout.addRow("Stock Actuel :", self.f_stock)
        
        sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine); sep1.setFrameShadow(QFrame.Sunken)
        form_layout.addRow(sep1)
        
        form_layout.addRow("Dernier Prix d'Achat :", self.f_cost)
        form_layout.addRow("Prix de Vente (Client) :", self.f_sell)
        form_layout.addRow("PPT (Prix Populaire) :", self.f_ppt)
        form_layout.addRow("TVA :", self.f_tva)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine); sep2.setFrameShadow(QFrame.Sunken)
        form_layout.addRow(sep2)

        form_layout.addRow("U.G % (Gratuité) :", self.f_ug_pct)
        form_layout.addRow("Seuil UJ :", self.f_uj_seuil)
        form_layout.addRow("UJ Stock :", self.f_uj_stock)
        
        sep3 = QFrame(); sep3.setFrameShape(QFrame.HLine); sep3.setFrameShadow(QFrame.Sunken)
        form_layout.addRow(sep3)

        form_layout.addRow("N° LOT :", self.f_lot)
        form_layout.addRow("DDP (Péremption) :", self.f_exp)

        right_layout.addLayout(form_layout)

        # Buttons Right Panel
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_del = QPushButton("Supprimer (F4)")
        self.btn_del.setProperty("variant", "danger")
        self.btn_del.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.btn_del)

        self.btn_save = QPushButton("Valider")
        self.btn_save.setProperty("variant", "success")
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)

        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])

        self._set_edit_mode(False)

    def _calculate_uj_stock(self):
        stock = self.f_stock.value()
        ug_pct = self.f_ug_pct.value()
        uj_stock = stock * (ug_pct / 100.0)
        self.f_uj_stock.setText(f"{uj_stock:.2f}")

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        self.db_session.expire_all()
        products = self.product_repo.search(query, limit=100) if query else self.product_repo.search("", limit=100)

        for p in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(p.code))
            self.table.setItem(row, 1, QTableWidgetItem(p.name))
            
            stock_qty = p.stock.quantity if p.stock else 0.0
            stock_item = QTableWidgetItem(f"{stock_qty:.2f}")
            self.table.setItem(row, 2, stock_item)
            
            pv_ttc = p.selling_price * (1 + (p.tax_rate/100.0))
            self.table.setItem(row, 3, QTableWidgetItem(f"{pv_ttc:.2f} DA"))
            
            status = "🔴 Rupture" if stock_qty <= p.min_stock_level else "🟢 En Stock"
            self.table.setItem(row, 4, QTableWidgetItem(status))
            
            # Store product reference in the first column
            self.table.item(row, 0).setData(Qt.UserRole, p)

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            self._clear_form()
            self._set_edit_mode(False)
            self.current_product = None
            return

        row = selected_items[0].row()
        p = self.table.item(row, 0).data(Qt.UserRole)
        self.current_product = p
        
        self.f_code.setText(p.code)
        self.f_barcode.setText(p.barcode or "")
        self.f_name.setText(p.name)
        self.f_stock.setValue(p.stock.quantity if p.stock else 0.0)
        self.f_cost.setValue(p.cost_price)
        self.f_sell.setValue(p.selling_price)
        self.f_ppt.setValue(getattr(p, "ppt_price", 0.0) or 0.0)
        self.f_tva.setValue(p.tax_rate)
        
        # Block signals briefly so it doesn't calculate multiple times unnecessarily
        self.f_ug_pct.blockSignals(True)
        self.f_ug_pct.setValue(getattr(p, "ug_percent", 0.0) or 0.0)
        self.f_ug_pct.blockSignals(False)
        
        self.f_uj_seuil.setValue(getattr(p, "uj_seuil", 0) or 0)
        self.f_lot.setText(p.lot_number or "")
        self.f_exp.setText(p.expiry_date or "")
        
        self._calculate_uj_stock()
        
        self._set_edit_mode(True)

    def _on_new_product(self):
        self.table.clearSelection()
        self.current_product = None
        self._clear_form()
        self.f_stock.setValue(0.0)
        self.f_ug_pct.setValue(0.0)
        self._calculate_uj_stock()
        self._set_edit_mode(True)
        self.f_code.setFocus()

    def _on_delete(self):
        if not self.current_product: return
        reply = QMessageBox.question(self, "Supprimer", f"Supprimer {self.current_product.name} ?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.product_repo.soft_delete(self.current_product.id)
            self.refresh_data(self.search_input.text())

    def _on_save(self):
        if not self.f_code.text().strip() or not self.f_name.text().strip():
            QMessageBox.warning(self, "Erreur", "Le code et la désignation sont obligatoires.")
            return

        from app.services.product_service import ProductService
        svc = ProductService(self.db_session)
        
        data = {
            "code": self.f_code.text().strip(),
            "barcode": self.f_barcode.text().strip() or None,
            "name": self.f_name.text().strip(),
            "cost_price": self.f_cost.value(),
            "selling_price": self.f_sell.value(),
            "ppt_price": self.f_ppt.value(),
            "tax_rate": self.f_tva.value(),
            "ug_percent": self.f_ug_pct.value(),
            "uj_seuil": self.f_uj_seuil.value(),
            "lot_number": self.f_lot.text().strip(),
            "expiry_date": self.f_exp.text().strip(),
        }

        try:
            if self.current_product:
                if not hasattr(self.current_product, "stock") or not self.current_product.stock:
                    from app.models.product import Stock
                    self.current_product.stock = Stock(product_id=self.current_product.id, quantity=self.f_stock.value())
                    self.db_session.add(self.current_product.stock)
                else:
                    self.current_product.stock.quantity = self.f_stock.value()
                
                svc.update_product(self.current_product.id, data)
                QMessageBox.information(self, "Succès", "Produit mis à jour avec succès.")
            else:
                data["created_by"] = self.user.id
                p = svc.create_product(data, self.user.id)
                if p:
                    from app.models.product import Stock
                    p.stock = Stock(product_id=p.id, quantity=self.f_stock.value())
                    self.db_session.add(p.stock)
                    self.db_session.commit()
                    QMessageBox.information(self, "Succès", "Produit créé avec succès.")
                    self.current_product = p
            self.refresh_data(self.search_input.text())
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))

    def _set_edit_mode(self, enabled: bool):
        self.f_code.setEnabled(enabled)
        self.f_barcode.setEnabled(enabled)
        self.f_name.setEnabled(enabled)
        self.f_stock.setEnabled(enabled)
        self.f_cost.setEnabled(enabled)
        self.f_sell.setEnabled(enabled)
        self.f_ppt.setEnabled(enabled)
        self.f_tva.setEnabled(enabled)
        self.f_ug_pct.setEnabled(enabled)
        self.f_uj_seuil.setEnabled(enabled)
        self.f_lot.setEnabled(enabled)
        self.f_exp.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_del.setEnabled(self.current_product is not None)

    def _clear_form(self):
        self.f_code.clear()
        self.f_barcode.clear()
        self.f_name.clear()
        self.f_cost.setValue(0)
        self.f_sell.setValue(0)
        self.f_ppt.setValue(0)
        self.f_tva.setValue(0)
        self.f_ug_pct.setValue(0)
        self.f_uj_seuil.setValue(0)
        self.f_lot.clear()
        self.f_exp.clear()

    def _on_print_stock(self):
        import os, tempfile, win32api
        from app.models.product import Product
        
        products = self.db_session.query(Product).filter(Product.is_deleted == 0, Product.is_active == 1).order_by(Product.name).all()
        if not products:
            QMessageBox.warning(self, "Erreur", "Aucun produit à imprimer.")
            return
            
        pdf_path = os.path.join(tempfile.gettempdir(), "etat_stock.pdf")
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from datetime import datetime
            
            doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph("<b>ETAT DE STOCK</b>", styles["Title"]))
            elements.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
            elements.append(Spacer(1, 20))
            
            data = [["Code", "Nom du Produit", "Stock Restant", "Prix Vente"]]
            for p in products:
                sq = getattr(p.stock, "quantity", 0.0) if p.stock else 0.0
                data.append([
                    p.code,
                    p.name,
                    f"{sq:.2f}",
                    f"{p.selling_price:.2f}"
                ])
                
            t = Table(data, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ]))
            
            elements.append(t)
            doc.build(elements)
            
            win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
            QMessageBox.information(self, "Succès", "L'état de stock a été envoyé à l'imprimante par défaut.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'impression : {str(e)}")
        
    def _on_listing_client(self):
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox, QListWidget, QListWidgetItem
        from app.models.client import Client
        from ui.utils.widgets import SearchableComboBox
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Générer un Listing Client")
        dlg.setMinimumSize(500, 600)
        
        layout = QVBoxLayout(dlg)
        
        form = QFormLayout()
        
        client_combo = SearchableComboBox()
        clients = self.db_session.query(Client).filter_by(is_deleted=0, is_active=1).order_by(Client.name).all()
        for c in clients:
            client_combo.addItem(c.name, c.id)
        form.addRow("Client :", client_combo)
        
        cb_price = QCheckBox("Inclure le prix (PPA)")
        cb_price.setChecked(True)
        form.addRow("", cb_price)
        
        cb_note = QCheckBox("Inclure la note/description")
        cb_note.setChecked(False)
        form.addRow("", cb_note)
        
        layout.addLayout(form)
        
        layout.addWidget(QLabel("<b>Sélectionner les produits à inclure :</b>"))
        
        list_widget = QListWidget()
        from app.models.product import Product
        products = self.db_session.query(Product).filter_by(is_deleted=0, is_active=1).order_by(Product.name).all()
        
        for p in products:
            item = QListWidgetItem(f"{p.name} ({p.code})")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, p.id)
            list_widget.addItem(item)
            
        layout.addWidget(list_widget)
        
        btn_layout = QHBoxLayout()
        btn_all = QPushButton("Tout sélectionner")
        btn_all.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.Checked) for i in range(list_widget.count())])
        btn_none = QPushButton("Tout désélectionner")
        btn_none.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.Unchecked) for i in range(list_widget.count())])
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        layout.addLayout(btn_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        
        if dlg.exec():
            selected_ids = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_ids.append(item.data(Qt.UserRole))
            
            if not selected_ids:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner au moins un produit.")
                return
                
            client_id = client_combo.currentData()
            client = self.db_session.query(Client).get(client_id) if client_id else None
            client_name = client.name if client else "Client Standard"
            
            selected_products = [p for p in products if p.id in selected_ids]
            
            import os, tempfile, win32api
            pdf_path = os.path.join(tempfile.gettempdir(), f"listing_{client_name.replace(' ', '_')}.pdf")
            
            try:
                from app.utils.pdf_exporter import PDFExporter
                from app.config import config
                
                co_info = {
                    "name": getattr(config, "company_name", "ParaFarm ERP"),
                    "address": getattr(config, "company_address", "Alger, Algérie"),
                    "phone": getattr(config, "company_phone", "—"),
                    "nif": getattr(config, "company_nif", "—"),
                }
                
                PDFExporter.export_product_listing_pdf(
                    file_path=pdf_path,
                    client_name=client_name,
                    products=selected_products,
                    company_info=co_info,
                    include_price=cb_price.isChecked(),
                    include_note=cb_note.isChecked()
                )
                
                win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération du listing : {str(e)}")
