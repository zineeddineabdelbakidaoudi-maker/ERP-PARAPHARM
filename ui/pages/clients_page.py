"""
ParaFarm ERP — Clients Page (Master-Detail Design)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSplitter, QFrame, QFormLayout, QStackedWidget, QAbstractItemView, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from app.core.database import get_session
from app.services.auth_service import get_current_session
from app.services.client_service import ClientService
from app.models.client import Client
from app.models.debt import Debt
from app.models.sale import Sale
from app.models.invoice import Invoice
from app.models.credit_note import CreditNote
from ui.dialogs.client_dialog import ClientDialog

class ClientsPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.service = ClientService(self.db_session)
        self.current_client = None
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(15)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un client (Code, Nom, Téléphone)...")
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
        can_create = session.has_permission("CLIENTS", "CREATE") if session else False

        add_btn = QPushButton("➕ Nouveau Client")
        add_btn.setMinimumHeight(35)
        add_btn.clicked.connect(self._on_add_client)
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
        
        self.btn_edit_client = QPushButton("✏️ Modifier Info")
        self.btn_edit_client.setStyleSheet(btn_style)
        self.btn_edit_client.clicked.connect(self._on_edit_current_client)
        actions_layout.addWidget(self.btn_edit_client)
        
        self.btn_etat = QPushButton("🖨️ Etat Créances")
        self.btn_etat.setStyleSheet(btn_style)
        self.btn_etat.clicked.connect(self._export_etat_creances)
        actions_layout.addWidget(self.btn_etat)
        
        self.btn_bl = QPushButton("📄 Nouveau BL / Facture")
        self.btn_bl.setStyleSheet(btn_style.replace("#F8F9FA", "#3498DB").replace("#2C3E50", "white"))
        self.btn_bl.clicked.connect(lambda: self._show_document_creator("Bon de Livraison (BL)"))
        actions_layout.addWidget(self.btn_bl)
        
        self.btn_avoir = QPushButton("↩️ Nouvel Avoir")
        self.btn_avoir.setStyleSheet(btn_style)
        self.btn_avoir.clicked.connect(self._create_avoir)
        actions_layout.addWidget(self.btn_avoir)
        
        self.btn_versement = QPushButton("💰 Versement")
        self.btn_versement.setStyleSheet(btn_style)
        self.btn_versement.clicked.connect(self._create_versement)
        actions_layout.addWidget(self.btn_versement)
        
        self.btn_reclamation = QPushButton("⚠️ Réclamation")
        self.btn_reclamation.setStyleSheet(btn_style)
        self.btn_reclamation.clicked.connect(self._create_reclamation)
        actions_layout.addWidget(self.btn_reclamation)
        
        main_layout.addWidget(self.actions_panel)

        # ─── MAIN CONTENT SPLITTER ───
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Client Info Frame
        info_frame = QFrame()
        info_layout = QFormLayout(info_frame)
        self.lbl_name = QLabel("---")
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 16px; color: #2C3E50;")
        self.lbl_code = QLabel("---")
        self.lbl_phone = QLabel("---")
        self.lbl_credit = QLabel("---")
        self.lbl_solde = QLabel("---")
        
        info_layout.addRow("Nom :", self.lbl_name)
        info_layout.addRow("Code :", self.lbl_code)
        info_layout.addRow("Téléphone :", self.lbl_phone)
        info_layout.addRow("Crédit Max :", self.lbl_credit)
        info_layout.addRow("Solde Actuel :", self.lbl_solde)
        
        self.detail_left = QFrame()
        self.detail_left.setProperty("class", "card")
        self.detail_left.setMinimumWidth(400)
        # Removed maximum width to allow it to expand into the empty space
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
        
        # Page 0: Table of clients
        page_table = QWidget()
        pt_layout = QVBoxLayout(page_table)
        pt_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Code", "Nom Complet", "Téléphone", "Crédit Max"])
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
        if query:
            clients = self.service.search_clients(query)
        else:
            res = self.service.get_all_clients()
            clients = res.get("items", []) if isinstance(res, dict) else res

        for c in clients:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            c_item = QTableWidgetItem(c.code)
            c_item.setData(Qt.UserRole, c.id)
            self.table.setItem(row, 0, c_item)
            self.table.setItem(row, 1, QTableWidgetItem(c.name))
            self.table.setItem(row, 2, QTableWidgetItem(c.phone or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{c.credit_limit:.2f} DA"))

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_add_client(self):
        dialog = ClientDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.current_client = None
            self._clear_detail()
            return
            
        client_id = selected[0].data(Qt.UserRole)
        self.current_client = self.db_session.query(Client).get(client_id)
        if self.current_client:
            self._load_detail()

    def _set_actions_enabled(self, enabled: bool):
        self.btn_edit_client.setEnabled(enabled)
        self.btn_etat.setEnabled(enabled)
        self.btn_bl.setEnabled(enabled)
        self.btn_avoir.setEnabled(enabled)
        self.btn_versement.setEnabled(enabled)
        self.btn_reclamation.setEnabled(enabled)

    def _clear_detail(self):
        self.lbl_name.setText("---")
        self.lbl_code.setText("---")
        self.lbl_phone.setText("---")
        self.lbl_credit.setText("---")
        self.lbl_solde.setText("---")
        self.hist_table.setRowCount(0)
        self._set_actions_enabled(False)
        self._close_creator()

    def _load_detail(self):
        c = self.current_client
        self.lbl_name.setText(c.name)
        self.lbl_code.setText(c.code)
        self.lbl_phone.setText(c.phone or "—")
        self.lbl_credit.setText(f"{c.credit_limit:,.2f} DA".replace(",", " "))
        
        # Load Historique
        self.hist_table.setRowCount(0)
        debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "CLIENT",
            Debt.entity_id == c.id,
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
            
            if d.reference_type == "SALE":
                type_str = "BL"
                sale = self.db_session.query(Sale).get(d.reference_id)
                if sale: ref = sale.sale_number
            elif d.reference_type == "SALE_INVOICE":
                type_str = "Facture"
                inv = self.db_session.query(Invoice).get(d.reference_id)
                if inv: ref = inv.invoice_number
            elif d.reference_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                type_str = "Avoir"
                cn = self.db_session.query(CreditNote).get(d.reference_id)
                if cn: 
                    ref = cn.note_number or f"BR{cn.id}"
                    montant = cn.total_amount
            elif d.reference_type == "VERSEMENT":
                type_str = "Versement"
                ref = f"VRS-{d.id}"
                
            self.hist_table.setItem(row, 0, QTableWidgetItem(date_str))
            
            t_item = QTableWidgetItem(type_str)
            t_item.setData(Qt.UserRole, (d.reference_type, d.reference_id))
            self.hist_table.setItem(row, 1, t_item)
            
            self.hist_table.setItem(row, 2, QTableWidgetItem(ref))
            # Format montant. If Avoir, show as negative.
            amount_str = f"-{abs(montant):.2f}" if d.reference_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"] else f"{abs(montant):.2f}"
            self.hist_table.setItem(row, 3, QTableWidgetItem(amount_str))
            
            r_item = QTableWidgetItem(f"{abs(reste):.2f}")
            if reste > 0 and d.reference_type not in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                r_item.setForeground(QBrush(QColor("#C0392B")))
            self.hist_table.setItem(row, 4, r_item)
            
            # Calculate total solde
            if d.remaining_amount > 0:
                tot_dette += d.remaining_amount
            elif d.remaining_amount < 0:
                tot_avoir += abs(d.remaining_amount)

        net = tot_dette - tot_avoir
        if net > 0:
            self.lbl_solde.setText(f"<span style='color:#C0392B;'>{net:,.2f} DA</span> (Dette)".replace(",", " "))
        else:
            self.lbl_solde.setText(f"<span style='color:#2980B9;'>{abs(net):,.2f} DA</span> (Avoir)".replace(",", " "))
            
        self._set_actions_enabled(True)

    def _show_document_creator(self, doc_type="Bon de Livraison (BL)"):
        if not self.current_client:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un client d'abord.")
            return
            
        self._close_creator()
            
        from ui.dialogs.client_document_creation_dialog import ClientDocumentCreationDialog
        creator = ClientDocumentCreationDialog(self.user, self.current_client, self)
        creator.setWindowFlags(Qt.Widget)
        
        creator.doc_type_combo.setCurrentText(doc_type)
        creator.rejected.connect(self._close_creator)
        creator.accepted.connect(self._on_doc_saved)
        
        for btn in creator.findChildren(QPushButton):
            if btn.text() == "Annuler":
                btn.setText("Retour à la liste")
        
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
        self._load_detail() # Refresh history

    def _on_edit_current_client(self):
        if not self.current_client: return
        dialog = ClientDialog(self.user, client=self.current_client, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())
            self._load_detail()

    def _export_etat_creances(self):
        if not self.current_client: return
        from app.utils.pdf_exporter import PDFExporter
        from PySide6.QtWidgets import QFileDialog
        import os
        from datetime import datetime
        d = QFileDialog.getSaveFileName(self, "Enregistrer Etat des Créances", 
            f"Etat_Creances_{self.current_client.name}.pdf", "PDF (*.pdf)")
        if d[0]:
            try:
                PDFExporter.export_etat_creances_to_pdf(
                    d[0], self.db_session, self.current_client.id,
                    "2000-01-01", datetime.now().strftime("%Y-%m-%d")
                )
                QMessageBox.information(self, "Succès", "Fichier PDF généré avec succès.")
                os.startfile(d[0])
            except Exception as e:
                QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\n{e}")

    def _on_hist_double_clicked(self, item):
        row = item.row()
        data = self.hist_table.item(row, 1).data(Qt.UserRole)
        if not data: return
        doc_type, doc_id = data
        
        try:
            if doc_type == "SALE":
                from ui.dialogs.view_sale_dialog import ViewSaleDialog
                dlg = ViewSaleDialog(doc_id, parent=self)
                dlg.exec()
            elif doc_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                from ui.pages.credit_notes_page import CreditNoteDialog
                cn = self.db_session.query(CreditNote).get(doc_id)
                if cn:
                    self.db_session.refresh(cn)
                    dlg = CreditNoteDialog(self.db_session, self.user, note=cn, parent=self)
                    dlg.exec()
            elif doc_type == "SALE_INVOICE":
                from ui.dialogs.invoice_dialog import InvoiceDialog
                inv = self.db_session.query(Invoice).get(doc_id)
                if inv:
                    dlg = InvoiceDialog(self.db_session, self.user, invoice=inv, parent=self)
                    dlg.exec()
            elif doc_type == "VERSEMENT":
                QMessageBox.information(self, "Versement", f"Versement ID: {doc_id}. Détails dans l'historique des paiements.")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ouverture: {str(e)}")

    def _create_avoir(self):
        if not self.current_client: return
        try:
            from ui.pages.credit_notes_page import CreditNoteDialog
            dlg = CreditNoteDialog(self.db_session, self.user, parent=self)
            if dlg.exec():
                self._load_detail()
        except Exception:
            pass

    def _create_versement(self):
        if not self.current_client: return
        try:
            from ui.dialogs.client_payment_dialog import ClientPaymentDialog
            dlg = ClientPaymentDialog(self.user, self)
            for idx in range(dlg.client_combo.count()):
                if dlg.client_combo.itemData(idx) == self.current_client.id:
                    dlg.client_combo.setCurrentIndex(idx)
                    break
            if dlg.exec():
                self._load_detail()
        except Exception:
            pass

    def _create_reclamation(self):
        if not self.current_client: return
        try:
            from ui.pages.reclamations_client_page import ReclamationDialog
            from app.models.reclamation import Reclamation
            # In a real scenario, we prepopulate client. Here we just open the general dialog.
            dlg = ReclamationDialog(self.user, parent=self)
            if dlg.exec():
                self._load_detail()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Action impossible : {e}")

