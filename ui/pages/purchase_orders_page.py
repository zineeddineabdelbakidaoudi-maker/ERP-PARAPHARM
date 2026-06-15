from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Purchase Orders Page (Bons de Commande Fournisseur)
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QMessageBox, QWidget, QDateEdit, QLineEdit
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.supplier import Supplier
from app.models.product import Product
from ui.pages.base_document_page import BaseDocumentPage


class POItemDialog(QDialog):
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un Article")
        self.setMinimumWidth(420)
        self.db_session = db_session
        self.result_data = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.product_combo = SearchableComboBox()
        for p in self.db_session.query(Product).order_by(Product.name).all():
            self.product_combo.addItem(f"{p.code} — {p.name}", p.id)
        self.product_combo.currentIndexChanged.connect(self._on_change)
        form.addRow("Produit *", self.product_combo)

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0.01, 99999)
        self.qty_spin.setValue(1)
        self.qty_spin.valueChanged.connect(self._calc)
        form.addRow("Quantité *", self.qty_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 9999999)
        self.price_spin.setDecimals(2)
        self.price_spin.setSuffix(" DA")
        self.price_spin.valueChanged.connect(self._calc)
        form.addRow("Prix Achat Unitaire", self.price_spin)

        self.total_label = QLabel("0.00 DA")
        self.total_label.setStyleSheet("font-weight:700; font-size:14px; color:#1B5E20;")
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
        self._on_change()

    def _on_change(self):
        pid = self.product_combo.currentData()
        if pid:
            p = self.db_session.query(Product).get(pid)
            if p:
                self.price_spin.setValue(p.cost_price or 0)
        self._calc()

    def _calc(self):
        self.total_label.setText(f"{self.qty_spin.value() * self.price_spin.value():,.2f} DA")

    def _on_ok(self):
        self.result_data = {
            "product_id": self.product_combo.currentData(),
            "product_name": self.product_combo.currentText(),
            "quantity": self.qty_spin.value(),
            "unit_price": self.price_spin.value(),
            "line_total": self.qty_spin.value() * self.price_spin.value(),
        }
        self.accept()


class PurchaseOrderDialog(QDialog):
    def __init__(self, db_session, user, po=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.po = po
        self.line_items = []
        self.setWindowTitle("Modifier Bon de Commande" if po else "Nouveau Bon de Commande")
        self.setMinimumSize(700, 550)
        self.setWindowState(Qt.WindowMaximized)
        self._setup_ui()
        if po:
            self._load_data()

    def _setup_ui(self):
        from PySide6.QtWidgets import QTabWidget, QListWidget
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        title = QLabel(self.windowTitle())
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # TAB 1: Informations
        tab_info = QWidget()
        form_layout = QFormLayout(tab_info)
        
        # Num BC (auto)
        self.num_input = QLineEdit("Généré automatiquement" if not self.po else self.po.order_number)
        self.num_input.setReadOnly(True)
        self.num_input.setStyleSheet("background-color: #ECEFF1;")
        form_layout.addRow("N° BC", self.num_input)

        supp_layout = QHBoxLayout()
        self.supplier_combo = SearchableComboBox()
        for s in self.db_session.query(Supplier).order_by(Supplier.name).all():
            self.supplier_combo.addItem(s.name, s.id)
        self.btn_supplier_picker = QPushButton("🔍 Détails fournisseur")
        self.btn_supplier_picker.setFixedSize(140, 26)
        self.btn_supplier_picker.clicked.connect(self._open_supplier_picker)
        supp_layout.addWidget(self.supplier_combo, stretch=1)
        supp_layout.addWidget(self.btn_supplier_picker)
        form_layout.addRow("Fournisseur *", supp_layout)
        
        self.delivery_date = QDateEdit()
        self.delivery_date.setCalendarPopup(True)
        self.delivery_date.setDate(QDate.currentDate().addDays(14))
        form_layout.addRow("Date Livraison Prévue", self.delivery_date)
        
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        form_layout.addRow("Observations", self.notes_input)
        
        self.tabs.addTab(tab_info, "ℹ️ Informations générales")

        # TAB 2: Lignes
        tab_lignes = QWidget()
        lignes_layout = QVBoxLayout(tab_lignes)
        
        items_bar = QHBoxLayout()
        add_btn = QPushButton("➕ Ajouter Article")
        add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._add_item)
        items_bar.addWidget(add_btn)
        items_bar.addStretch()
        lignes_layout.addLayout(items_bar)

        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["Produit", "Qté", "PU HT", "Montant HT", ""])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.items_table.setColumnWidth(4, 50)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(40)
        self.items_table.setAlternatingRowColors(True)
        lignes_layout.addWidget(self.items_table)

        total_bar = QHBoxLayout()
        total_bar.addStretch()
        
        # Acompte
        acompte_layout = QVBoxLayout()
        acompte_layout.addWidget(QLabel("Acompte versé :"))
        self.acompte_spin = QDoubleSpinBox()
        self.acompte_spin.setMaximum(999999999)
        self.acompte_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.acompte_spin.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px; border: 1px solid #B0BEC5; border-radius: 4px;")
        self.acompte_spin.valueChanged.connect(self._refresh_items)
        acompte_layout.addWidget(self.acompte_spin)
        total_bar.addLayout(acompte_layout)
        
        # Totals Panel
        totals_panel = QVBoxLayout()
        self.total_label = QLabel("Total HT: 0.00 DA")
        self.total_label.setProperty("class", "totalLabel")
        totals_panel.addWidget(self.total_label)
        
        self.reste_label = QLabel("Reste à payer: 0.00 DA")
        self.reste_label.setStyleSheet("color: #C62828; font-weight: bold; font-size: 14px;")
        totals_panel.addWidget(self.reste_label)
        total_bar.addLayout(totals_panel)
        
        lignes_layout.addLayout(total_bar)
        
        self.tabs.addTab(tab_lignes, "📦 Lignes de commande")

        # TAB 3: Documents
        tab_docs = QWidget()
        docs_layout = QVBoxLayout(tab_docs)
        self.docs_list = QListWidget()
        docs_layout.addWidget(self.docs_list)
        btn_joindre = QPushButton("📎 Joindre fichier")
        docs_layout.addWidget(btn_joindre)
        self.tabs.addTab(tab_docs, "📎 Documents joints")

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setProperty("variant", "secondary")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton("💾 Enregistrer et Valider")
        save.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold;")
        save.clicked.connect(self._on_save)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _open_supplier_picker(self):
        from ui.dialogs.supplier_picker_dialog import SupplierPickerDialog
        picker = SupplierPickerDialog(self.user, parent=self)
        if picker.exec() and picker.selected_supplier:
            for i in range(self.supplier_combo.count()):
                if self.supplier_combo.itemData(i) == picker.selected_supplier.id:
                    self.supplier_combo.setCurrentIndex(i)
                    break

    def _load_data(self):
        for i in range(self.supplier_combo.count()):
            if self.supplier_combo.itemData(i) == self.po.supplier_id:
                self.supplier_combo.setCurrentIndex(i)
                break
        if self.po.expected_delivery_date:
            self.delivery_date.setDate(QDate.fromString(self.po.expected_delivery_date, "yyyy-MM-dd"))
        if self.po.notes:
            self.notes_input.setText(self.po.notes)
        if hasattr(self.po, "paid_amount"):
            self.acompte_spin.setValue(self.po.paid_amount)
        for item in self.po.items:
            self.line_items.append({
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "—",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            })
        self._refresh_items()

    def _add_item(self):
        dlg = POItemDialog(self.db_session, self)
        if dlg.exec() and dlg.result_data:
            self.line_items.append(dlg.result_data)
            self._refresh_items()

    def _remove_item(self, idx):
        if 0 <= idx < len(self.line_items):
            self.line_items.pop(idx)
            self._refresh_items()

    def _refresh_items(self):
        self.items_table.setRowCount(0)
        total = 0
        for i, item in enumerate(self.line_items):
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            self.items_table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            self.items_table.setItem(row, 1, QTableWidgetItem(f"{item['quantity']:.2f}"))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"{item['unit_price']:,.2f} DA"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"{item['line_total']:,.2f} DA"))
            del_btn = QPushButton("❌")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_item(idx))
            self.items_table.setCellWidget(row, 4, del_btn)
            total += item["line_total"]
        self.total_label.setText(f"Total HT: {total:,.2f} DA".replace(",", " "))
        reste = max(0.0, total - self.acompte_spin.value())
        self.reste_label.setText(f"Reste à payer: {reste:,.2f} DA".replace(",", " "))

    def _on_save(self):
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un fournisseur.")
            return
        if not self.line_items:
            QMessageBox.warning(self, "Erreur", "Ajoutez au moins un article.")
            return
        try:
            total = sum(i["line_total"] for i in self.line_items)
            if self.po:
                self.po.supplier_id = supplier_id
                self.po.expected_delivery_date = self.delivery_date.date().toString("yyyy-MM-dd")
                self.po.notes = self.notes_input.toPlainText()
                self.po.total_amount = total
                self.po.paid_amount = self.acompte_spin.value()
                
                if self.po.status != "DRAFT":
                    self.po.status = "MODIFIED"
                for old in self.po.items:
                    self.db_session.delete(old)
                self.db_session.flush()
                for item in self.line_items:
                    self.db_session.add(PurchaseOrderItem(
                        purchase_order_id=self.po.id, product_id=item["product_id"],
                        quantity=item["quantity"], unit_price=item["unit_price"],
                        line_total=item["line_total"],
                    ))
            else:
                now = datetime.now()
                order_number = f"BC-{now.strftime('%Y%m%d%H%M%S')}"
                po = PurchaseOrder(
                    order_number=order_number,
                    supplier_id=supplier_id,
                    status="DRAFT",
                    total_amount=total,
                    paid_amount=self.acompte_spin.value(),
                    expected_delivery_date=self.delivery_date.date().toString("yyyy-MM-dd"),
                    notes=self.notes_input.toPlainText(),
                    created_by=self.user.id
                )
                self.db_session.add(po)
                self.db_session.flush()
                for item in self.line_items:
                    self.db_session.add(PurchaseOrderItem(
                        purchase_order_id=po.id, product_id=item["product_id"],
                        quantity=item["quantity"], unit_price=item["unit_price"],
                        line_total=item["line_total"],
                    ))
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", str(e))


class PurchaseOrdersPage(BaseDocumentPage):
    PAGE_TITLE = "Bons de Commande"
    STATUS_OPTIONS = ["Tous", "DRAFT", "VALIDATED", "MODIFIED", "COMPLETED", "CANCELLED"]

    def __init__(self, user, parent=None):
        self.db_session = get_session()
        super().__init__(user, parent)

    def _get_columns(self):
        return ["N°", "Date", "Fournisseur", "Total", "Créé par", "Statut", "Actions"]

    def _load_data(self, search, status_filter):
        query = self.db_session.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())
        if status_filter:
            query = query.filter(PurchaseOrder.status == status_filter)
        pos = query.all()
        if search:
            q = search.lower()
            pos = [p for p in pos if q in p.order_number.lower() or (p.supplier and q in p.supplier.name.lower())]
        return [{
            "id": p.id, "N°": p.order_number, "Date": p.created_at,
            "Fournisseur": p.supplier.name if p.supplier else "—",
            "Total": f"{p.total_amount:,.2f} DA",
            "Créé par": p.user.full_name if p.user else "—",
            "status": p.status, "_obj": p,
        } for p in pos]

    def _on_add(self):
        dlg = PurchaseOrderDialog(self.db_session, self.user, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_edit(self, row_data):
        po = row_data.get("_obj")
        if not po: return
        dlg = PurchaseOrderDialog(self.db_session, self.user, po=po, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_delete(self, row_data):
        po = row_data.get("_obj")
        if not po: return
        if po.status != "DRAFT":
            QMessageBox.warning(self, "Erreur", "Seuls les bons de commande brouillon peuvent être supprimés.")
            return
        reply = QMessageBox.question(self, "Confirmer", f"Supprimer le BC {po.order_number} ?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_session.delete(po)
            self.db_session.commit()
            self.refresh_data()

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

        btn_print = QPushButton("🖨 Imprimer")
        btn_print.setFixedWidth(90)
        btn_print.setStyleSheet("background: #6c757d; color: white; border-radius: 3px; padding: 2px 6px;")
        btn_print.clicked.connect(lambda checked, row_id=record_id: self.print_document(row_id))
        layout.addWidget(btn_print)

        if row_data.get("status") == "DRAFT":
            v_btn = QPushButton("✔️ Valider")
            v_btn.setProperty("variant", "icon-view")
            v_btn.clicked.connect(lambda checked, r=row_data: self._validate(r))
            layout.addWidget(v_btn)

        self.table.setCellWidget(row, col, widget)

    def open_detail(self, row_id):
        po = self.db_session.query(PurchaseOrder).get(row_id)
        if po:
            dlg = PurchaseOrderDialog(self.db_session, self.user, po=po, parent=self)
            dlg.exec()

    def print_document(self, row_id):
        po = self.db_session.query(PurchaseOrder).get(row_id)
        if po:
            row_data = {"_obj": po}
            self._export_pdf(row_data)

    def _validate(self, row_data):
        po = row_data.get("_obj")
        if po:
            po.status = "VALIDATED"
            po.validated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db_session.commit()
            self.refresh_data()

    def _export_pdf(self, row_data):
        from app.utils.pdf_exporter import PDFExporter
        from PySide6.QtWidgets import QFileDialog
        po = row_data.get("_obj")
        if not po: return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter Bon de Commande", f"BC_{po.order_number}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path: return
        
        # We can reuse the export_invoice_to_pdf logic since POs have a similar structure
        # Just inject it via an adapter or rely on duck typing
        # The PDFExporter expects: invoice.invoice_number, invoice.issue_date, invoice.client.name, invoice.items, invoice.total_amount_ht, etc.
        # Since PO models are slightly different, I'll pass a dummy object or adapt it.
        class POAdapter:
            def __init__(self, po):
                self.invoice_number = po.order_number
                self.issue_date = po.created_at[:10]
                self.created_at = po.created_at
                self.status = po.status
                self.total_amount_ht = po.total_amount
                self.total_vat = 0.0
                self.total_amount = po.total_amount
                self.is_bc = True
                
            @property
            def client(self):
                class SuppAdapter:
                    name = po.supplier.name if po.supplier else "—"
                    code = po.supplier.code if po.supplier else "—"
                return SuppAdapter()

        adapted_po = POAdapter(po)
        
        try:
            PDFExporter.export_invoice_to_pdf(
                file_path=file_path,
                invoice=adapted_po,
                items=po.items,
                paid_amount=getattr(po, "paid_amount", 0.0)
            )
            QMessageBox.information(self, "Succès", f"Bon de Commande PDF généré:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
