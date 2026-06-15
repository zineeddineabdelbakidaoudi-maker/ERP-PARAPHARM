import sys
import os
from sqlalchemy.orm import Session
from app.core.database import get_session
from app.models.product import Product, Category
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.client import Client

def seed():
    session = get_session()
    
    # 1. Categories
    cat_meds = session.query(Category).filter_by(name="Médicaments").first()
    if not cat_meds:
        cat_meds = Category(name="Médicaments")
        session.add(cat_meds)
        session.flush()

    cat_para = session.query(Category).filter_by(name="Parapharmacie").first()
    if not cat_para:
        cat_para = Category(name="Parapharmacie")
        session.add(cat_para)
        session.flush()

    # 2. Supplier
    sup = session.query(Supplier).filter_by(code="FRS-TEST").first()
    if not sup:
        sup = Supplier(
            code="FRS-TEST",
            name="Fournisseur Test Pharma",
            phone="0555001122",
            address="Alger Centre",
            category="PHARMACEUTIQUE"
        )
        session.add(sup)

    # 3. Client
    cli = session.query(Client).filter_by(code="CLI-TEST").first()
    if not cli:
        cli = Client(
            code="CLI-TEST",
            name="Client Test",
            phone="0666001122",
            client_type="PARTICULIER"
        )
        session.add(cli)

    # 4. Products
    products = [
        {"code": "PRD-001", "name": "Doliprane 1000mg", "cat": cat_meds.id, "pa": 120.0, "pv": 150.0},
        {"code": "PRD-002", "name": "Augmentin 1g", "cat": cat_meds.id, "pa": 800.0, "pv": 950.0},
        {"code": "PRD-003", "name": "Sérum Physiologique", "cat": cat_para.id, "pa": 50.0, "pv": 80.0},
        {"code": "PRD-004", "name": "Vitamine C 1000", "cat": cat_meds.id, "pa": 200.0, "pv": 280.0},
    ]

    for p_data in products:
        prod = session.query(Product).filter_by(code=p_data["code"]).first()
        if not prod:
            prod = Product(
                code=p_data["code"],
                name=p_data["name"],
                category_id=p_data["cat"],
                cost_price=p_data["pa"],
                selling_price=p_data["pv"],
                min_stock_level=10.0,
                tax_rate=19.0,
                created_by=1
            )
            session.add(prod)
            session.flush()
            
            # Init stock
            stock = Stock(product_id=prod.id, quantity=100.0)
            session.add(stock)

    try:
        session.commit()
        print("Test data seeded successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error seeding data: {e}")

if __name__ == "__main__":
    seed()
