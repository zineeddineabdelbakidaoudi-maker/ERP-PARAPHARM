import sys

with open('app/utils/pdf_exporter.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = """
    @staticmethod
    def export_etat_dettes_to_pdf(file_path, db_session, supplier_id,
                                        start_date, end_date, company_info=None):
        \"\"\"Generate an Etat des Dettes matching Etat des Creances but for suppliers.\"\"\"
        from reportlab.lib import colors as _c
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from datetime import datetime as _dt
        from app.models.supplier import Supplier
        from app.models.debt import Debt

        start_dt = start_date + " 00:00:00"
        end_dt   = end_date   + " 23:59:59"

        supplier = db_session.query(Supplier).get(supplier_id)
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        debts = db_session.query(Debt).filter(
            Debt.entity_type == "SUPPLIER",
            Debt.entity_id == supplier_id,
            Debt.is_deleted == 0,
            Debt.created_at.between(start_dt, end_dt)
        ).order_by(Debt.created_at).all()

        co = company_info or {}
        co_name    = co.get("name",    "SARL AZ VITA PHARM")
        co_phone   = co.get("phone",   "05.52.58.23.27 / 034.15.42.23")

        doc = SimpleDocTemplate(file_path, pagesize=A4,
            rightMargin=1.2*cm, leftMargin=1.2*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        def _p(text, bold=False, size=9, color=_c.black, align="LEFT"):
            st = ParagraphStyle("_px", parent=styles["Normal"], fontSize=size,
                textColor=color, leading=size*1.3,
                alignment={"LEFT":0,"CENTER":1,"RIGHT":2}.get(align, 0))
            return Paragraph(f"<b>{text}</b>" if bold else text, st)

        elements.append(_p(co_name, bold=True, size=12))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(_p("ETAT DES DETTES", bold=True, size=11, align="CENTER"))
        elements.append(HRFlowable(width="40%", thickness=0.5, color=_c.HexColor("#CCCCCC"), spaceAfter=5))
        elements.append(_p(f"Du : {start_date} Au : {end_date}", size=9, align="CENTER"))
        elements.append(Spacer(1, 0.5*cm))

        s_name  = getattr(supplier, "name",    "")
        s_addr  = getattr(supplier, "address", "")
        s_reg   = getattr(supplier, "region",  "")
        
        s_info = Table([
            [_p(f"FOURNISSEUR: {s_name}", bold=True), _p(f"Tél : {co_phone}", align="RIGHT")],
            [_p(f"Adresse : {s_addr}"), _p(f"Région : {s_reg}", align="RIGHT")]
        ], colWidths=[10*cm, 8.6*cm])
        s_info.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
        elements.append(s_info)
        elements.append(Spacer(1, 0.3*cm))

        headers = ["Référence", "Date", "PPA", "Net H.T", "TVA", "Net à payer", "Règlement", "Reste à payer"]
        item_rows = [[_p(h, bold=True, size=8, align="CENTER") for h in headers]]
        
        tot_ppa = 0.0
        tot_ht = 0.0
        tot_tva = 0.0
        tot_net = 0.0
        tot_regl = 0.0
        tot_reste = 0.0
        
        for d in debts:
            date_str = d.created_at[:10]
            date_str = f"{date_str[8:10]}/{date_str[5:7]}/{date_str[0:4]}"
            
            ref = ""
            ppa = 0.0
            ht = 0.0
            tva = 0.0
            net = 0.0
            regl = 0.0
            reste = 0.0
            
            if d.reference_type == "PURCHASE":
                from app.models.purchase import Purchase
                purch = db_session.query(Purchase).get(d.reference_id)
                if purch:
                    ref = purch.purchase_number
                    ht = purch.subtotal
                    tva = purch.tax_total
                    net = purch.total_amount
                    ppa = purch.subtotal * 1.5
                reste = d.remaining_amount
                regl = d.paid_amount
                
            elif d.reference_type == "SUPPLIER_INVOICE":
                from app.models.supplier_invoice import SupplierInvoice
                inv = db_session.query(SupplierInvoice).get(d.reference_id)
                if inv:
                    ref = inv.invoice_number or f"FACT-{inv.id}"
                    ht = inv.total_ht
                    tva = inv.total_tva
                    net = inv.total_ttc
                    ppa = inv.total_ht * 1.5
                reste = d.remaining_amount
                regl = d.paid_amount

            elif d.reference_type == "SUPPLIER_RETURN":
                from app.models.supplier_return import SupplierReturn
                ret = db_session.query(SupplierReturn).get(d.reference_id)
                if ret:
                    ref = ret.return_number or f"RET-{ret.id}"
                    net = -ret.total_amount
                    ht = -ret.total_amount
                    tva = 0.0
                    ppa = ht * 1.5
                    reste = d.remaining_amount
            
            elif d.reference_type == "PAYMENT":
                ref = "PAIEMENT"
                regl = d.paid_amount
                reste = d.remaining_amount
                if d.remaining_amount < 0:
                    reste = 0.0
            
            tot_ppa += ppa
            tot_ht += ht
            tot_tva += tva
            tot_net += net
            tot_regl += regl
            tot_reste += reste
            
            item_rows.append([
                _p(ref, size=7, align="LEFT"),
                _p(date_str, size=7, align="CENTER"),
                _p(f"{ppa:,.2f}".replace(","," "), size=7, align="RIGHT"),
                _p(f"{ht:,.2f}".replace(","," "), size=7, align="RIGHT"),
                _p(f"{tva:,.2f}".replace(","," "), size=7, align="RIGHT"),
                _p(f"{net:,.2f}".replace(","," "), size=7, align="RIGHT"),
                _p(f"{regl:,.2f}".replace(","," "), size=7, align="RIGHT"),
                _p(f"{reste:,.2f}".replace(","," "), size=7, align="RIGHT"),
            ])
            
        item_rows.append([
            _p(f"Total Fournisseur : {s_name.split()[0] if s_name else ''}", bold=True, size=8),
            "",
            _p(f"{tot_ppa:,.2f}".replace(","," "), bold=True, size=8, align="RIGHT"),
            _p(f"{tot_ht:,.2f}".replace(","," "), bold=True, size=8, align="RIGHT"),
            _p(f"{tot_tva:,.2f}".replace(","," "), bold=True, size=8, align="RIGHT"),
            _p(f"{tot_net:,.2f}".replace(","," "), bold=True, size=8, align="RIGHT"),
            _p(f"{tot_regl:,.2f}".replace(","," "), bold=True, size=8, align="RIGHT"),
            _p(f"{tot_reste:,.2f}".replace(","," "), bold=True, size=8, align="RIGHT"),
        ])
            
        t = Table(item_rows, repeatRows=1, colWidths=[3.2*cm, 2.2*cm, 2.5*cm, 2.5*cm, 1.8*cm, 2.5*cm, 2.2*cm, 2.2*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),_c.HexColor("#EFEFEF")),
            ("GRID",(0,0),(-1,-2),0.2,_c.HexColor("#CCCCCC")),
            ("LINEABOVE",(0,-1),(-1,-1),1,_c.black),
            ("LINEBELOW",(0,-1),(-1,-1),1,_c.black),
            ("SPAN",(0,-1),(1,-1)),
            ("TOPPADDING",(0,0),(-1,-1),2),
            ("BOTTOMPADDING",(0,0),(-1,-1),2)
        ]))
        elements.append(t)
        
        elements.append(Spacer(1, 2*cm))
        elements.append(_p(f"Date impression : {_dt.now().strftime('%d/%m/%Y')}", size=8, color=_c.grey, align="RIGHT"))
        
        doc.build(elements)
"""

content = content.replace("    # ── Fiche d'Expedition (Shipping Note) -----------------------------------------", new_func + "\\n    # ── Fiche d'Expedition (Shipping Note) -----------------------------------------", 1)

with open('app/utils/pdf_exporter.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
