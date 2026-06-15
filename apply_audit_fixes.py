import os
import re

def patch_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for search, replace in replacements:
        if search in content:
            content = content.replace(search, replace)
        else:
            print(f"Warning: Could not find '{search[:30]}...' in {filepath}")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# 1. invoices_page.py - TVA checkbox for exonerated clients
invoices_replacements = [
    (
        "client_id = self.client_combo.currentData()\\n        if not client_id:\\n            return",
        "client_id = self.client_combo.currentData()\\n        if not client_id:\\n            self.tva_checkbox.setChecked(True)\\n            return\\n        from app.models.fiscal import ExonerationTVA\\n        from datetime import datetime\\n        now_str = datetime.now().strftime('%Y-%m-%d')\\n        exo = self.db_session.query(ExonerationTVA).filter(ExonerationTVA.client_id == client_id).filter((ExonerationTVA.date_fin >= now_str) | (ExonerationTVA.date_fin == None) | (ExonerationTVA.date_fin == '')).first()\\n        if exo:\\n            self.tva_checkbox.setChecked(False)\\n        else:\\n            self.tva_checkbox.setChecked(True)"
    )
]
patch_file("ui/pages/invoices_page.py", invoices_replacements)

# 2. fiscal_pages.py - A LOT of changes
fiscal_replacements = [
    # Etat 104 - Avoirs CreditNote
    (
        "invs = self.db_session.query(Invoice).filter(\\n            Invoice.created_at.like(f\\"{prefix}%\\"),\\n            Invoice.status != 'CANCELLED'\\n        ).all()",
        "invs = self.db_session.query(Invoice).filter(\\n            Invoice.created_at.like(f\\"{prefix}%\\"),\\n            Invoice.status != 'CANCELLED'\\n        ).all()\\n        from app.models.credit_note import CreditNote\\n        cns = self.db_session.query(CreditNote).filter(\\n            CreditNote.created_at.like(f\\"{prefix}%\\"),\\n            CreditNote.status != 'CANCELLED'\\n        ).all()"
    ),
    (
        "for inv in invs:\\n            ca_brut += inv.subtotal",
        "for inv in invs:\\n            ca_brut += inv.subtotal\\n        for cn in cns:\\n            avoirs += (cn.total_amount / 1.19)  # Approx HT deduction"
    ),
    # Annexe 5 - Trimestre + CreditNote
    (
        "self.month_combo = QComboBox()\\n        for m in range(1, 13):\\n            self.month_combo.addItem(f\\"Mois {m:02d}\\", m)\\n        \\n        self.year_spin = QSpinBox()\\n        self.year_spin.setRange(2000, 2100)\\n        self.year_spin.setValue(datetime.now().year)\\n        \\n        toolbar.addWidget(QLabel(\\"Période :\\"))\\n        toolbar.addWidget(self.month_combo)",
        "self.trimestre_combo = QComboBox()\\n        self.trimestre_combo.addItems(['Trimestre 1', 'Trimestre 2', 'Trimestre 3', 'Trimestre 4', 'Année Entière'])\\n        \\n        self.year_spin = QSpinBox()\\n        self.year_spin.setRange(2000, 2100)\\n        self.year_spin.setValue(datetime.now().year)\\n        \\n        toolbar.addWidget(QLabel(\\"Période :\\"))\\n        toolbar.addWidget(self.trimestre_combo)"
    ),
    (
        "m = self.month_combo.currentData()\\n        y = self.year_spin.value()\\n        prefix = f\\"{y}-{m:02d}\\"\\n        \\n        invs = self.db_session.query(Invoice).filter(\\n            Invoice.created_at.like(f\\"{prefix}%\\"),\\n            Invoice.status != 'CANCELLED'\\n        ).all()",
        "y = self.year_spin.value()\\n        trim_idx = self.trimestre_combo.currentIndex()\\n        if trim_idx == 4:\\n            prefix_start = f\\"{y}-01-01\\"\\n            prefix_end = f\\"{y}-12-31\\"\\n        else:\\n            m_start = trim_idx * 3 + 1\\n            m_end = m_start + 2\\n            import calendar\\n            last_day = calendar.monthrange(y, m_end)[1]\\n            prefix_start = f\\"{y}-{m_start:02d}-01\\"\\n            prefix_end = f\\"{y}-{m_end:02d}-{last_day}\\"\\n        \\n        invs = self.db_session.query(Invoice).filter(\\n            Invoice.created_at >= prefix_start,\\n            Invoice.created_at <= prefix_end + ' 23:59:59',\\n            Invoice.status != 'CANCELLED'\\n        ).all()\\n        from app.models.credit_note import CreditNote\\n        cns = self.db_session.query(CreditNote).filter(\\n            CreditNote.created_at >= prefix_start,\\n            CreditNote.created_at <= prefix_end + ' 23:59:59',\\n            CreditNote.status != 'CANCELLED'\\n        ).all()"
    ),
    (
        "self.table.setItem(r, 2, QTableWidgetItem(inv.client.tax_id or \\"\\"))",
        "self.table.setItem(r, 2, QTableWidgetItem(inv.client.tax_id or \\"⚠️ NIF Manquant\\"))"
    ),
    (
        "total_ht += inv.subtotal\\n            total_tva += inv.tax_total\\n            total_ttc += inv.total_amount",
        "total_ht += inv.subtotal\\n            total_tva += inv.tax_total\\n            total_ttc += inv.total_amount\\n        for cn in cns:\\n            r = self.table.rowCount()\\n            self.table.insertRow(r)\\n            self.table.setItem(r, 0, QTableWidgetItem(cn.note_number))\\n            self.table.setItem(r, 1, QTableWidgetItem(cn.created_at[:10]))\\n            self.table.setItem(r, 2, QTableWidgetItem(cn.client.tax_id or \\"⚠️ NIF Manquant\\"))\\n            self.table.setItem(r, 3, QTableWidgetItem(cn.client.name))\\n            self.table.setItem(r, 4, QTableWidgetItem(cn.client.rc or \\"\\"))\\n            self.table.setItem(r, 5, QTableWidgetItem(format_money(-(cn.total_amount/1.19))))\\n            self.table.setItem(r, 6, QTableWidgetItem(format_money(-(cn.total_amount - (cn.total_amount/1.19)))))\\n            self.table.setItem(r, 7, QTableWidgetItem(format_money(-cn.total_amount)))\\n            for col in range(8):\\n                self.table.item(r, col).setForeground(QBrush(QColor('#D32F2F')))\\n            total_ht -= (cn.total_amount/1.19)\\n            total_tva -= (cn.total_amount - (cn.total_amount/1.19))\\n            total_ttc -= cn.total_amount"
    ),
    # G50 - Trimestre + Delivery + TAP
    (
        "class DeclarationG50Page(BaseFiscalPage):\\n    def __init__(self, user, parent=None):\\n        super().__init__(user, parent)\\n        self.create_header(\\"Déclaration G50\\")\\n        \\n        toolbar = QHBoxLayout()\\n        self.month_combo = QComboBox()\\n        for m in range(1, 13):\\n            self.month_combo.addItem(f\\"Mois {m:02d}\\", m)\\n        \\n        self.year_spin = QSpinBox()\\n        self.year_spin.setRange(2000, 2100)\\n        self.year_spin.setValue(datetime.now().year)\\n        \\n        toolbar.addWidget(QLabel(\\"Période :\\"))\\n        toolbar.addWidget(self.month_combo)",
        "class DeclarationG50Page(BaseFiscalPage):\\n    def __init__(self, user, parent=None):\\n        super().__init__(user, parent)\\n        self.create_header(\\"Déclaration G50\\")\\n        \\n        toolbar = QHBoxLayout()\\n        self.trimestre_combo = QComboBox()\\n        self.trimestre_combo.addItems(['Trimestre 1', 'Trimestre 2', 'Trimestre 3', 'Trimestre 4'])\\n        \\n        self.year_spin = QSpinBox()\\n        self.year_spin.setRange(2000, 2100)\\n        self.year_spin.setValue(datetime.now().year)\\n        \\n        toolbar.addWidget(QLabel(\\"Période :\\"))\\n        toolbar.addWidget(self.trimestre_combo)"
    ),
    (
        "m = self.month_combo.currentData()\\n        y = self.year_spin.value()\\n        prefix = f\\"{y}-{m:02d}\\"",
        "y = self.year_spin.value()\\n        trim_idx = self.trimestre_combo.currentIndex()\\n        m_start = trim_idx * 3 + 1\\n        m_end = m_start + 2\\n        import calendar\\n        last_day = calendar.monthrange(y, m_end)[1]\\n        prefix_start = f\\"{y}-{m_start:02d}-01\\"\\n        prefix_end = f\\"{y}-{m_end:02d}-{last_day}\\""
    ),
    (
        "invs = self.db_session.query(Invoice).filter(\\n            Invoice.created_at.like(f\\"{prefix}%\\"),\\n            Invoice.status != 'CANCELLED'\\n        ).all()\\n        \\n        from app.models.purchase import Purchase\\n        purchases = self.db_session.query(Purchase).filter(\\n            Purchase.created_at.like(f\\"{prefix}%\\"),\\n            Purchase.status != 'CANCELLED'\\n        ).all()",
        "invs = self.db_session.query(Invoice).filter(\\n            Invoice.created_at >= prefix_start,\\n            Invoice.created_at <= prefix_end + ' 23:59:59',\\n            Invoice.status != 'CANCELLED'\\n        ).all()\\n        \\n        from app.models.purchase import Purchase\\n        purchases = self.db_session.query(Purchase).filter(\\n            Purchase.created_at >= prefix_start,\\n            Purchase.created_at <= prefix_end + ' 23:59:59',\\n            Purchase.status != 'CANCELLED'\\n        ).all()\\n        from app.models.delivery import Delivery\\n        deliveries = self.db_session.query(Delivery).filter(\\n            Delivery.type == 'RECEIPT',\\n            Delivery.created_at >= prefix_start,\\n            Delivery.created_at <= prefix_end + ' 23:59:59',\\n            Delivery.status != 'CANCELLED'\\n        ).all()"
    ),
    (
        "ca_ht = 0.0\\n        tva_19 = 0.0\\n        tva_9 = 0.0\\n        \\n        for inv in invs:",
        "ca_ht = 0.0\\n        exo_ht = 0.0\\n        tva_19 = 0.0\\n        tva_9 = 0.0\\n        \\n        for inv in invs:"
    ),
    (
        "ca_ht += inv.subtotal\\n            for item in inv.items:\\n                tr = item.tax_rate",
        "ca_ht += inv.subtotal\\n            for item in inv.items:\\n                tr = item.tax_rate\\n                if tr == 0: exo_ht += (item.quantity * item.unit_price)"
    ),
    (
        "tva_deduc = 0.0\\n        for p in purchases:\\n            tva_deduc += p.tax_amount",
        "tva_deduc = 0.0\\n        for p in purchases:\\n            tva_deduc += p.tax_amount\\n        for d in deliveries:\\n            for item in d.items:\\n                tva_deduc += (item.quantity * item.unit_price) * (getattr(item.product, 'tax_rate', 19.0) or 19.0)/100.0"
    ),
    (
        "tap = ca_ht * 0.02\\n        tva_nette = max(0, (tva_19 + tva_9) - tva_deduc)\\n        total_g50 = tap + tva_nette",
        "tap = (ca_ht - exo_ht) * 0.02\\n        credit_tva = max(0, tva_deduc - (tva_19 + tva_9))\\n        tva_nette = max(0, (tva_19 + tva_9) - tva_deduc)\\n        total_g50 = tap + tva_nette"
    ),
    (
        "('tva_nette', 'TVA Nette à Payer'), \\n                       ('total', 'TOTAL G50 À PAYER')]:",
        "('tva_nette', 'TVA Nette à Payer'), \\n                       ('credit_tva', 'Crédit de TVA (à reporter)'), \\n                       ('total', 'TOTAL G50 À PAYER')]:"
    ),
    (
        "elif k == 'tva_nette': val = tva_nette\\n            elif k == 'total': val = total_g50",
        "elif k == 'tva_nette': val = tva_nette\\n            elif k == 'credit_tva': val = credit_tva\\n            elif k == 'total': val = total_g50"
    ),
    # G12 - Acomptes
    (
        "self.year_spin.setValue(datetime.now().year)\\n        \\n        toolbar.addWidget(QLabel(\\"Année :\\"))\\n        toolbar.addWidget(self.year_spin)",
        "self.year_spin.setValue(datetime.now().year)\\n        \\n        toolbar.addWidget(QLabel(\\"Année :\\"))\\n        toolbar.addWidget(self.year_spin)\\n        toolbar.addWidget(QLabel(\\"Acomptes G50 versés :\\"))\\n        self.acomptes_input = QLineEdit(\\"0.00\\")\\n        self.acomptes_input.setFixedWidth(100)\\n        self.acomptes_input.textChanged.connect(self.load_data)\\n        toolbar.addWidget(self.acomptes_input)"
    ),
    (
        "acomptes = 0.0 # TODO: store acomptes\\n        solde = max(0, ifu - acomptes)",
        "try:\\n            acomptes = float(self.acomptes_input.text().replace(',', '.'))\\n        except: acomptes = 0.0\\n        solde = max(0, ifu - acomptes)"
    ),
    # Exoneration - Motif / Plafond
    (
        "self.table = self.create_table([\\"Client\\", \\"Motif\\", \\"N° Décision\\", \\"Date Déc.\\", \\"Montant Exonéré HT\\", \\"Période\\"])",
        "self.table = self.create_table([\\"Client\\", \\"Motif\\", \\"N° Décision\\", \\"Date Début\\", \\"Date Fin\\", \\"Montant Plafonné\\", \\"Consommé HT\\"])"
    ),
    (
        "self.table.setItem(r, 3, QTableWidgetItem(exo.date_decision))\\n            self.table.setItem(r, 4, QTableWidgetItem(format_money(exo.montant_ht)))\\n            self.table.setItem(r, 5, QTableWidgetItem(exo.periode))",
        "self.table.setItem(r, 3, QTableWidgetItem(exo.date_decision))\\n            self.table.setItem(r, 4, QTableWidgetItem(exo.date_fin))\\n            self.table.setItem(r, 5, QTableWidgetItem(format_money(exo.montant_plafonne)))\\n            self.table.setItem(r, 6, QTableWidgetItem(format_money(exo.montant_ht)))"
    ),
    # Rappels Clients - Envoyé
    (
        "btn_print = QPushButton(\\"🖨️ Imprimer Rappel\\")\\n            btn_print.clicked.connect(lambda ch, client_name=c.name, amt=info['amount']: self.print_rappel(client_name, amt))\\n            self.table.setCellWidget(r, 5, btn_print)",
        "btn_layout = QHBoxLayout()\\n            btn_layout.setContentsMargins(0,0,0,0)\\n            btn_print = QPushButton(\\"🖨️ Imprimer\\")\\n            btn_print.clicked.connect(lambda ch, client_name=c.name, amt=info['amount']: self.print_rappel(client_name, amt))\\n            btn_done = QPushButton(\\"✅ Marquer Envoyé\\")\\n            btn_done.clicked.connect(lambda ch, cid=cid: self.mark_sent(cid))\\n            btn_layout.addWidget(btn_print)\\n            btn_layout.addWidget(btn_done)\\n            w = QWidget()\\n            w.setLayout(btn_layout)\\n            self.table.setCellWidget(r, 5, w)"
    ),
    (
        "def print_rappel(self, client_name, amount):",
        "def mark_sent(self, cid):\\n        c = self.db_session.query(Client).get(cid)\\n        if c:\\n            from datetime import datetime\\n            c.last_reminder_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')\\n            self.db_session.commit()\\n            QMessageBox.information(self, \\"Succès\\", \\"Rappel marqué comme envoyé.\\")\\n            self.load_data()\\n\\n    def print_rappel(self, client_name, amount):"
    )
]
patch_file("ui/pages/fiscal_pages.py", fiscal_replacements)
