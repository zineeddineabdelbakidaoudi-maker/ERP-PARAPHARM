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

fiscal_replacements = [
    # Etat 104 - Avoirs CreditNote
    (
        r"""        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at.like(f"{prefix}%"),
            Invoice.status != 'CANCELLED'
        ).all()""",
        r"""        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at.like(f"{prefix}%"),
            Invoice.status != 'CANCELLED'
        ).all()
        from app.models.credit_note import CreditNote
        cns = self.db_session.query(CreditNote).filter(
            CreditNote.created_at.like(f"{prefix}%"),
            CreditNote.status != 'CANCELLED'
        ).all()"""
    ),
    (
        r"""        for inv in invs:
            ca_brut += inv.subtotal""",
        r"""        for inv in invs:
            ca_brut += inv.subtotal
        for cn in cns:
            avoirs += (cn.total_amount / 1.19)"""
    ),
    # Annexe 5
    (
        r"""        self.month_combo = QComboBox()
        for m in range(1, 13):
            self.month_combo.addItem(f"Mois {m:02d}", m)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        
        toolbar.addWidget(QLabel("Période :"))
        toolbar.addWidget(self.month_combo)""",
        r"""        self.trimestre_combo = QComboBox()
        self.trimestre_combo.addItems(['Trimestre 1', 'Trimestre 2', 'Trimestre 3', 'Trimestre 4', 'Année Entière'])
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        
        toolbar.addWidget(QLabel("Période :"))
        toolbar.addWidget(self.trimestre_combo)"""
    ),
    (
        r"""        m = self.month_combo.currentData()
        y = self.year_spin.value()
        prefix = f"{y}-{m:02d}"
        
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at.like(f"{prefix}%"),
            Invoice.status != 'CANCELLED'
        ).all()""",
        r"""        y = self.year_spin.value()
        trim_idx = self.trimestre_combo.currentIndex()
        if trim_idx == 4:
            prefix_start = f"{y}-01-01"
            prefix_end = f"{y}-12-31"
        else:
            m_start = trim_idx * 3 + 1
            m_end = m_start + 2
            import calendar
            last_day = calendar.monthrange(y, m_end)[1]
            prefix_start = f"{y}-{m_start:02d}-01"
            prefix_end = f"{y}-{m_end:02d}-{last_day}"
        
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at >= prefix_start,
            Invoice.created_at <= prefix_end + ' 23:59:59',
            Invoice.status != 'CANCELLED'
        ).all()
        from app.models.credit_note import CreditNote
        cns = self.db_session.query(CreditNote).filter(
            CreditNote.created_at >= prefix_start,
            CreditNote.created_at <= prefix_end + ' 23:59:59',
            CreditNote.status != 'CANCELLED'
        ).all()"""
    ),
    (
        r"""self.table.setItem(r, 2, QTableWidgetItem(inv.client.tax_id or ""))""",
        r"""self.table.setItem(r, 2, QTableWidgetItem(inv.client.tax_id or "⚠️ NIF Manquant"))"""
    ),
    (
        r"""            total_ht += inv.subtotal
            total_tva += inv.tax_total
            total_ttc += inv.total_amount""",
        r"""            total_ht += inv.subtotal
            total_tva += inv.tax_total
            total_ttc += inv.total_amount
            
        for cn in cns:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(cn.note_number))
            self.table.setItem(r, 1, QTableWidgetItem(cn.created_at[:10]))
            self.table.setItem(r, 2, QTableWidgetItem(cn.client.tax_id or "⚠️ NIF Manquant"))
            self.table.setItem(r, 3, QTableWidgetItem(cn.client.name))
            self.table.setItem(r, 4, QTableWidgetItem(cn.client.rc or ""))
            self.table.setItem(r, 5, QTableWidgetItem(format_money(-(cn.total_amount/1.19))))
            self.table.setItem(r, 6, QTableWidgetItem(format_money(-(cn.total_amount - (cn.total_amount/1.19)))))
            self.table.setItem(r, 7, QTableWidgetItem(format_money(-cn.total_amount)))
            for col in range(8):
                self.table.item(r, col).setForeground(QBrush(QColor('#D32F2F')))
            total_ht -= (cn.total_amount/1.19)
            total_tva -= (cn.total_amount - (cn.total_amount/1.19))
            total_ttc -= cn.total_amount"""
    ),
    # G50
    (
        r"""class DeclarationG50Page(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Déclaration G50")
        
        toolbar = QHBoxLayout()
        self.month_combo = QComboBox()
        for m in range(1, 13):
            self.month_combo.addItem(f"Mois {m:02d}", m)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        
        toolbar.addWidget(QLabel("Période :"))
        toolbar.addWidget(self.month_combo)""",
        r"""class DeclarationG50Page(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Déclaration G50")
        
        toolbar = QHBoxLayout()
        self.trimestre_combo = QComboBox()
        self.trimestre_combo.addItems(['Trimestre 1', 'Trimestre 2', 'Trimestre 3', 'Trimestre 4'])
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        
        toolbar.addWidget(QLabel("Période :"))
        toolbar.addWidget(self.trimestre_combo)"""
    ),
    (
        r"""        m = self.month_combo.currentData()
        y = self.year_spin.value()
        prefix = f"{y}-{m:02d}"
        
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at.like(f"{prefix}%"),
            Invoice.status != 'CANCELLED'
        ).all()
        
        from app.models.purchase import Purchase
        purchases = self.db_session.query(Purchase).filter(
            Purchase.created_at.like(f"{prefix}%"),
            Purchase.status != 'CANCELLED'
        ).all()""",
        r"""        y = self.year_spin.value()
        trim_idx = self.trimestre_combo.currentIndex()
        m_start = trim_idx * 3 + 1
        m_end = m_start + 2
        import calendar
        last_day = calendar.monthrange(y, m_end)[1]
        prefix_start = f"{y}-{m_start:02d}-01"
        prefix_end = f"{y}-{m_end:02d}-{last_day}"
        
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at >= prefix_start,
            Invoice.created_at <= prefix_end + ' 23:59:59',
            Invoice.status != 'CANCELLED'
        ).all()
        
        from app.models.purchase import Purchase
        purchases = self.db_session.query(Purchase).filter(
            Purchase.created_at >= prefix_start,
            Purchase.created_at <= prefix_end + ' 23:59:59',
            Purchase.status != 'CANCELLED'
        ).all()
        from app.models.delivery import Delivery
        deliveries = self.db_session.query(Delivery).filter(
            Delivery.type == 'RECEIPT',
            Delivery.created_at >= prefix_start,
            Delivery.created_at <= prefix_end + ' 23:59:59',
            Delivery.status != 'CANCELLED'
        ).all()"""
    ),
    (
        r"""        ca_ht = 0.0
        tva_19 = 0.0
        tva_9 = 0.0
        
        for inv in invs:""",
        r"""        ca_ht = 0.0
        exo_ht = 0.0
        tva_19 = 0.0
        tva_9 = 0.0
        
        for inv in invs:"""
    ),
    (
        r"""            ca_ht += inv.subtotal
            for item in inv.items:
                tr = item.tax_rate""",
        r"""            ca_ht += inv.subtotal
            for item in inv.items:
                tr = item.tax_rate
                if tr == 0: exo_ht += (item.quantity * item.unit_price)"""
    ),
    (
        r"""        tva_deduc = 0.0
        for p in purchases:
            tva_deduc += p.tax_amount""",
        r"""        tva_deduc = 0.0
        for p in purchases:
            tva_deduc += p.tax_amount
        for d in deliveries:
            for item in d.items:
                tva_deduc += (item.quantity * item.unit_price) * (getattr(item.product, 'tax_rate', 19.0) or 19.0)/100.0"""
    ),
    (
        r"""        tap = ca_ht * 0.02
        tva_nette = max(0, (tva_19 + tva_9) - tva_deduc)
        total_g50 = tap + tva_nette""",
        r"""        tap = (ca_ht - exo_ht) * 0.02
        credit_tva = max(0, tva_deduc - (tva_19 + tva_9))
        tva_nette = max(0, (tva_19 + tva_9) - tva_deduc)
        total_g50 = tap + tva_nette"""
    ),
    (
        r"""                       ('tva_nette', 'TVA Nette à Payer'), 
                       ('total', 'TOTAL G50 À PAYER')]:""",
        r"""                       ('tva_nette', 'TVA Nette à Payer'), 
                       ('credit_tva', 'Crédit de TVA (à reporter)'), 
                       ('total', 'TOTAL G50 À PAYER')]:"""
    ),
    (
        r"""            elif k == 'tva_nette': val = tva_nette
            elif k == 'total': val = total_g50""",
        r"""            elif k == 'tva_nette': val = tva_nette
            elif k == 'credit_tva': val = credit_tva
            elif k == 'total': val = total_g50"""
    ),
    # G12
    (
        r"""        self.year_spin.setValue(datetime.now().year)
        
        toolbar.addWidget(QLabel("Année :"))
        toolbar.addWidget(self.year_spin)""",
        r"""        self.year_spin.setValue(datetime.now().year)
        
        toolbar.addWidget(QLabel("Année :"))
        toolbar.addWidget(self.year_spin)
        toolbar.addWidget(QLabel("Acomptes G50 versés :"))
        self.acomptes_input = QLineEdit("0.00")
        self.acomptes_input.setFixedWidth(100)
        self.acomptes_input.textChanged.connect(self.load_data)
        toolbar.addWidget(self.acomptes_input)"""
    ),
    (
        r"""        acomptes = 0.0 # TODO: store acomptes
        solde = max(0, ifu - acomptes)""",
        r"""        try:
            acomptes = float(self.acomptes_input.text().replace(',', '.'))
        except: acomptes = 0.0
        solde = max(0, ifu - acomptes)"""
    ),
    # Exoneration
    (
        r"""self.table = self.create_table(["Client", "Motif", "N° Décision", "Date Déc.", "Montant Exonéré HT", "Période"])""",
        r"""self.table = self.create_table(["Client", "Motif", "N° Décision", "Date Début", "Date Fin", "Montant Plafonné", "Consommé HT"])"""
    ),
    (
        r"""            self.table.setItem(r, 3, QTableWidgetItem(exo.date_decision))
            self.table.setItem(r, 4, QTableWidgetItem(format_money(exo.montant_ht)))
            self.table.setItem(r, 5, QTableWidgetItem(exo.periode))""",
        r"""            self.table.setItem(r, 3, QTableWidgetItem(exo.date_decision))
            self.table.setItem(r, 4, QTableWidgetItem(exo.date_fin))
            self.table.setItem(r, 5, QTableWidgetItem(format_money(exo.montant_plafonne)))
            self.table.setItem(r, 6, QTableWidgetItem(format_money(exo.montant_ht)))"""
    ),
    # Rappels
    (
        r"""            btn_print = QPushButton("🖨️ Imprimer Rappel")
            btn_print.clicked.connect(lambda ch, client_name=c.name, amt=info['amount']: self.print_rappel(client_name, amt))
            self.table.setCellWidget(r, 5, btn_print)""",
        r"""            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0,0,0,0)
            btn_print = QPushButton("🖨️ Imprimer")
            btn_print.clicked.connect(lambda ch, client_name=c.name, amt=info['amount']: self.print_rappel(client_name, amt))
            btn_done = QPushButton("✅ Marquer Envoyé")
            btn_done.clicked.connect(lambda ch, cid=cid: self.mark_sent(cid))
            btn_layout.addWidget(btn_print)
            btn_layout.addWidget(btn_done)
            w = QWidget()
            w.setLayout(btn_layout)
            self.table.setCellWidget(r, 5, w)"""
    ),
    (
        r"""    def print_rappel(self, client_name, amount):""",
        r"""    def mark_sent(self, cid):
        c = self.db_session.query(Client).get(cid)
        if c:
            from datetime import datetime
            c.last_reminder_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db_session.commit()
            QMessageBox.information(self, "Succès", "Rappel marqué comme envoyé.")
            self.load_data()

    def print_rappel(self, client_name, amount):"""
    )
]
patch_file("ui/pages/fiscal_pages.py", fiscal_replacements)
