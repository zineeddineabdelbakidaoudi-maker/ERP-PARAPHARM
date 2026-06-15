with open('ui/pages/deliveries_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

bad_text = """            self.db_session.add(new_debt)
                    reference_id=0,
                    total_amount=0.0,
                    paid_amount=excess,
                    remaining_amount=-excess,
                    status=DebtStatus.PAID.value,
                    notes="Versement anticipé / Trop-perçu Livraison"
                )
                self.db_session.add(credit_debt)

            self.db_session.commit()"""

good_text = """            self.db_session.add(new_debt)
            self.db_session.commit()"""

text = text.replace(bad_text, good_text)

with open('ui/pages/deliveries_page.py', 'w', encoding='utf-8') as f:
    f.write(text)
