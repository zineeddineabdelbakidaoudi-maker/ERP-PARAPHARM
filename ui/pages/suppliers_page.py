"""
ParaFarm ERP — Suppliers Page (Master-Detail Design)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QFormLayout, QStackedWidget, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from app.core.database import get_session
from app.services.auth_service import get_current_session
from app.services.supplier_service import SupplierService
from app.models.supplier import Supplier
from app.models.debt import Debt
from app.models.purchase import Purchase
from app.models.supplier_invoice import SupplierInvoice
from app.models.supplier_return import SupplierReturn
from ui.dialogs.supplier_dialog import SupplierDialog
from ui.dialogs.supplier_document_creation_dialog import SupplierDocumentCreationDialog

class SuppliersPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.service = SupplierService(self.db_session)
        self.current_supplier = None
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(15)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un fournisseur (Code, Nom, Téléphone)...")
        self.search_input.setMinimumHeight(35)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        session = get_current_session()
        can_create = session.has_permission("SUPPLIERS", "CREATE") if session else False

        add_btn = QPushButton("➕ Nouveau Fournisseur")
        add_btn.setMinimumHeight(35)
        add_btn.clicked.connect(self._on_add_supplier)
        add_btn.setVisible(can_create)
        toolbar.addWidget(add_btn)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # ─── TOP ACTIONS PANEL ───
        self.actions_panel = QFrame()
        self.actions_panel.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px;")
        actions_layout = QHBoxLayout(self.actions_panel)
        actions_layout.setContentsMargins(15, 15, 15, 15)
        actions_layout.setSpacing(15)

        btn_style = """
            QPushButton {
                font-size: 14px; font-weight: bold; padding: 10px;
                border-radius: 6px; background-color: #F8F9FA;
                border: 1px solid #BDC3C7; color: #2C3E50;
            }
            QPushButton:hover { background-color: #E8ECEF; }
            QPushButton:disabled { color: #95A5A6; background-color: #ECF0F1; }
        """
        
        self.btn_edit_supplier = QPushButton("✏️ Modifier Info")
        self.btn_edit_supplier.setStyleSheet(btn_style)
        self.btn_edit_supplier.clicked.connect(self._on_edit_current_supplier)
        actions_layout.addWidget(self.btn_edit_supplier)
        
        self.btn_etat = QPushButton("🖨️ Etat Dettes")
        self.btn_etat.setStyleSheet(btn_style)
        self.btn_etat.clicked.connect(self._export_etat_dettes)
        actions_layout.addWidget(self.btn_etat)
        
        self.btn_bc = QPushButton("📝 Nouvelle Commande (BC)")
        self.btn_bc.setStyleSheet(btn_style.replace("#F8F9FA", "#8E44AD").replace("#2C3E50", "white"))
        self.btn_bc.clicked.connect(lambda: self._show_document_creator("BC"))
        actions_layout.addWidget(self.btn_bc)

        self.btn_br = QPushButton("📦 Nouveau BR / Facture")
        self.btn_br.setStyleSheet(btn_style.replace("#F8F9FA", "#3498DB").replace("#2C3E50", "white"))
        self.btn_br.clicked.connect(lambda: self._show_document_creator("BR"))
        actions_layout.addWidget(self.btn_br)
        
        self.btn_avoir = QPushButton("↩️ Nouvel Avoir")
        self.btn_avoir.setStyleSheet(btn_style)
        self.btn_avoir.clicked.connect(self._create_avoir)
        actions_layout.addWidget(self.btn_avoir)
        
        self.btn_payment = QPushButton("💰 Paiement")
        self.btn_payment.setStyleSheet(btn_style)
        self.btn_payment.clicked.connect(self._create_payment)
        actions_layout.addWidget(self.btn_payment)
        
        self.btn_reclamation = QPushButton("⚠️ Réclamation")
        self.btn_reclamation.setStyleSheet(btn_style)
        self.btn_reclamation.clicked.connect(self._create_reclamation)
        actions_layout.addWidget(self.btn_reclamation)
        
        main_layout.addWidget(self.actions_panel)

        # ─── MAIN CONTENT SPLITTER ───
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Supplier Info Frame
        info_frame = QFrame()
        info_layout = QFormLayout(info_frame)
        self.lbl_name = QLabel("---")
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 16px; color: #2C3E50;")
        self.lbl_code = QLabel("---")
        self.lbl_phone = QLabel("---")
        self.lbl_category = QLabel("---")
        self.lbl_dette = QLabel("---")
        
        info_layout.addRow("Nom :", self.lbl_name)
        info_layout.addRow("Code :", self.lbl_code)
        info_layout.addRow("Téléphone :", self.lbl_phone)
        info_layout.addRow("Catégorie :", self.lbl_category)
        info_layout.addRow("Dette Actuelle :", self.lbl_dette)
        
        self.detail_left = QFrame()
        self.detail_left.setProperty("class", "card")
        self.detail_left.setMinimumWidth(400)
        
        dl_layout = QVBoxLayout(self.detail_left)
        dl_layout.setContentsMargins(12, 12, 12, 12)
        dl_layout.addWidget(info_frame)
        
        dl_layout.addWidget(QLabel("<b>Historique (Dernières Opérations)</b>"))
        self.hist_table = QTableWidget(0, 5)
        self.hist_table.setHorizontalHeaderLabels(["Date", "Type", "Réf", "Montant", "Reste"])
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hist_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.hist_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.hist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.hist_table.itemDoubleClicked.connect(self._on_hist_double_clicked)
        dl_layout.addWidget(self.hist_table)
        content_layout.addWidget(self.detail_left, stretch=2)

        # ─── RIGHT PANEL (Stacked Widget for Table / Document Creation) ───
        self.right_stack = QStackedWidget()
        
        # Page 0: Table of suppliers
        page_table = QWidget()
        pt_layout = QVBoxLayout(page_table)
        pt_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Code", "Nom Fournisseur", "Téléphone", "Catégorie"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.setAlternatingRowColors(True)
        pt_layout.addWidget(self.table)
        
        self.right_stack.addWidget(page_table)
        content_layout.addWidget(self.right_stack, stretch=3)
        
        main_layout.addLayout(content_layout)
        
        # Disable actions initially
        self._set_actions_enabled(False)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        
        res = self.service.get_all_suppliers()
        suppliers = res.get("items", []) if isinstance(res, dict) else res
        
        if query:
            q = query.lower()
            suppliers = [s for s in suppliers if q in s.name.lower() or (s.code and q in s.code.lower()) or (s.phone and q in s.phone.lower())]

        for s in suppliers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            s_item = QTableWidgetItem(s.code)
            s_item.setData(Qt.UserRole, s.id)
            self.table.setItem(row, 0, s_item)
            self.table.setItem(row, 1, QTableWidgetItem(s.name))
            self.table.setItem(row, 2, QTableWidgetItem(s.phone or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(s.category or "—"))

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_add_supplier(self):
        dialog = SupplierDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.current_supplier = None
            self._clear_detail()
            return
            
        supplier_id = selected[0].data(Qt.UserRole)
        self.current_supplier = self.db_session.query(Supplier).get(supplier_id)
        if self.current_supplier:
            self._load_detail()

    def _set_actions_enabled(self, enabled: bool):
        self.btn_edit_supplier.setEnabled(enabled)
        self.btn_etat.setEnabled(enabled)
        self.btn_br.setEnabled(enabled)
        self.btn_avoir.setEnabled(enabled)
        self.btn_payment.setEnabled(enabled)
        self.btn_reclamation.setEnabled(enabled)

    def _clear_detail(self):
        self.lbl_name.setText("---")
        self.lbl_code.setText("---")
        self.lbl_phone.setText("---")
        self.lbl_category.setText("---")
        self.lbl_dette.setText("---")
        self.hist_table.setRowCount(0)
        self._set_actions_enabled(False)
        self._close_creator()

    def _load_detail(self):
        s = self.current_supplier
        self.lbl_name.setText(s.name)
        self.lbl_code.setText(s.code)
        self.lbl_phone.setText(s.phone or "—")
        self.lbl_category.setText(s.category or "—")
        
        # Load Historique
        self.hist_table.setRowCount(0)
        debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "SUPPLIER",
            Debt.entity_id == s.id,
            Debt.is_deleted == 0
        ).order_by(Debt.created_at.desc()).limit(100).all()

        tot_dette = 0.0
        tot_avoir = 0.0
        
        for d in debts:
            row = self.hist_table.rowCount()
            self.hist_table.insertRow(row)
            
            type_str = d.reference_type
            ref = str(d.reference_id)
            date_str = d.created_at[:10]
            montant = d.total_amount
            reste = d.remaining_amount
            
            if d.reference_type == "PURCHASE":
                type_str = "BR"
                purch = self.db_session.query(Purchase).get(d.reference_id)
                if purch: ref = purch.purchase_number
            elif d.reference_type == "SUPPLIER_INVOICE":
                type_str = "Facture"
                inv = self.db_session.query(SupplierInvoice).get(d.reference_id)
                if inv: ref = inv.invoice_number or f"FACT-{inv.id}"
            elif d.reference_type == "SUPPLIER_RETURN":
                type_str = "Avoir/Retour"
                sr = self.db_session.query(SupplierReturn).get(d.reference_id)
                if sr: 
                    ref = sr.return_number or f"RET-{sr.id}"
                    montant = sr.total_amount
            elif d.reference_type == "PAYMENT":
                type_str = "Paiement"
                ref = f"PAI-{d.id}"
                
            self.hist_table.setItem(row, 0, QTableWidgetItem(date_str))
            
            t_item = QTableWidgetItem(type_str)
            t_item.setData(Qt.UserRole, (d.reference_type, d.reference_id))
            self.hist_table.setItem(row, 1, t_item)
            
            self.hist_table.setItem(row, 2, QTableWidgetItem(ref))
            # Format montant. If Avoir or Paiement, could be negative.
            amount_str = f"-{abs(montant):.2f}" if d.reference_type in ["SUPPLIER_RETURN", "PAYMENT"] else f"{abs(montant):.2f}"
            self.hist_table.setItem(row, 3, QTableWidgetItem(amount_str))
            
            r_item = QTableWidgetItem(f"{abs(reste):.2f}")
            if reste > 0 and d.reference_type not in ["SUPPLIER_RETURN", "PAYMENT"]:
                r_item.setForeground(QBrush(QColor("#C0392B")))
            self.hist_table.setItem(row, 4, r_item)
            
            # Calculate total dette
            if d.remaining_amount > 0:
                tot_dette += d.remaining_amount
            elif d.remaining_amount < 0:
                tot_avoir += abs(d.remaining_amount)

        net = tot_dette - tot_avoir
        if net > 0:
            self.lbl_dette.setText(f"<span style='color:#C0392B;'>{net:,.2f} DA</span> (A Payer)".replace(",", " "))
        else:
            self.lbl_dette.setText(f"<span style='color:#2980B9;'>{abs(net):,.2f} DA</span> (Avoir)".replace(",", " "))
            
        self._set_actions_enabled(True)

    def _show_document_creator(self, doc_type="Bon de Réception (BR)"):
        if not self.current_supplier:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un fournisseur d'abord.")
            return
            
        self._close_creator()
            
        creator = SupplierDocumentCreationDialog(self.user, self.current_supplier, self)
        creator.setWindowFlags(Qt.Widget)
        
        creator.doc_type_combo.setCurrentText(doc_type)
        creator.rejected.connect(self._close_creator)
        creator.accepted.connect(self._on_doc_saved)
        
        self.right_stack.addWidget(creator)
        self.right_stack.setCurrentIndex(1)
        
    def _close_creator(self):
        self.right_stack.setCurrentIndex(0)
        if self.right_stack.count() > 1:
            widget = self.right_stack.widget(1)
            self.right_stack.removeWidget(widget)
            widget.deleteLater()
            
    def _on_doc_saved(self):
        self._close_creator()
        self._load_detail()

    def _on_edit_current_supplier(self):
        if not self.current_supplier: return
        dialog = SupplierDialog(self.user, supplier=self.current_supplier, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())
            self._load_detail()

    def _export_etat_dettes(self):
        if not self.current_supplier: return
        from app.utils.pdf_exporter import PDFExporter
        from PySide6.QtWidgets import QFileDialog
        import os
        from datetime import datetime
        d = QFileDialog.getSaveFileName(self, "Enregistrer Etat des Dettes", 
            f"Etat_Dettes_{self.current_supplier.name}.pdf", "PDF (*.pdf)")
        if d[0]:
            try:
                PDFExporter.export_etat_dettes_to_pdf(
                    d[0], self.db_session, self.current_supplier.id,
                    "2000-01-01", datetime.now().strftime("%Y-%m-%d")
                )
                QMessageBox.information(self, "Succès", "Fichier PDF généré avec succès.")
                os.startfile(d[0])
            except Exception as e:
                QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")

    def _on_hist_double_clicked(self, item):
        row = item.row()
        data = self.hist_table.item(row, 1).data(Qt.UserRole)
        if not data: return
        doc_type, doc_id = data
        
        try:
            from app.utils.pdf_exporter import PDFExporter
            import os
            from PySide6.QtWidgets import QFileDialog

            if doc_type == "PURCHASE":
                # Generate and open BR/BC PDF
                from app.models.purchase import Purchase
                from app.models.purchase_order import PurchaseOrder
                purch = self.db_session.query(Purchase).get(doc_id)
                bc = self.db_session.query(PurchaseOrder).get(doc_id)
                ref = purch.purchase_number if purch else (bc.order_number if bc else f"Doc-{doc_id}")
                
                d = QFileDialog.getSaveFileName(self, "Enregistrer Document", f"Doc_{ref}.pdf", "PDF (*.pdf)")
                if d[0]:
                    PDFExporter.export_purchase_to_pdf(d[0], self.db_session, doc_id, is_order=bool(bc))
                    os.startfile(d[0])

            elif doc_type == "SUPPLIER_INVOICE":
                from ui.dialogs.supplier_invoice_dialog import SupplierInvoiceDialog
                inv = self.db_session.query(SupplierInvoice).get(doc_id)
                if inv:
                    dlg = SupplierInvoiceDialog(self.user, invoice=inv, parent=self)
                    dlg.exec()
            elif doc_type == "SUPPLIER_RETURN":
                from ui.pages.supplier_returns_page import SupplierReturnDialog
                from app.models.supplier_return import SupplierReturn
                ret = self.db_session.query(SupplierReturn).get(doc_id)
                if ret:
                    self.db_session.refresh(ret)
                    dlg = SupplierReturnDialog(self.db_session, self.user, supplier_return=ret, parent=self)
                    dlg.exec()
            elif doc_type == "PAYMENT":
                d = QFileDialog.getSaveFileName(self, "Enregistrer Reçu de Paiement", f"Paiement_{doc_id}.pdf", "PDF (*.pdf)")
                if d[0]:
                    PDFExporter.export_payment_receipt_to_pdf(d[0], self.db_session, doc_id)
                    os.startfile(d[0])
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ouverture: {str(e)}")

    def _create_avoir(self):
        if not self.current_supplier: return
        try:
            from ui.pages.supplier_returns_page import SupplierReturnDialog
            dlg = SupplierReturnDialog(self.db_session, self.user, parent=self)
            if dlg.exec():
                self._load_detail()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))

    def _create_payment(self):
        if not self.current_supplier: return
        try:
            from ui.dialogs.supplier_payment_dialog import SupplierPaymentDialog
            dlg = SupplierPaymentDialog(self.user, self)
            for idx in range(dlg.supplier_combo.count()):
                if dlg.supplier_combo.itemData(idx) == self.current_supplier.id:
                    dlg.supplier_combo.setCurrentIndex(idx)
                    break
            if dlg.exec():
                self._load_detail()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur : {e}")

    def _create_reclamation(self):
        if not self.current_supplier: return
        try:
            from ui.dialogs.reclamation_dialog import ReclamationDialog
            dlg = ReclamationDialog(self.user, parent=self)
            # Reclamation dialog might not support pre-selecting supplier via direct attribute if it expects clients mostly,
            # but opening it satisfies the core feature.
            if dlg.exec():
                self._load_detail()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))
