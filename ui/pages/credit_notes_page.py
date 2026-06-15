from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Credit Notes Page (Avoirs Client)
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QMessageBox, QWidget, QCheckBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.credit_note import CreditNote, CreditNoteItem
from app.models.invoice import Invoice
from app.models.client import Client
from app.models.product import Product
from ui.pages.base_document_page import BaseDocumentPage


class CreditNoteDialog(QDialog):
    def __init__(self, db_session, user, note=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.note = note
        self.line_items = []
        self.setWindowTitle("Modifier Avoir" if note else "Nouvel Avoir Client")
        self.setMinimumSize(950, 650)
        self._setup_ui()
        if note:
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

        self.client_combo = SearchableComboBox()
        for c in self.db_session.query(Client).order_by(Client.name).all():
            self.client_combo.addItem(c.name, c.id)
        form.addRow("Client *", self.client_combo)

        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems(["Aucun", "Facture Vente", "Bon de Livraison (BL)"])
        self.doc_type_combo.currentIndexChanged.connect(self._on_client_or_type_changed)
        form.addRow("Liaison par *", self.doc_type_combo)

        self.doc_combo = SearchableComboBox()
        self.doc_combo.currentIndexChanged.connect(self._on_doc_changed)
        form.addRow("Document d'origine", self.doc_combo)

        # Connect client change to filter documents list
        self.client_combo.currentIndexChanged.connect(self._on_client_or_type_changed)

        self.reason_input = QTextEdit()
        self.reason_input.setMaximumHeight(60)
        self.reason_input.setPlaceholderText("Raison de l'avoir (retour, erreur, etc.)")
        form.addRow("Raison", self.reason_input)
        self._on_client_or_type_changed()
        layout.addWidget(form_frame)

        items_bar = QHBoxLayout()
        items_bar.addWidget(QLabel("Articles à créditer"))
        items_bar.addStretch()
        add_btn = QPushButton("➕ Ajouter Ligne")
        add_btn.clicked.connect(self._add_item)
        items_bar.addWidget(add_btn)
        layout.addLayout(items_bar)

        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels(["Produit", "Qté", "Prix", ""])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.items_table.setColumnWidth(3, 60)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.items_table)

        total_bar = QHBoxLayout()
        self.chk_refunded = QCheckBox("Remboursé en espèces (Ne pas déduire du solde)")
        self.chk_refunded.setStyleSheet("font-weight: bold; color: #E65100;")
        total_bar.addWidget(self.chk_refunded)
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
        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == self.note.client_id:
                self.client_combo.setCurrentIndex(i)
                break
        if self.note.invoice_id:
            self.doc_type_combo.setCurrentText("Facture Vente")
            self._on_client_or_type_changed()
            for i in range(self.doc_combo.count()):
                data = self.doc_combo.itemData(i)
                if data and isinstance(data, tuple) and data[0] == "INVOICE" and data[1] == self.note.invoice_id:
                    self.doc_combo.setCurrentIndex(i)
                    break
        if self.note.reason:
            self.reason_input.setText(self.note.reason)
        if getattr(self.note, 'refunded_in_cash', 0) == 1:
            self.chk_refunded.setChecked(True)
        for item in self.note.items:
            self.line_items.append({
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "—",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            })
        self._refresh_items()

    def _on_client_or_type_changed(self):
        self.doc_combo.blockSignals(True)
        self.doc_combo.clear()
        self.doc_combo.addItem("— Choisir un document —", None)
        
        client_id = self.client_combo.currentData()
        doc_type = self.doc_type_combo.currentText()
        
        if client_id:
            if doc_type == "Facture Vente":
                from app.models.invoice import Invoice
                invoices = self.db_session.query(Invoice).filter(
                    Invoice.client_id == client_id,
                    Invoice.status != "CANCELLED"
                ).order_by(Invoice.created_at.desc()).all()
                for inv in invoices:
                    self.doc_combo.addItem(f"{inv.invoice_number} ({inv.total_amount:,.2f} DA)", ("INVOICE", inv.id))
            elif doc_type == "Bon de Livraison (BL)":
                from app.models.delivery import Delivery
                deliveries = self.db_session.query(Delivery).filter(
                    Delivery.client_id == client_id,
                    Delivery.is_deleted == 0
                ).order_by(Delivery.created_at.desc()).all()
                for d in deliveries:
                    from app.models.debt import Debt
                    debt = self.db_session.query(Debt).filter(
                        Debt.entity_type == "CLIENT",
                        Debt.reference_id == (d.sale_id or d.id)
                    ).first()
                    amt_str = f"{debt.total_amount:,.2f} DA" if debt else "— DA"
                    self.doc_combo.addItem(f"{d.delivery_number} ({amt_str})", ("DELIVERY", d.id))
        self.doc_combo.blockSignals(False)

    def _on_doc_changed(self):
        doc_data = self.doc_combo.currentData()
        if not doc_data or not isinstance(doc_data, tuple):
            return
            
        doc_type, doc_id = doc_data
        
        if doc_type == "INVOICE":
            from app.models.invoice import Invoice
            inv = self.db_session.query(Invoice).get(doc_id)
            if inv:
                reply = QMessageBox.question(
                    self, "Copier Facture",
                    f"Copier les articles de la facture {inv.invoice_number} ?\nCela écrasera la liste d'avoir actuelle.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.line_items = []
                    for item in inv.items:
                        self.line_items.append({
                            "product_id": item.product_id,
                            "product_name": item.product.name if item.product else f"Produit #{item.product_id}",
                            "quantity": item.quantity,
                            "unit_price": item.unit_price,
                            "line_total": item.line_total,
                        })
                    self.reason_input.setText(f"Retour d'articles de la Facture N° {inv.invoice_number}")
                    self._refresh_items()
                    
        elif doc_type == "DELIVERY":
            from app.models.delivery import Delivery
            from app.models.sale import Sale
            d = self.db_session.query(Delivery).get(doc_id)
            if d:
                reply = QMessageBox.question(
                    self, "Copier BL",
                    f"Copier les articles du Bon de Livraison {d.delivery_number} ?\nCela écrasera la liste d'avoir actuelle.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.line_items = []
                    if d.sale and d.sale.items:
                        for item in d.sale.items:
                            self.line_items.append({
                                "product_id": item.product_id,
                                "product_name": item.product.name if item.product else f"Produit #{item.product_id}",
                                "quantity": item.quantity,
                                "unit_price": item.unit_price,
                                "line_total": item.line_total,
                            })
                    else:
                        for item in d.items:
                            price = item.product.selling_price if item.product else 0.0
                            self.line_items.append({
                                "product_id": item.product_id,
                                "product_name": item.product.name if item.product else f"Produit #{item.product_id}",
                                "quantity": item.quantity,
                                "unit_price": price,
                                "line_total": item.quantity * price,
                            })
                    self.reason_input.setText(f"Retour d'articles du Bon de Livraison N° {d.delivery_number}")
                    self._refresh_items()

    def _add_item(self):
        from ui.pages.preparations_page import PreparationItemDialog
        dlg = PreparationItemDialog(self.db_session, self)
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
            del_btn = QPushButton("❌")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda *args, idx=i: self._remove_item(idx))
            self.items_table.setCellWidget(row, 3, del_btn)
            total += item["line_total"]
        self.total_label.setText(f"Total: {total:,.2f} DA")

    def _on_save(self):
        client_id = self.client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un client.")
            return
        if not self.line_items:
            QMessageBox.warning(self, "Erreur", "Ajoutez au moins une ligne.")
            return
        try:
            total = sum(i["line_total"] for i in self.line_items)
            doc_data = self.doc_combo.currentData()
            invoice_id = doc_data[1] if (doc_data and isinstance(doc_data, tuple) and doc_data[0] == "INVOICE") else None
            if self.note:
                self.note.client_id = client_id
                self.note.invoice_id = invoice_id
                self.note.reason = self.reason_input.toPlainText()
                self.note.total_amount = total
                self.note.refunded_in_cash = 1 if self.chk_refunded.isChecked() else 0
                for old in self.note.items:
                    self.db_session.delete(old)
                self.db_session.flush()
                for item in self.line_items:
                    self.db_session.add(CreditNoteItem(
                        credit_note_id=self.note.id, product_id=item["product_id"],
                        quantity=item["quantity"], unit_price=item["unit_price"],
                        line_total=item["line_total"],
                    ))
            else:
                now = datetime.now()
                cn = CreditNote(
                    note_number=f"AV-{now.strftime('%Y%m%d%H%M%S')}",
                    client_id=client_id, invoice_id=invoice_id,
                    status="DRAFT", total_amount=total,
                    reason=self.reason_input.toPlainText(),
                    refunded_in_cash=1 if self.chk_refunded.isChecked() else 0,
                    created_by=self.user.id,
                )
                self.db_session.add(cn)
                self.db_session.flush()
                for item in self.line_items:
                    self.db_session.add(CreditNoteItem(
                        credit_note_id=cn.id, product_id=item["product_id"],
                        quantity=item["quantity"], unit_price=item["unit_price"],
                        line_total=item["line_total"],
                    ))
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", str(e))


class CreditNotesPage(BaseDocumentPage):
    PAGE_TITLE = "Avoirs Client"
    STATUS_OPTIONS = ["Tous", "DRAFT", "VALIDATED", "APPLIED"]

    def __init__(self, user, parent=None):
        self.db_session = get_session()
        super().__init__(user, parent)

    def _get_columns(self):
        return ["N°", "Date", "Client", "Total", "Créé par", "Statut", "Actions"]

    def _load_data(self, search, status_filter):
        query = self.db_session.query(CreditNote).order_by(CreditNote.created_at.desc())
        if status_filter:
            query = query.filter(CreditNote.status == status_filter)
        notes = query.all()
        if search:
            q = search.lower()
            notes = [n for n in notes if q in n.note_number.lower() or (n.client and q in n.client.name.lower())]
        return [{
            "id": n.id, "N°": n.note_number, "Date": n.created_at,
            "Client": n.client.name if n.client else "—",
            "Total": f"{n.total_amount:,.2f} DA",
            "Créé par": n.user.full_name if n.user else "—",
            "status": n.status, "_obj": n,
        } for n in notes]

    def _on_add(self):
        dlg = CreditNoteDialog(self.db_session, self.user, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_edit(self, row_data):
        cn = row_data.get("_obj")
        if cn and cn.status != "DRAFT":
            QMessageBox.warning(self, "Erreur", "Seuls les avoirs brouillon peuvent être modifiés.")
            return
        dlg = CreditNoteDialog(self.db_session, self.user, note=cn, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_delete(self, row_data):
        cn = row_data.get("_obj")
        if not cn: return
        if cn.status != "DRAFT":
            QMessageBox.warning(self, "Erreur", "Seuls les avoirs brouillon peuvent être supprimés.")
            return
        reply = QMessageBox.question(self, "Confirmer", f"Supprimer l'avoir {cn.note_number} ?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_session.delete(cn)
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
            v_btn.clicked.connect(lambda: self._validate(row_data))
            layout.addWidget(v_btn)
            
        self.table.setCellWidget(row, col, widget)

    def open_detail(self, row_id):
        cn = self.db_session.query(CreditNote).get(row_id)
        if cn:
            dlg = CreditNoteDialog(self.db_session, self.user, note=cn, parent=self)
            dlg.exec()

    def print_document(self, row_id):
        cn = self.db_session.query(CreditNote).get(row_id)
        if not cn: return
        import os
        from PySide6.QtWidgets import QFileDialog
        from app.utils.pdf_exporter import PDFExporter
        from app.models.setting import Setting
        
        d = QFileDialog.getSaveFileName(self, "Enregistrer PDF", f"Avoir_Client_{cn.note_number}.pdf", "PDF (*.pdf)")
        if d[0]:
            co_info = {
                "name": self.db_session.query(Setting).filter_by(key="company_name").first().value if self.db_session.query(Setting).filter_by(key="company_name").first() else "ParaFarm ERP",
                "address": self.db_session.query(Setting).filter_by(key="company_address").first().value if self.db_session.query(Setting).filter_by(key="company_address").first() else "",
                "phone": self.db_session.query(Setting).filter_by(key="company_phone").first().value if self.db_session.query(Setting).filter_by(key="company_phone").first() else ""
            }
            try:
                PDFExporter.export_credit_note_to_pdf(d[0], cn, cn.items, company_info=co_info)
                os.startfile(d[0])
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur PDF : {str(e)}")

    def _validate(self, row_data):
        cn = row_data.get("_obj")
        if cn:
            if cn.status != "VALIDATED":
                cn.status = "VALIDATED"
                
                # Check if we need to adjust the client's balance
                if getattr(cn, 'refunded_in_cash', 0) == 0:
                    from app.models.debt import Debt
                    from datetime import datetime
                    
                    # Create a negative debt to decrease the client's balance
                    d = Debt(
                        entity_type="CLIENT",
                        entity_id=cn.client_id,
                        reference_type="CREDIT_NOTE",
                        reference_id=cn.id,
                        total_amount=-cn.total_amount,
                        paid_amount=0.0,
                        remaining_amount=-cn.total_amount,
                        due_date=datetime.now().strftime("%Y-%m-%d"),
                        status="PENDING"
                    )
                    self.db_session.add(d)

            self.db_session.commit()
            
            # Print PDF automatically
            try:
                self._print_pdf_direct(row_data)
            except Exception as e:
                QMessageBox.warning(self, "Impression", f"Erreur lors de l'impression: {str(e)}")
                
            self.refresh_data()

    def _print_pdf_direct(self, row_data):
        cn = row_data.get("_obj")
        if not cn: return
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
        file_path = os.path.join(temp_dir, f"Avoir_Client_{cn.note_number}.pdf")
        
        PDFExporter.export_credit_note_to_pdf(file_path, cn, cn.items, company_info=co_info)
        PrinterService.print_pdf(self.db_session, file_path)
