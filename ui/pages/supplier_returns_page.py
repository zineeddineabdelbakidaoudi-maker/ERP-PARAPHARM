from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Supplier Returns Page (Retours Fournisseur)
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QFrame, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QMessageBox, QWidget
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.supplier_return import SupplierReturn, SupplierReturnItem
from app.models.supplier import Supplier
from app.models.product import Product
from ui.pages.base_document_page import BaseDocumentPage


class ReturnItemDialog(QDialog):
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Article à Retourner")
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
        form.addRow("Prix Unitaire", self.price_spin)

        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("N° Lot (optionnel)")
        form.addRow("N° Lot", self.batch_input)

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
            "batch_number": self.batch_input.text().strip() or None,
        }
        self.accept()


class SupplierReturnDialog(QDialog):
    def __init__(self, db_session, user, ret=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.ret = ret
        self.line_items = []
        self.setWindowTitle("Modifier Retour" if ret else "Nouveau Retour Fournisseur")
        self.setMinimumSize(950, 650)
        self._setup_ui()
        if ret:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        title = QLabel(self.windowTitle())
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form = QFormLayout(form_frame)
        self.supplier_combo = SearchableComboBox()
        for s in self.db_session.query(Supplier).order_by(Supplier.name).all():
            self.supplier_combo.addItem(s.name, s.id)
        form.addRow("Fournisseur *", self.supplier_combo)

        self.br_combo = SearchableComboBox()
        self.br_combo.currentIndexChanged.connect(self._on_br_changed)
        form.addRow("Copier depuis BR (Optionnel)", self.br_combo)

        # Connect supplier change to filter BR list
        self.supplier_combo.currentIndexChanged.connect(self._on_supplier_changed)

        self.reason_input = QTextEdit()
        self.reason_input.setMaximumHeight(60)
        self.reason_input.setPlaceholderText("Raison du retour (périmé, défectueux, etc.)")
        form.addRow("Raison", self.reason_input)
        self._on_supplier_changed()
        layout.addWidget(form_frame)

        items_bar = QHBoxLayout()
        items_bar.addWidget(QLabel("Articles à retourner"))
        items_bar.addStretch()
        add_btn = QPushButton("➕ Ajouter Article")
        add_btn.clicked.connect(self._add_item)
        items_bar.addWidget(add_btn)
        layout.addLayout(items_bar)

        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["Produit", "Qté", "Lot", "Total", ""])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.items_table.setColumnWidth(4, 60)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.items_table)

        total_bar = QHBoxLayout()
        total_bar.addStretch()
        self.total_label = QLabel("Total: 0.00 DA")
        self.total_label.setProperty("class", "totalLabel")
        total_bar.addWidget(self.total_label)
        layout.addLayout(total_bar)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setProperty("variant", "secondary")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton("💾 Enregistrer")
        save.clicked.connect(self._on_save)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _load_data(self):
        for i in range(self.supplier_combo.count()):
            if self.supplier_combo.itemData(i) == self.ret.supplier_id:
                self.supplier_combo.setCurrentIndex(i)
                break
        if self.ret.reason:
            self.reason_input.setText(self.ret.reason)
        for item in self.ret.items:
            self.line_items.append({
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "—",
                "quantity": item.quantity, "unit_price": item.unit_price,
                "line_total": item.line_total,
                "batch_number": item.batch_number,
            })
        self._refresh_items()

    def _on_supplier_changed(self):
        self.br_combo.blockSignals(True)
        self.br_combo.clear()
        self.br_combo.addItem("Ne pas copier...", None)
        supplier_id = self.supplier_combo.currentData()
        if supplier_id:
            from app.models.purchase import Purchase
            purchases = self.db_session.query(Purchase).filter(
                Purchase.supplier_id == supplier_id,
                Purchase.is_deleted == 0
            ).order_by(Purchase.purchase_date.desc()).all()
            for p in purchases:
                self.br_combo.addItem(f"{p.purchase_number} ({p.purchase_date[:10]})", p.id)
        self.br_combo.blockSignals(False)

    def _on_br_changed(self):
        purchase_id = self.br_combo.currentData()
        if not purchase_id:
            return
        from app.models.purchase import Purchase
        purchase = self.db_session.query(Purchase).get(purchase_id)
        if purchase:
            reply = QMessageBox.question(
                self, "Copier BR",
                f"Voulez-vous copier les articles du bon de réception {purchase.purchase_number} ?\nCela écrasera la liste de retour actuelle.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.line_items = []
                for item in purchase.items:
                    qty = item.received_qty if item.received_qty is not None else item.ordered_qty
                    self.line_items.append({
                        "product_id": item.product_id,
                        "product_name": item.product.name if item.product else f"Produit #{item.product_id}",
                        "quantity": qty,
                        "unit_price": item.unit_cost,
                        "line_total": qty * item.unit_cost,
                        "batch_number": item.batch_number,
                    })
                self.reason_input.setText(f"Retour d'articles du Bon de Réception N° {purchase.purchase_number}")
                self._refresh_items()

    def _add_item(self):
        dlg = ReturnItemDialog(self.db_session, self)
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
            self.items_table.setItem(row, 2, QTableWidgetItem(item.get("batch_number") or "—"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"{item['line_total']:,.2f} DA"))
            del_btn = QPushButton("❌")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_item(idx))
            self.items_table.setCellWidget(row, 4, del_btn)
            total += item["line_total"]
        self.total_label.setText(f"Total: {total:,.2f} DA")

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
            if self.ret:
                self.ret.supplier_id = supplier_id
                self.ret.reason = self.reason_input.toPlainText()
                self.ret.total_amount = total
                for old in self.ret.items:
                    self.db_session.delete(old)
                self.db_session.flush()
                for item in self.line_items:
                    self.db_session.add(SupplierReturnItem(
                        supplier_return_id=self.ret.id, product_id=item["product_id"],
                        quantity=item["quantity"], unit_price=item["unit_price"],
                        line_total=item["line_total"], batch_number=item.get("batch_number"),
                    ))
            else:
                now = datetime.now()
                ret = SupplierReturn(
                    return_number=f"RET-{now.strftime('%Y%m%d%H%M%S')}",
                    supplier_id=supplier_id, status="DRAFT", total_amount=total,
                    reason=self.reason_input.toPlainText(), created_by=self.user.id,
                )
                self.db_session.add(ret)
                self.db_session.flush()
                for item in self.line_items:
                    self.db_session.add(SupplierReturnItem(
                        supplier_return_id=ret.id, product_id=item["product_id"],
                        quantity=item["quantity"], unit_price=item["unit_price"],
                        line_total=item["line_total"], batch_number=item.get("batch_number"),
                    ))
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", str(e))


class SupplierReturnsPage(BaseDocumentPage):
    PAGE_TITLE = "Retours Fournisseur"
    STATUS_OPTIONS = ["Tous", "DRAFT", "SHIPPED", "COMPLETED"]

    def __init__(self, user, parent=None):
        self.db_session = get_session()
        super().__init__(user, parent)

    def _get_columns(self):
        return ["N°", "Date", "Fournisseur", "Total", "Créé par", "Statut", "Actions"]

    def _load_data(self, search, status_filter):
        query = self.db_session.query(SupplierReturn).order_by(SupplierReturn.created_at.desc())
        if status_filter:
            query = query.filter(SupplierReturn.status == status_filter)
        rets = query.all()
        if search:
            q = search.lower()
            rets = [r for r in rets if q in r.return_number.lower() or (r.supplier and q in r.supplier.name.lower())]
        return [{
            "id": r.id, "N°": r.return_number, "Date": r.created_at,
            "Fournisseur": r.supplier.name if r.supplier else "—",
            "Total": f"{r.total_amount:,.2f} DA",
            "Créé par": r.user.full_name if r.user else "—",
            "status": r.status, "_obj": r,
        } for r in rets]

    def _on_add(self):
        dlg = SupplierReturnDialog(self.db_session, self.user, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_edit(self, row_data):
        ret = row_data.get("_obj")
        if ret and ret.status != "DRAFT":
            QMessageBox.warning(self, "Erreur", "Seuls les retours brouillon peuvent être modifiés.")
            return
        dlg = SupplierReturnDialog(self.db_session, self.user, ret=ret, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_delete(self, row_data):
        ret = row_data.get("_obj")
        if not ret: return
        if ret.status != "DRAFT":
            QMessageBox.warning(self, "Erreur", "Seuls les retours brouillon peuvent être supprimés.")
            return
        reply = QMessageBox.question(self, "Confirmer", f"Supprimer le retour {ret.return_number} ?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_session.delete(ret)
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
            v_btn = QPushButton("✔️ Expédier")
            v_btn.setProperty("variant", "icon-view")
            v_btn.clicked.connect(lambda: self._ship(row_data))
            layout.addWidget(v_btn)
            
        self.table.setCellWidget(row, col, widget)

    def open_detail(self, row_id):
        ret = self.db_session.query(SupplierReturn).get(row_id)
        if ret:
            dlg = SupplierReturnDialog(self.db_session, self.user, ret=ret, parent=self)
            dlg.exec()

    def print_document(self, row_id):
        ret = self.db_session.query(SupplierReturn).get(row_id)
        if not ret: return
        import os
        from PySide6.QtWidgets import QFileDialog
        from app.utils.pdf_exporter import PDFExporter
        from app.models.setting import Setting
        
        d = QFileDialog.getSaveFileName(self, "Enregistrer PDF", f"Retour_Fournisseur_{ret.return_number}.pdf", "PDF (*.pdf)")
        if d[0]:
            co_info = {
                "name": self.db_session.query(Setting).filter_by(key="company_name").first().value if self.db_session.query(Setting).filter_by(key="company_name").first() else "ParaFarm ERP",
                "address": self.db_session.query(Setting).filter_by(key="company_address").first().value if self.db_session.query(Setting).filter_by(key="company_address").first() else "",
                "phone": self.db_session.query(Setting).filter_by(key="company_phone").first().value if self.db_session.query(Setting).filter_by(key="company_phone").first() else ""
            }
            try:
                PDFExporter.export_supplier_return_to_pdf(d[0], ret, ret.items, company_info=co_info)
                os.startfile(d[0])
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur PDF : {str(e)}")

    def _ship(self, row_data):
        ret = row_data.get("_obj")
        if ret and ret.status == "DRAFT":
            try:
                ret.status = "SHIPPED"
                
                from app.services.stock_service import StockService
                from app.services.debt_service import DebtService
                from app.constants import MovementType
                
                stock_service = StockService(self.db_session)
                debt_service = DebtService(self.db_session)
                
                for item in ret.items:
                    stock_service.record_movement(
                        product_id=item.product_id,
                        movement_type=MovementType.ADJUSTMENT,
                        quantity=-item.quantity,
                        user_id=self.user.id,
                        reference_type="SUPPLIER_RETURN",
                        reference_id=ret.id,
                        unit_cost=item.unit_price,
                        batch_number=item.batch_number
                    )
                
                debt_service.create_debt(
                    entity_type="SUPPLIER",
                    entity_id=ret.supplier_id,
                    ref_type="SUPPLIER_RETURN",
                    ref_id=ret.id,
                    amount=-ret.total_amount,
                    paid_amount=-ret.total_amount
                )
                
                self.db_session.commit()
                
                # Print PDF automatically
                try:
                    self._print_pdf_direct(row_data)
                except Exception as e:
                    QMessageBox.warning(self, "Impression", f"Erreur lors de l'impression: {str(e)}")
                    
                self.refresh_data()
                QMessageBox.information(self, "Succès", "Retour expédié. Stock et dette ajustés.")
            except Exception as e:
                self.db_session.rollback()
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'expédition: {str(e)}")

    def _print_pdf_direct(self, row_data):
        ret = row_data.get("_obj")
        if not ret: return
        import os
        import tempfile
        from app.utils.pdf_exporter import PDFExporter
        from app.models.setting import Setting
        from app.services.printer_service import PrinterService
        
        co_info = {
            "name": self.db_session.query(Setting).filter_by(key="company_name").first().value if self.db_session.query(Setting).filter_by(key="company_name").first() else "ParaFarm ERP",
            "address": self.db_session.query(Setting).filter_by(key="company_address").first().value if self.db_session.query(Setting).filter_by(key="company_address").first() else "",
            "phone": self.db_session.query(Setting).filter_by(key="company_phone").first().value if self.db_session.query(Setting).filter_by(key="company_phone").first() else ""
        }
        
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"Retour_Fournisseur_{ret.return_number}.pdf")
        
        PDFExporter.export_supplier_return_to_pdf(file_path, ret, ret.items, company_info=co_info)
        PrinterService.print_pdf(self.db_session, file_path)
